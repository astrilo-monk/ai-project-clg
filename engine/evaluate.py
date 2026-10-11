"""
Heuristic evaluation function.

EVAL(position) estimates how good a position is for WHITE, in centipawns
(100 centipawns = 1 pawn). Positive means White is better, negative means
Black is better.

The search calls this when it reaches its depth limit and cannot look further.

It combines two kinds of knowledge:
1. Material: how many pieces each side has, weighted by value.
2. Position: where those pieces stand, using piece-square tables.

Values and tables come from Tomasz Michniewski's "Simplified Evaluation
Function" (Chess Programming Wiki), a well-known starting point for engines.
"""

import chess

# ---------------------------------------------------------------------------
# 1. Material values (declarative knowledge)
# ---------------------------------------------------------------------------
PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000,  # never actually captured; kept so lookups never fail
}

# Score for a checkmate. Much larger than any material total, so the search
# always prefers delivering mate over winning pieces.
MATE_SCORE = 100000

# ---------------------------------------------------------------------------
# 2. Piece-square tables (heuristic knowledge)
# ---------------------------------------------------------------------------
# A piece-square table gives a small bonus or penalty for a piece standing on
# a particular square. Example: a knight in the center attacks up to 8
# squares, but in a corner only 2, so central squares get a bonus (+20) and
# corners a penalty (-50).
#
# Each table is written from WHITE's point of view, laid out like a board
# printed on paper: the first row is rank 8, the last row is rank 1,
# columns go a to h.

PAWN_TABLE = [
     0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,   # about to promote
    10, 10, 20, 30, 30, 20, 10, 10,
     5,  5, 10, 25, 25, 10,  5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,   # center pawns on e4/d4 are good
     5, -5,-10,  0,  0,-10, -5,  5,
     5, 10, 10,-20,-20, 10, 10,  5,   # do not leave d2/e2 pawns at home
     0,  0,  0,  0,  0,  0,  0,  0,
]

KNIGHT_TABLE = [
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50,  # "a knight on the rim is dim"
]

BISHOP_TABLE = [
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5, 10, 10,  5,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -20,-10,-10,-10,-10,-10,-10,-20,
]

ROOK_TABLE = [
     0,  0,  0,  0,  0,  0,  0,  0,
     5, 10, 10, 10, 10, 10, 10,  5,   # rook on the 7th rank is strong
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
     0,  0,  0,  5,  5,  0,  0,  0,
]

QUEEN_TABLE = [
    -20,-10,-10, -5, -5,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5,  5,  5,  5,  0,-10,
     -5,  0,  5,  5,  5,  5,  0, -5,
      0,  0,  5,  5,  5,  5,  0, -5,
    -10,  5,  5,  5,  5,  5,  0,-10,
    -10,  0,  5,  0,  0,  0,  0,-10,
    -20,-10,-10, -5, -5,-10,-10,-20,
]

# Middlegame: keep the king tucked away behind pawns (castled).
KING_MIDDLEGAME_TABLE = [
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -20,-30,-30,-40,-40,-30,-30,-20,
    -10,-20,-20,-20,-20,-20,-20,-10,
     20, 20,  0,  0,  0,  0, 20, 20,
     20, 30, 10,  0,  0, 10, 30, 20,
]

# Endgame: few pieces left, so the king becomes a fighting piece and should
# come to the center.
KING_ENDGAME_TABLE = [
    -50,-40,-30,-20,-20,-30,-40,-50,
    -30,-20,-10,  0,  0,-10,-20,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-30,  0,  0,  0,  0,-30,-30,
    -50,-30,-30,-30,-30,-30,-30,-50,
]

PIECE_SQUARE_TABLES = {
    chess.PAWN: PAWN_TABLE,
    chess.KNIGHT: KNIGHT_TABLE,
    chess.BISHOP: BISHOP_TABLE,
    chess.ROOK: ROOK_TABLE,
    chess.QUEEN: QUEEN_TABLE,
}


def table_index(square: chess.Square, color: chess.Color) -> int:
    """
    Convert a python-chess square to an index into the tables above.

    python-chess numbers squares a1=0, b1=1, ... h8=63 (rank 1 first).
    The tables are written rank 8 first, so for White we flip the rank.
    For Black we use the square as-is: Black's "rank 8 from its own side"
    is rank 1, which is exactly the mirror image we need.
    """
    return chess.square_mirror(square) if color == chess.WHITE else square


def is_endgame(board: chess.Board) -> bool:
    """
    Simple endgame test: no queens left, or each side with a queen has at
    most one minor piece besides pawns.
    """
    for color in (chess.WHITE, chess.BLACK):
        queens = len(board.pieces(chess.QUEEN, color))
        minors = len(board.pieces(chess.KNIGHT, color)) + len(board.pieces(chess.BISHOP, color))
        rooks = len(board.pieces(chess.ROOK, color))
        if queens and (rooks or minors > 1):
            return False
    return True


