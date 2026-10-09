"""
Hints: suggest a good move to the player, with the reason behind it.

A plain engine would only say "play Nxd5". A coach says
"Nxd5: it wins their queen for free." The reason comes from the same
rule-based describer used for explanations.
"""

from dataclasses import dataclass

import chess

from assistant.blunder import REVIEW_DEPTH
from assistant.explain import describe_move_idea
from engine.search import find_best_move


@dataclass
class Hint:
    move: chess.Move
    san: str
    idea: str      # e.g. "wins their queen for free"
    score: int     # White's point of view

    @property
    def text(self) -> str:
        return f"Try {self.san}: it {self.idea}."


def get_hint(board: chess.Board, depth: int = REVIEW_DEPTH) -> Hint | None:
    """Best move for the side to move, or None if the game is over."""
    if board.is_game_over():
        return None
    result = find_best_move(board, depth)
    return Hint(
        move=result.move,
        san=board.san(result.move),
        idea=describe_move_idea(board, result.move),
        score=result.score,
    )
