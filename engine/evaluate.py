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