def evaluate(board: chess.Board) -> int:
    """
    Return the static evaluation of `board` from White's point of view.

    Terminal positions (mate, stalemate, draws) are handled by the search,
    not here. This function only scores "quiet" non-terminal positions.
    """
    endgame = is_endgame(board)
    score = 0

    for square, piece in board.piece_map().items():
        idx = table_index(square, piece.color)
        if piece.piece_type == chess.KING:
            table = KING_ENDGAME_TABLE if endgame else KING_MIDDLEGAME_TABLE
        else:
            table = PIECE_SQUARE_TABLES[piece.piece_type]

        value = PIECE_VALUES[piece.piece_type] + table[idx]
        score += value if piece.color == chess.WHITE else -value

    return score


# ===========================================================================
# Advanced evaluation (Phase 5), used only by the stronger search in
# engine/strong.py. evaluate() above stays unchanged so the Phase 2 results
# in the report can still be reproduced.
# ===========================================================================
#
# What it adds on top of material + piece-square tables:
#   1. Tapered evaluation: instead of a yes/no "is it the endgame?", the score
#      blends a middlegame score and an endgame score according to how much
#      material is left (the "game phase").
#   2. Pawn structure: passed pawns (worth more the further they are, and
#      much more in the endgame), doubled pawns, isolated pawns.
#   3. Bishop pair, rooks on open and half-open files.
#   4. King safety: pawns sheltering the king (middlegame only).
#   5. Mop-up: when one side is clearly winning an endgame, push the losing
#      king to the edge and bring the winning king closer, so the engine can
#      actually deliver checkmate instead of shuffling.

# Game phase: 24 at the start (all pieces on the board), 0 with only kings and pawns.
PHASE_WEIGHTS = {chess.KNIGHT: 1, chess.BISHOP: 1, chess.ROOK: 2, chess.QUEEN: 4}
MAX_PHASE = 24

# Indexed by how far the pawn has advanced from its own side (rank 0 to 7).
PASSED_PAWN_BONUS = [0, 5, 10, 20, 35, 60, 100, 0]
DOUBLED_PAWN_PENALTY = 15
ISOLATED_PAWN_PENALTY = 15
BISHOP_PAIR_BONUS = 30
ROOK_OPEN_FILE_BONUS = 20       # no pawns at all on the rook's file
ROOK_HALF_OPEN_FILE_BONUS = 10  # no pawns of its own colour on the file
KING_SHIELD_BONUS = 10          # per pawn directly in front of the king


def _squares_ahead(square: chess.Square, color: chess.Color, files: list[int], ranks_ahead: int = 7) -> int:
    """Bitmask of the squares on `files` that are in front of `square` (from `color`'s side)."""
    rank = chess.square_rank(square)
    ahead = range(rank + 1, min(8, rank + 1 + ranks_ahead)) if color == chess.WHITE \
        else range(rank - 1, max(-1, rank - 1 - ranks_ahead), -1)
    mask = 0
    for f in files:
        if 0 <= f < 8:
            for r in ahead:
                mask |= chess.BB_SQUARES[chess.square(f, r)]
    return mask


def _neighbours(file: int) -> list[int]:
    return [file - 1, file, file + 1]


# Precomputed once at import, so evaluation only does fast bitmask ANDs.
# PASSED_MASK[color][sq]: if no enemy pawn stands on these squares, a pawn on sq is passed.
PASSED_MASK = {c: [_squares_ahead(sq, c, _neighbours(chess.square_file(sq))) for sq in chess.SQUARES]
               for c in chess.COLORS}
# SHIELD_MASK[color][sq]: the two ranks in front of a king on sq, on its file and the two next to it.
SHIELD_MASK = {c: [_squares_ahead(sq, c, _neighbours(chess.square_file(sq)), ranks_ahead=2) for sq in chess.SQUARES]
               for c in chess.COLORS}
ADJACENT_FILES = [(chess.BB_FILES[f - 1] if f > 0 else 0) | (chess.BB_FILES[f + 1] if f < 7 else 0) for f in range(8)]


# Pawn hash table: the pawn structure changes only when a pawn moves or is
# captured, so most positions in a search share the same few pawn layouts.
# We cache the pawn score by layout instead of recomputing it every time.
_pawn_cache: dict[tuple[int, int, bool], tuple[int, int]] = {}


def _pawn_structure(own_pawns: int, enemy_pawns: int, color: chess.Color) -> tuple[int, int]:
    """(doubled + isolated penalties, passed pawn bonus) for one side."""
    key = (own_pawns, enemy_pawns, color)
    cached = _pawn_cache.get(key)
    if cached is not None:
        return cached

    penalties = 0
    for f in range(8):
        on_file = (own_pawns & chess.BB_FILES[f]).bit_count()
        if on_file > 1:
            penalties -= DOUBLED_PAWN_PENALTY * (on_file - 1)
        if on_file and not own_pawns & ADJACENT_FILES[f]:
            penalties -= ISOLATED_PAWN_PENALTY * on_file

    passed = 0
    for sq in chess.scan_forward(own_pawns):
        if not enemy_pawns & PASSED_MASK[color][sq]:
            advanced = chess.square_rank(sq) if color == chess.WHITE else 7 - chess.square_rank(sq)
            passed += PASSED_PAWN_BONUS[advanced]

    if len(_pawn_cache) > 200_000:  # ponytail: crude size cap, an LRU would keep the hottest entries
        _pawn_cache.clear()
    _pawn_cache[key] = (penalties, passed)
    return penalties, passed


