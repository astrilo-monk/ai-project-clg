"""
Move ordering.

Alpha-beta pruning returns the same answer whatever order moves are searched
in, but it prunes MUCH more when the best move is searched first. Once a
strong move has been found, weaker sibling moves get cut off quickly.

We cannot know the best move in advance, so we guess using cheap rules:

1. Captures first, ordered by MVV-LVA:
   "Most Valuable Victim, Least Valuable Attacker".
   Pawn takes queen (gain big, risk little) is tried before
   queen takes pawn (gain little, risk a lot).
2. Promotions next (a pawn becoming a queen is almost always strong).
3. Checks next (they force the opponent to respond).
4. All other quiet moves last.
"""

import chess

from engine.evaluate import PIECE_VALUES


def score_move(board: chess.Board, move: chess.Move, include_checks: bool = True) -> int:
    """
    Higher score means 'search this move earlier'.

    `include_checks` can be switched off where speed matters more than order,
    because testing whether a move gives check costs extra time.
    """
    score = 0

    if board.is_capture(move):
        if board.is_en_passant(move):
            victim = chess.PAWN  # the captured pawn is not on the target square
        else:
            victim = board.piece_type_at(move.to_square)
        attacker = board.piece_type_at(move.from_square)
        # Multiply the victim by 10 so the victim always dominates:
        # any capture of a queen outranks any capture of a rook, and so on.
        score += 10 * PIECE_VALUES[victim] - PIECE_VALUES[attacker] + 100000

    if move.promotion:
        score += PIECE_VALUES[move.promotion] + 50000

    if include_checks and board.gives_check(move):
        score += 10000

    return score


def order_moves(board: chess.Board) -> list[chess.Move]:
    """Return all legal moves, most promising first."""
    return sorted(board.legal_moves, key=lambda m: score_move(board, m), reverse=True)


def capture_moves(board: chess.Board) -> list[chess.Move]:
    """Only captures and promotions, ordered by MVV-LVA. Used by quiescence search."""
    moves = [m for m in board.legal_moves if board.is_capture(m) or m.promotion]
    return sorted(moves, key=lambda m: score_move(board, m, include_checks=False), reverse=True)
