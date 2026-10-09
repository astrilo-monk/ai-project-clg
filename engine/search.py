"""
Adversarial search: minimax and alpha-beta pruning.

Convention used everywhere in this file:
    White is the MAX player (wants the score as HIGH as possible).
    Black is the MIN player (wants the score as LOW as possible).
    Scores come from evaluate(), which is always from White's point of view.

Two algorithms are kept side by side on purpose, so the report can compare
them on the same positions:

    minimax()    looks at EVERY move to the given depth.
    alphabeta()  returns the SAME score as minimax but skips branches that
                 cannot change the decision.
"""

import time
from dataclasses import dataclass

import chess

from engine.evaluate import MATE_SCORE, evaluate
from engine.ordering import capture_moves, order_moves

INFINITY = 10**9


@dataclass
class SearchStats:
    """Counts how much work the search did. Used for the report."""
    nodes: int = 0


@dataclass
class SearchResult:
    move: chess.Move | None
    score: int            # centipawns from White's point of view
    depth: int
    nodes: int
    seconds: float
    algorithm: str


# ---------------------------------------------------------------------------
# Terminal test and utility
# ---------------------------------------------------------------------------

def terminal_score(board: chess.Board, ply: int) -> int | None:
    """
    If the game is over in this position, return its utility.
    Otherwise return None.

    Checkmate is scored MATE_SCORE minus `ply` (how many half-moves from the
    root). This makes the engine prefer a FASTER mate when winning and a
    SLOWER mate when losing, instead of treating all mates as equal.
    """
    if not any(board.legal_moves):
        if board.is_check():
            # The side to move has been checkmated.
            return -(MATE_SCORE - ply) if board.turn == chess.WHITE else (MATE_SCORE - ply)
        return 0  # stalemate

    if board.is_insufficient_material() or board.halfmove_clock >= 100 or board.is_repetition(3):
        return 0  # draw

    return None


# ---------------------------------------------------------------------------
# 1. Plain minimax
# ---------------------------------------------------------------------------

def minimax(board: chess.Board, depth: int, ply: int, stats: SearchStats) -> int:
    """
    Classic minimax.

    At each node:
      - If the game is over, return the utility.
      - If depth is 0, return the heuristic evaluation.
      - If White to move, return the MAXIMUM of the children's scores.
      - If Black to move, return the MINIMUM of the children's scores.

    It visits every node of the tree, so the number of nodes grows roughly
    as (branching factor) ^ depth, about 35^depth in chess.
    """
    stats.nodes += 1

    result = terminal_score(board, ply)
    if result is not None:
        return result
    if depth == 0:
        return evaluate(board)

    if board.turn == chess.WHITE:
        best = -INFINITY
        for move in board.legal_moves:
            board.push(move)
            best = max(best, minimax(board, depth - 1, ply + 1, stats))
            board.pop()
        return best
    else:
        best = INFINITY
        for move in board.legal_moves:
            board.push(move)
            best = min(best, minimax(board, depth - 1, ply + 1, stats))
            board.pop()
        return best


# ---------------------------------------------------------------------------
# 2. Alpha-beta pruning
# ---------------------------------------------------------------------------

def alphabeta(
    board: chess.Board,
    depth: int,
    alpha: int,
    beta: int,
    ply: int,
    stats: SearchStats,
    use_ordering: bool = True,
    use_quiescence: bool = False,
) -> int:
    """
    Minimax with alpha-beta pruning.

    alpha = the best score White is ALREADY GUARANTEED elsewhere in the tree.
    beta  = the best score Black is ALREADY GUARANTEED elsewhere in the tree.

    If at some node alpha >= beta, the current line is one that the opponent
    would never allow (they already have something better), so the remaining
    moves at this node cannot affect the final decision. We stop searching
    them: this is the "cut-off" or "prune".

    The answer is identical to minimax; only the amount of work changes.
    """
    stats.nodes += 1

    result = terminal_score(board, ply)
    if result is not None:
        return result
    if depth == 0:
        if use_quiescence:
            return quiescence(board, alpha, beta, ply, stats)
        return evaluate(board)

    moves = order_moves(board) if use_ordering else list(board.legal_moves)

    if board.turn == chess.WHITE:  # MAX node
        best = -INFINITY
        for move in moves:
            board.push(move)
            score = alphabeta(board, depth - 1, alpha, beta, ply + 1, stats, use_ordering, use_quiescence)
            board.pop()
            best = max(best, score)
            alpha = max(alpha, best)
            if alpha >= beta:
                break  # beta cut-off: Black will never let the game reach here
        return best
    else:  # MIN node
        best = INFINITY
        for move in moves:
            board.push(move)
            score = alphabeta(board, depth - 1, alpha, beta, ply + 1, stats, use_ordering, use_quiescence)
            board.pop()
            best = min(best, score)
            beta = min(beta, best)
            if alpha >= beta:
                break  # alpha cut-off: White will never let the game reach here
        return best


