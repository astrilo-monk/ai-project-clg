"""
Stronger search (Phase 5), used by the app's Hard and Expert opponent.

engine/search.py keeps the textbook minimax and alpha-beta untouched, so the
report's comparison can still be reproduced, and the coach keeps using that
exact search. This file adds the standard techniques real engines put on top
of alpha-beta. Each one is explained where it is used:

  1. Iterative deepening with a time limit   (search_best_move)
  2. Transposition table                     (negamax, "TT")
  3. Killer moves and history heuristic      (order_moves)
  4. Null-move pruning                       (negamax)
  5. Check extension, principal variation search and late move reductions (negamax)
  6. Delta pruning in quiescence search      (quiescence)
  7. Repetition = draw at the FIRST repeat   (negamax), so it stops shuffling
  8. The advanced evaluation                 (engine/evaluate.py)

NEGAMAX: the search below is alpha-beta written in its "negamax" form.
Minimax has two branches, one where White maximises and one where Black
minimises. Since min(a, b) = -max(-a, -b), both can be written as one branch
if every score is from the point of view of the side to move: my best score
is the maximum of minus my opponent's best score. Same algorithm, half the
code, which matters once each node does several extra things.
"""

import time

import chess

from engine.evaluate import MATE_SCORE, PIECE_VALUES, evaluate_advanced
from engine.search import SearchResult

INFINITY = 10**9
MATE_THRESHOLD = MATE_SCORE - 1000  # any score beyond this is "mate in N"
MAX_QUIESCENCE_PLIES = 8
NULL_MOVE_REDUCTION = 2
DELTA_MARGIN = 200
# Switches for experiments (tests/engine_match.py measures each technique on and off).
USE_NULL_MOVE = True
USE_LMR = True

# Transposition table entry flags: what kind of score we stored.
EXACT, LOWER_BOUND, UPPER_BOUND = 0, 1, 2


class TimeUp(Exception):
    """Raised inside the search when the time budget runs out."""