def _structure(board: chess.Board, color: chess.Color) -> tuple[int, int]:
    """
    Pawn structure, bishops, rooks and king shelter for one side.
    Returns (middlegame score, endgame score) from that side's point of view.
    """
    own_pawns = board.pieces_mask(chess.PAWN, color)
    enemy_pawns = board.pieces_mask(chess.PAWN, not color)
    common, passed = _pawn_structure(own_pawns, enemy_pawns, color)

    if board.pieces_mask(chess.BISHOP, color).bit_count() >= 2:
        common += BISHOP_PAIR_BONUS

    for sq in chess.scan_forward(board.pieces_mask(chess.ROOK, color)):
        file_mask = chess.BB_FILES[chess.square_file(sq)]
        if not (own_pawns | enemy_pawns) & file_mask:
            common += ROOK_OPEN_FILE_BONUS
        elif not own_pawns & file_mask:
            common += ROOK_HALF_OPEN_FILE_BONUS

    shield = 0
    king = board.king(color)
    if king is not None:
        home_ranks = (0, 1) if color == chess.WHITE else (6, 7)
        if chess.square_rank(king) in home_ranks:
            shield = KING_SHIELD_BONUS * min(3, (own_pawns & SHIELD_MASK[color][king]).bit_count())

    # Passed pawns count normally in the middlegame and double in the endgame;
    # king shelter only matters while there are pieces around to attack it.
    return common + passed + shield, common + 2 * passed


def _centre_distance(square: chess.Square) -> int:
    """0 for the four centre squares, up to 6 for a corner."""
    f, r = chess.square_file(square), chess.square_rank(square)
    return max(3 - f, f - 4) + max(3 - r, r - 4)


# Speed: piece value + piece-square bonus, precomputed for every (colour, piece, square),
# indexed directly by python-chess square number. Same numbers as evaluate().
VALUE_TABLE = {
    (color, pt): [PIECE_VALUES[pt] + PIECE_SQUARE_TABLES[pt][table_index(sq, color)] for sq in chess.SQUARES]
    for color in chess.COLORS for pt in PIECE_SQUARE_TABLES
}
KING_TABLES = {
    color: ([KING_MIDDLEGAME_TABLE[table_index(sq, color)] for sq in chess.SQUARES],
            [KING_ENDGAME_TABLE[table_index(sq, color)] for sq in chess.SQUARES])
    for color in chess.COLORS
}


def evaluate_advanced(board: chess.Board) -> int:
    """Static evaluation from White's point of view, in centipawns (see the notes above)."""
    mg = eg = material = 0
    phase = 0

    # Walk the piece bitmasks directly: much faster than board.piece_map().
    for color, sign in ((chess.WHITE, 1), (chess.BLACK, -1)):
        occupied = board.occupied_co[color]
        for pt in PIECE_SQUARE_TABLES:
            mask = board.pieces_mask(pt, color)
            if not mask:
                continue
            table = VALUE_TABLE[(color, pt)]
            positional = sum(table[sq] for sq in chess.scan_forward(mask))
            count = mask.bit_count()
            mg += sign * positional
            eg += sign * positional
            material += sign * PIECE_VALUES[pt] * count
            phase += PHASE_WEIGHTS.get(pt, 0) * count
        king = board.kings & occupied
        if king:
            sq = king.bit_length() - 1
            mg += sign * KING_TABLES[color][0][sq]
            eg += sign * KING_TABLES[color][1][sq]

    for color, sign in ((chess.WHITE, 1), (chess.BLACK, -1)):
        s_mg, s_eg = _structure(board, color)
        mg += sign * s_mg
        eg += sign * s_eg

    # Mop-up: a clearly winning side (at least a rook ahead) in the endgame.
    if abs(material) >= 400:
        winner = chess.WHITE if material > 0 else chess.BLACK
        own_king, enemy_king = board.king(winner), board.king(not winner)
        if own_king is not None and enemy_king is not None:
            mop_up = 10 * _centre_distance(enemy_king) + 6 * (7 - chess.square_distance(own_king, enemy_king))
            eg += mop_up if winner == chess.WHITE else -mop_up

    # Blend: all middlegame at phase 24, all endgame at phase 0.
    # Integer maths and truncation toward zero keep the score exactly symmetric
    # between White and Black (tests/test_engine.py checks this).
    phase = min(phase, MAX_PHASE)
    return int((mg * phase + eg * (MAX_PHASE - phase)) / MAX_PHASE)
