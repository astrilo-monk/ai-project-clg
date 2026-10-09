"""
Blunder detection: judge how good the player's move was.

Idea (the same one strong chess websites use):

    1. Ask the engine for the BEST move in the position before the player moved,
       and its score.
    2. Ask the engine for the score of the move the player ACTUALLY played.
    3. The difference is the "centipawn loss": how much worse the player's
       move is than the best move, measured in hundredths of a pawn.

    centipawn loss = score(best move) - score(played move)
                     (both from the player's own point of view)

The loss is then turned into a label a beginner understands:

    loss 0 (same as engine)   Best         "!"
    loss under 50             Good
    loss 50 to 99             Inaccuracy   "?!"
    loss 100 to 199           Mistake      "?"
    loss 200 or more          Blunder      "??"

200 centipawns = 2 pawns, roughly losing a minor piece's worth of advantage.
The symbols are the standard chess annotation symbols used in books.
"""

from dataclasses import dataclass

import chess

from engine.evaluate import MATE_SCORE
from engine.search import find_best_move, terminal_score

# Depth used by the coach. It is independent of the opponent's difficulty:
# even on "Easy" the coach should still judge your moves properly.
REVIEW_DEPTH = 3

# Any score this close to MATE_SCORE means "forced mate".
MATE_THRESHOLD = MATE_SCORE - 1000

LABELS = ("Best", "Good", "Inaccuracy", "Mistake", "Blunder")

SYMBOLS = {
    "Best": "!",
    "Good": "",
    "Inaccuracy": "?!",
    "Mistake": "?",
    "Blunder": "??",
}


@dataclass
class MoveReview:
    """Everything the coach found out about one move."""
    move: chess.Move
    san: str
    mover: chess.Color
    label: str
    loss: int                 # centipawns lost versus the best move (never negative)
    best_move: chess.Move
    best_san: str
    best_score: int           # score of the best move, White's point of view
    played_score: int         # score of the played move, White's point of view
    reply: chess.Move | None  # opponent's best answer to the played move
    reply_san: str | None

    @property
    def symbol(self) -> str:
        return SYMBOLS[self.label]


def is_mate_score(score: int) -> bool:
    return abs(score) >= MATE_THRESHOLD


def mate_in(score: int) -> int:
    """Convert a mate score into 'mate in N moves' (full moves, not half-moves)."""
    plies = MATE_SCORE - abs(score)
    return (plies + 1) // 2


def for_player(score: int, color: chess.Color) -> int:
    """Scores are stored from White's view. Flip the sign for Black."""
    return score if color == chess.WHITE else -score


def classify(loss: int) -> str:
    if loss < 50:
        return "Good"
    if loss < 100:
        return "Inaccuracy"
    if loss < 200:
        return "Mistake"
    return "Blunder"


def _one_ply_later(score: int) -> int:
    """
    A mate found by searching AFTER the move is one half-move further from
    the original position. Mate scores encode distance, so shift them by 1
    to compare fairly with the score of the best move.
    """
    if score >= MATE_THRESHOLD:
        return score - 1
    if score <= -MATE_THRESHOLD:
        return score + 1
    return score


def review_move(board: chess.Board, move: chess.Move, depth: int = REVIEW_DEPTH) -> MoveReview:
    """
    Judge `move` played in position `board` (the position BEFORE the move).

    Cost: two engine searches. One for the best move at `depth`, one for the
    played move at `depth - 1` (one half-move has already been played, so this
    searches exactly the same part of the game tree as step 1 did for that move).
    """
    if depth < 2:
        raise ValueError("review depth must be at least 2")
    if move not in board.legal_moves:
        raise ValueError(f"{move} is not legal in this position")

    mover = board.turn
    san = board.san(move)

    # Step 1: what would the engine have played?
    best = find_best_move(board, depth)

    # Step 2: how good is the move the player chose?
    after = board.copy()
    after.push(move)
    game_over_score = terminal_score(after, 1)
    if game_over_score is not None:
        played_score, reply, reply_san = game_over_score, None, None
    elif move == best.move:
        # Same move as the engine: same score, but we still want the reply.
        reply_result = find_best_move(after, depth - 1)
        played_score, reply = best.score, reply_result.move
        reply_san = after.san(reply)
    else:
        reply_result = find_best_move(after, depth - 1)
        played_score, reply = _one_ply_later(reply_result.score), reply_result.move
        reply_san = after.san(reply)

    # Step 3: centipawn loss, from the mover's point of view.
    loss = max(0, for_player(best.score, mover) - for_player(played_score, mover))

    if move == best.move or loss == 0:
        label = "Best"
    else:
        label = classify(loss)

    return MoveReview(
        move=move,
        san=san,
        mover=mover,
        label=label,
        loss=loss,
        best_move=best.move,
        best_san=board.san(best.move),
        best_score=best.score,
        played_score=played_score,
        reply=reply,
        reply_san=reply_san,
    )