class Searcher:
    def __init__(self, board: chess.Board, time_limit: float | None, evaluate_fn=evaluate_advanced):
        self.board = board
        self.evaluate = evaluate_fn
        self.start = time.perf_counter()
        self.deadline = self.start + time_limit if time_limit else None
        self.can_stop = False  # depth 1 always finishes, so there is always a move to play
        self.nodes = 0
        self.partial: tuple[int, chess.Move] | None = None

        # Transposition table: position -> (depth, score, flag, best move).
        # Chess positions are often reached by different move orders
        # (1.e4 e5 2.Nf3 = 1.Nf3 e5 2.e4). The table remembers what we already
        # found, so the same position is not searched twice. It also remembers
        # the best move, which we search first next time: that is what makes
        # iterative deepening cheap.
        self.tt: dict = {}

        # Killer moves: quiet moves that caused a cut-off at the same depth in
        # a sibling position. A move that refuted one line often refutes the next.
        self.killers: dict[int, list[chess.Move]] = {}
        # History heuristic: how often a (from, to) quiet move caused a cut-off anywhere.
        self.history: dict[tuple[int, int], int] = {}

        # Repetition detection. Positions from the real game, plus the current
        # search path. Reaching one of them again is scored as a draw straight
        # away. The old search only saw THREE-fold repetitions, so it happily
        # walked into positions that repeated, and drew won games.
        self.repetitions: dict = {}
        replay = board.copy()
        while replay.move_stack:
            replay.pop()
            key = replay._transposition_key()
            self.repetitions[key] = self.repetitions.get(key, 0) + 1

    # ---- helpers --------------------------------------------------------

    def check_time(self) -> None:
        self.nodes += 1
        if self.can_stop and self.deadline and self.nodes % 1024 == 0 and time.perf_counter() > self.deadline:
            raise TimeUp

    def static_eval(self) -> int:
        """evaluate() is from White's point of view; negamax needs the side to move's."""
        score = self.evaluate(self.board)
        return score if self.board.turn == chess.WHITE else -score

    def capture_value(self, move: chess.Move) -> int:
        """MVV-LVA: big victim and small attacker first."""
        board = self.board
        victim = chess.PAWN if board.is_en_passant(move) else board.piece_type_at(move.to_square)
        return 10 * PIECE_VALUES[victim] - PIECE_VALUES[board.piece_type_at(move.from_square)]

    def order_moves(self, moves: list[chess.Move], tt_move: chess.Move | None, ply: int) -> list[chess.Move]:
        """
        Best guess first: the transposition-table move, then captures (MVV-LVA),
        promotions, killer moves, and finally quiet moves by history score.
        Unlike engine/ordering.py we do not test for checks here: in python-chess
        that test is slow, and the killer and history moves do the job better.
        """
        board = self.board
        killers = self.killers.get(ply, [])

        def score(move: chess.Move) -> int:
            if move == tt_move:
                return 10_000_000
            if board.is_capture(move):
                return 1_000_000 + self.capture_value(move)
            if move.promotion:
                return 900_000
            if move in killers:
                return 800_000
            return min(self.history.get((move.from_square, move.to_square), 0), 700_000)

        return sorted(moves, key=score, reverse=True)

    def remember_cutoff(self, move: chess.Move, depth: int, ply: int) -> None:
        if self.board.is_capture(move) or move.promotion:
            return  # captures are already ordered first
        killers = self.killers.setdefault(ply, [])
        if move not in killers:
            killers.insert(0, move)
            del killers[2:]
        key = (move.from_square, move.to_square)
        self.history[key] = self.history.get(key, 0) + depth * depth

    # ---- the search -----------------------------------------------------

    def negamax(self, depth: int, alpha: int, beta: int, ply: int, allow_null: bool = True) -> int:
        """Alpha-beta in negamax form; the score is from the side to move's point of view."""
        self.check_time()
        board = self.board
        key = board._transposition_key()

        # Draws: a repeated position, the 50-move rule, or too little material to mate.
        if ply > 0 and (self.repetitions.get(key) or board.halfmove_clock >= 100 or board.is_insufficient_material()):
            return 0

        # Check extension: when in check, search one move deeper. Checks are
        # forcing, so this is where short tactics hide.
        in_check = board.is_check()
        if in_check:
            depth += 1

        if depth <= 0:
            return self.quiescence(alpha, beta, ply)

        # Transposition table lookup.
        tt_move = None
        entry = self.tt.get(key)
        if entry:
            tt_depth, tt_score, tt_flag, tt_move = entry
            if tt_depth >= depth and ply > 0:
                tt_score = score_from_tt(tt_score, ply)
                if (tt_flag == EXACT
                        or (tt_flag == LOWER_BOUND and tt_score >= beta)
                        or (tt_flag == UPPER_BOUND and tt_score <= alpha)):
                    return tt_score

        # Null-move pruning: let the opponent move twice in a row (we "pass").
        # If our position is STILL so good that the score beats beta, a real
        # move would be even better, so this whole line is a cut-off and we
        # skip it after only a shallow search. Not done in check (passing would
        # be illegal) or with only king and pawns (where passing can be better
        # than any move, "zugzwang", and the trick gives wrong answers).
        if (USE_NULL_MOVE and allow_null and not in_check and depth >= 3 and ply > 0 and abs(beta) < MATE_THRESHOLD
                and board.occupied_co[board.turn] & ~(board.pawns | board.kings)):
            board.push(chess.Move.null())
            score = -self.negamax(depth - 1 - NULL_MOVE_REDUCTION, -beta, -beta + 1, ply + 1, allow_null=False)
            board.pop()
            if score >= beta:
                return beta

        moves = list(board.legal_moves)
        if not moves:
            # Checkmate (prefer the fastest mate, see engine/search.py) or stalemate.
            return -(MATE_SCORE - ply) if in_check else 0

        original_alpha = alpha
        best_score, best_move = -INFINITY, None
        killers = self.killers.get(ply, [])
        self.repetitions[key] = self.repetitions.get(key, 0) + 1
        for i, move in enumerate(self.order_moves(moves, tt_move, ply)):
            quiet = not board.is_capture(move) and not move.promotion and move not in killers
            board.push(move)
            if i == 0:
                score = -self.negamax(depth - 1, -beta, -alpha, ply + 1)
            else:
                # Late move reduction: thanks to move ordering, quiet moves near
                # the end of the list are rarely good. Search them one ply
                # shallower first; if one turns out better than expected, it
                # gets a full-depth search below.
                reduction = 1 if USE_LMR and depth >= 3 and i >= 3 and quiet and not in_check and not board.is_check() else 0
                # Principal variation search: the first move is probably the
                # best, so for the others we only ask the cheaper yes/no question
                # "is this better than alpha?" with a zero-width window.
                score = -self.negamax(depth - 1 - reduction, -alpha - 1, -alpha, ply + 1)
                if score > alpha and reduction:
                    score = -self.negamax(depth - 1, -alpha - 1, -alpha, ply + 1)
                if alpha < score < beta:
                    # It really is better: search it again with the full window to get its exact score.
                    score = -self.negamax(depth - 1, -beta, -alpha, ply + 1)
            board.pop()
            if score > best_score:
                best_score, best_move = score, move
            alpha = max(alpha, score)
            if alpha >= beta:
                self.remember_cutoff(move, depth, ply)
                break  # cut-off: the opponent will never allow this line
        self.repetitions[key] -= 1

        if best_score <= original_alpha:
            flag = UPPER_BOUND   # nothing beat alpha: the true score is at most this
        elif best_score >= beta:
            flag = LOWER_BOUND   # cut-off: the true score is at least this
        else:
            flag = EXACT
        self.tt[key] = (depth, score_to_tt(best_score, ply), flag, best_move)
        return best_score

    def quiescence(self, alpha: int, beta: int, ply: int, qply: int = 0) -> int:
        """Captures only, until the position is quiet (same idea as engine/search.py, in negamax form)."""
        self.check_time()
        stand_pat = self.static_eval()
        if stand_pat >= beta or qply >= MAX_QUIESCENCE_PLIES:
            return stand_pat
        alpha = max(alpha, stand_pat)

        board = self.board
        captures = sorted(board.generate_legal_captures(), key=self.capture_value, reverse=True)
        for move in captures:
            # Delta pruning: if even winning this piece for free (plus a margin)
            # cannot lift the score up to alpha, do not bother searching it.
            victim = chess.PAWN if board.is_en_passant(move) else board.piece_type_at(move.to_square)
            if not move.promotion and stand_pat + PIECE_VALUES[victim] + DELTA_MARGIN < alpha:
                continue
            board.push(move)
            score = -self.quiescence(-beta, -alpha, ply + 1, qply + 1)
            board.pop()
            if score >= beta:
                return score
            alpha = max(alpha, score)
        return alpha

    def search_root(self, depth: int, previous_best: chess.Move | None) -> tuple[int, chess.Move]:
        board = self.board
        alpha, beta = -INFINITY, INFINITY
        best_move = None
        self.partial = None
        for move in self.order_moves(list(board.legal_moves), previous_best, 0):
            board.push(move)
            if best_move is None:
                score = -self.negamax(depth - 1, -beta, -alpha, 1)
            else:  # principal variation search, as in negamax()
                score = -self.negamax(depth - 1, -alpha - 1, -alpha, 1)
                if score > alpha:
                    score = -self.negamax(depth - 1, -beta, -alpha, 1)
            board.pop()
            if best_move is None or score > alpha:
                alpha, best_move = score, move
                self.partial = (alpha, best_move)  # best so far at this depth, in case time runs out
        self.tt[board._transposition_key()] = (depth, alpha, EXACT, best_move)
        return alpha, best_move