# ---------------------------------------------------------------------------
# 3. Quiescence search (reduces the horizon effect)
# ---------------------------------------------------------------------------

MAX_QUIESCENCE_PLIES = 8


def quiescence(board: chess.Board, alpha: int, beta: int, ply: int, stats: SearchStats, qply: int = 0) -> int:
    """
    The horizon effect: if the search stops right after "my queen takes a
    pawn", it thinks it won a pawn, because it cannot see that the opponent
    recaptures the queen on the very next move.

    Quiescence search fixes this by continuing to search CAPTURES ONLY after
    the depth limit, until the position is "quiet" (no more captures).

    "Stand pat": the side to move is never forced to capture, so the static
    evaluation is a lower bound (for White) or upper bound (for Black) on the
    score.
    """
    stats.nodes += 1
    stand_pat = evaluate(board)
    if qply >= MAX_QUIESCENCE_PLIES:
        return stand_pat

    if board.turn == chess.WHITE:
        if stand_pat >= beta:
            return stand_pat
        alpha = max(alpha, stand_pat)
        for move in capture_moves(board):
            board.push(move)
            score = quiescence(board, alpha, beta, ply + 1, stats, qply + 1)
            board.pop()
            if score >= beta:
                return score
            alpha = max(alpha, score)
        return alpha
    else:
        if stand_pat <= alpha:
            return stand_pat
        beta = min(beta, stand_pat)
        for move in capture_moves(board):
            board.push(move)
            score = quiescence(board, alpha, beta, ply + 1, stats, qply + 1)
            board.pop()
            if score <= alpha:
                return score
            beta = min(beta, score)
        return beta


# ---------------------------------------------------------------------------
# Root: choose the actual move to play
# ---------------------------------------------------------------------------

ALGORITHMS = ("minimax", "alphabeta")


def find_best_move(
    board: chess.Board,
    depth: int,
    algorithm: str = "alphabeta",
    use_ordering: bool = True,
    use_quiescence: bool = True,
) -> SearchResult:
    """
    Search every legal move at the root and return the best one for the side
    to move, together with statistics for the report.

    `board` is copied, so the caller's board is never modified.
    """
    if algorithm not in ALGORITHMS:
        raise ValueError(f"algorithm must be one of {ALGORITHMS}")
    if depth < 1:
        raise ValueError("depth must be at least 1")

    board = board.copy()
    stats = SearchStats()
    start = time.perf_counter()

    maximizing = board.turn == chess.WHITE
    best_move = None
    best_score = -INFINITY if maximizing else INFINITY
    alpha, beta = -INFINITY, INFINITY

    if algorithm == "alphabeta" and use_ordering:
        root_moves = order_moves(board)
    else:
        root_moves = list(board.legal_moves)

    for move in root_moves:
        board.push(move)
        if algorithm == "minimax":
            score = minimax(board, depth - 1, 1, stats)
        else:
            score = alphabeta(board, depth - 1, alpha, beta, 1, stats, use_ordering, use_quiescence)
        board.pop()

        if (maximizing and score > best_score) or (not maximizing and score < best_score):
            best_score, best_move = score, move

        if maximizing:
            alpha = max(alpha, best_score)
        else:
            beta = min(beta, best_score)

    seconds = time.perf_counter() - start
    return SearchResult(
        move=best_move,
        score=best_score if best_move else 0,
        depth=depth,
        nodes=stats.nodes,
        seconds=seconds,
        algorithm=algorithm,
    )


def describe_score(score: int) -> str:
    """Human-friendly score text, e.g. '+1.25' or 'White mates in 2'."""
    if abs(score) >= MATE_SCORE - 1000:
        plies = MATE_SCORE - abs(score)
        moves = (plies + 1) // 2
        side = "White" if score > 0 else "Black"
        return f"{side} mates in {moves}"
    return f"{score / 100:+.2f}"