# Mate scores depend on the distance from the root ("mate in 3 from here").
# The table stores them as distance from the stored position instead, so the
# same entry is correct wherever in the tree the position turns up again.
def score_to_tt(score: int, ply: int) -> int:
    if score >= MATE_THRESHOLD:
        return score + ply
    if score <= -MATE_THRESHOLD:
        return score - ply
    return score


def score_from_tt(score: int, ply: int) -> int:
    if score >= MATE_THRESHOLD:
        return score - ply
    if score <= -MATE_THRESHOLD:
        return score + ply
    return score


def search_best_move(board: chess.Board, time_limit: float | None = 1.0, max_depth: int = 64,
                     evaluate_fn=evaluate_advanced, min_depth: int = 1) -> SearchResult:
    """
    Iterative deepening: search depth 1, then 2, then 3, ... until the time
    runs out, and play the best move of the deepest search that finished.

    This sounds wasteful, but each search is far quicker than the next one
    (the tree grows about 5 to 10 times per extra depth), and each one fills
    the transposition table with the best moves, so the next depth searches
    the best move first and prunes much more. It also means the engine always
    has a move ready when the time is up.

    `min_depth` is always finished, however long it takes, so a busy or slow
    computer can make the engine slower but never shallower than that.

    `board` is copied, so the caller's board is never modified. The score is
    returned from White's point of view, like engine/search.py.
    """
    board = board.copy()
    if not any(board.legal_moves):
        return SearchResult(move=None, score=0, depth=0, nodes=0, seconds=0.0, algorithm="strong")

    searcher = Searcher(board, time_limit, evaluate_fn)
    searcher.repetitions[board._transposition_key()] = searcher.repetitions.get(board._transposition_key(), 0) + 1
    best_move, best_score, completed = None, 0, 0

    for depth in range(1, max_depth + 1):
        try:
            score, move = searcher.search_root(depth, best_move)
        except TimeUp:
            # The unfinished depth searched the previous best move first. If
            # that finished, and some other move already beat it, that move is
            # proven better at this depth: play it rather than waste the work.
            if searcher.partial:
                best_score, best_move = searcher.partial
            break
        best_move, best_score, completed = move, score, depth
        searcher.can_stop = depth >= min_depth
        if abs(score) >= MATE_THRESHOLD:
            break  # a forced mate was found; searching deeper cannot improve on it
        # The next depth takes several times longer than this one. If half the
        # budget is already gone, it would almost surely not finish, so stop now.
        if depth >= min_depth and time_limit and time.perf_counter() - searcher.start > time_limit / 2:
            break

    return SearchResult(
        move=best_move,
        score=best_score if board.turn == chess.WHITE else -best_score,
        depth=completed,
        nodes=searcher.nodes,
        seconds=time.perf_counter() - searcher.start,
        algorithm="strong",
    )
