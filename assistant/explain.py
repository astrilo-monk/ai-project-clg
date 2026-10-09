"""
Plain-English explanations: a small rule-based expert system.

The engine can tell THAT a move is bad (a number). A beginner needs to know
WHY. This module turns the engine's findings into sentences using hand-written
rules, each based on a common beginner mistake:

    Rule 1  Walking into checkmate
    Rule 2  Missing a checkmate
    Rule 3  Losing material (the opponent's best reply captures something)
    Rule 4  Leaving a piece hanging (undefended, or attacked by a cheaper piece)
    Rule 5  Missing a free capture
    Tips    Opening principles (early queen, giving up castling, knight on the rim)

Why rules instead of machine learning? Explanations in a teaching tool must
be correct, predictable and traceable. Every sentence here can be traced back
to one rule and one fact about the board, which a neural network could not
guarantee.

The rules only fire on moves the engine already judged as inaccuracies,
mistakes or blunders, so the engine decides IF a move is bad and the rules
explain WHY. The opening tips are general advice and can appear on any move.
"""

from dataclasses import dataclass, field

import chess

from assistant.blunder import MoveReview, for_player, is_mate_score, mate_in
from engine.evaluate import PIECE_VALUES

CENTER_SQUARES = (chess.D4, chess.E4, chess.D5, chess.E5)


@dataclass
class Feedback:
    headline: str
    reasons: list[str] = field(default_factory=list)  # why the move was bad
    better: str | None = None                         # what to play instead
    tips: list[str] = field(default_factory=list)     # general opening advice


# ---------------------------------------------------------------------------
# Board facts used by the rules
# ---------------------------------------------------------------------------

def name(piece_type: chess.PieceType) -> str:
    return chess.piece_name(piece_type)


def captured_piece_type(board: chess.Board, move: chess.Move) -> chess.PieceType | None:
    """Type of the piece a move captures, or None if it is not a capture."""
    if not board.is_capture(move):
        return None
    if board.is_en_passant(move):
        return chess.PAWN
    return board.piece_type_at(move.to_square)


def hanging_pieces(board: chess.Board, color: chess.Color) -> list[tuple[chess.Square, chess.PieceType, str]]:
    """
    Pieces of `color` that the opponent could win.

    A piece is "hanging" if it is attacked and either:
      - nothing defends it ("undefended"), or
      - it can be taken by a cheaper piece ("cheaper"), for example a pawn
        attacking a knight. Even if the knight is defended, pawn takes knight,
        recapture, still loses 220 centipawns.

    Kings are ignored (attacks on the king are checks, handled elsewhere).
    Returned most valuable first.
    """
    opponent = not color
    found = []
    for square, piece in board.piece_map().items():
        if piece.color != color or piece.piece_type == chess.KING:
            continue
        attackers = board.attackers(opponent, square)
        if not attackers:
            continue
        cheapest = min(PIECE_VALUES[board.piece_type_at(a)] for a in attackers)
        if not board.attackers(color, square):
            found.append((square, piece.piece_type, "undefended"))
        elif cheapest < PIECE_VALUES[piece.piece_type]:
            found.append((square, piece.piece_type, "cheaper"))
    found.sort(key=lambda item: PIECE_VALUES[item[1]], reverse=True)
    return found


def cheapest_attacker(board: chess.Board, square: chess.Square, by: chess.Color) -> chess.PieceType:
    return min((board.piece_type_at(a) for a in board.attackers(by, square)), key=lambda t: PIECE_VALUES[t])


def mate_threats(board: chess.Board) -> list[chess.Move]:
    """
    Moves with which the OPPONENT of the side to move could checkmate
    immediately if it were their turn ("threats").

    Trick: play a "null move" (pass the turn without moving) and then look for
    mate-in-one moves. Passing is illegal in real chess, but it is a standard
    way for engines to ask "what is my opponent threatening?".
    """
    if board.is_check():
        return []
    probe = board.copy(stack=False)
    probe.push(chess.Move.null())
    threats = []
    for move in probe.legal_moves:
        probe.push(move)
        if probe.is_checkmate():
            threats.append(move)
        probe.pop()
    return threats


def mate_threats_after_move(board: chess.Board, move: chess.Move) -> list[chess.Move]:
    """Mate threats the opponent still has after `move` is played."""
    after = board.copy(stack=False)
    after.push(move)
    if after.is_game_over():
        return []
    # After our move it is the opponent's turn, so look for their mates directly.
    threats = []
    for reply in after.legal_moves:
        after.push(reply)
        if after.is_checkmate():
            threats.append(reply)
        after.pop()
    return threats


def hanging_phrase(board: chess.Board, square: chess.Square, reason: str, owner: chess.Color) -> str:
    if reason == "undefended":
        return "is undefended and can be captured for free"
    attacker = name(cheapest_attacker(board, square, not owner))
    return f"can be taken by their {attacker}, a less valuable piece"


# ---------------------------------------------------------------------------
# Describing a GOOD move (used for "Better was ..." and for hints)
# ---------------------------------------------------------------------------

def describe_move_idea(board: chess.Board, move: chess.Move) -> str:
    """
    One short phrase describing the main idea of `move`, written so it fits
    after "it": e.g. "it wins their queen for free".
    Rules are checked from most to least important.
    """
    mover = board.turn
    piece_type = board.piece_type_at(move.from_square)
    after = board.copy()
    after.push(move)

    if after.is_checkmate():
        return "delivers checkmate"

    victim = captured_piece_type(board, move)
    if victim is not None:
        defended = bool(board.attackers(not mover, move.to_square)) and not board.is_en_passant(move)
        if not defended:
            return f"wins their {name(victim)} for free"
        if PIECE_VALUES[victim] > PIECE_VALUES[piece_type]:
            return f"wins material: your {name(piece_type)} takes their more valuable {name(victim)}"
        return f"captures their {name(victim)}"

    if move.promotion:
        return f"promotes your pawn to a {name(move.promotion)}"

    if board.is_castling(move):
        return "castles, tucking your king into safety and connecting your rooks"

    # Was the moved piece in danger before, and safe after?
    was_hanging = any(sq == move.from_square for sq, _, _ in hanging_pieces(board, mover))
    now_hanging = any(sq == move.to_square for sq, _, _ in hanging_pieces(after, mover))
    if was_hanging and not now_hanging:
        return f"moves your {name(piece_type)} out of danger"

    if after.is_check():
        return "gives check, forcing your opponent to respond"

    # Did it stop a checkmate threat?
    threats_before = mate_threats(board)
    if threats_before and not mate_threats_after_move(board, move):
        probe = board.copy(stack=False)
        probe.push(chess.Move.null())
        return f"stops your opponent's checkmate threat ({probe.san(threats_before[0])})"

    # Defends another piece that was hanging?
    before_hanging = {sq for sq, _, _ in hanging_pieces(board, mover)}
    after_hanging = {sq for sq, _, _ in hanging_pieces(after, mover)}
    saved = before_hanging - after_hanging - {move.from_square}
    if saved:
        sq = saved.pop()
        return f"protects your {name(board.piece_type_at(sq))} on {chess.square_name(sq)}"

    back_rank = 0 if mover == chess.WHITE else 7
    if piece_type in (chess.KNIGHT, chess.BISHOP) and chess.square_rank(move.from_square) == back_rank:
        return f"develops your {name(piece_type)} toward the center"

    if piece_type == chess.PAWN and move.to_square in CENTER_SQUARES:
        return "takes control of the center"

    return "improves your position"


# ---------------------------------------------------------------------------
# Explaining the player's move
# ---------------------------------------------------------------------------

HEADLINES = {
    "Best": "Best move!",
    "Good": "Good move.",
    "Inaccuracy": "Inaccuracy. There was a better move.",
    "Mistake": "Mistake.",
    "Blunder": "Blunder!",
}


def _loss_text(loss: int) -> str:
    pawns = loss / 100
    return f"about {pawns:.1f} pawns" if pawns < 9.5 else "a lot of material"


def explain_move(board: chess.Board, review: MoveReview) -> Feedback:
    """
    Build the coach's feedback for the move in `review`.
    `board` is the position BEFORE the move was played.
    """
    mover = review.mover
    move = review.move
    after = board.copy()
    after.push(move)

    feedback = Feedback(headline=HEADLINES[review.label])
    is_bad = review.label in ("Inaccuracy", "Mistake", "Blunder")

    if review.label == "Best":
        feedback.headline = f"Best move! {review.san} {describe_move_idea(board, move)}."
    elif review.label in ("Mistake", "Blunder") and not is_mate_score(review.best_score) and not is_mate_score(review.played_score):
        feedback.headline += f" This costs you {_loss_text(review.loss)}."

    if is_bad:
        reasons = feedback.reasons
        played_for_me = for_player(review.played_score, mover)
        best_for_me = for_player(review.best_score, mover)

        # Rule 1: walking into checkmate.
        if is_mate_score(played_for_me) and played_for_me < 0:
            n = mate_in(played_for_me)
            if n == 1:
                reasons.append(f"This move walks into checkmate: your opponent plays {review.reply_san}.")
            else:
                reasons.append(f"This move allows a forced checkmate in {n}, starting with {review.reply_san}.")

        # Rule 2: missing a checkmate.
        if is_mate_score(best_for_me) and best_for_me > 0 and not (is_mate_score(played_for_me) and played_for_me > 0):
            n = mate_in(best_for_me)
            when = "in one move" if n == 1 else f"in {n} moves"
            reasons.append(f"You missed a checkmate {when}, starting with {review.best_san}.")

        # Rule 3: the opponent's best reply wins something.
        reply_victim = captured_piece_type(after, review.reply) if review.reply else None
        hanging_after = hanging_pieces(after, mover)
        if reply_victim is not None and not reasons:
            target = review.reply.to_square
            if after.is_en_passant(review.reply):
                # En passant: the captured pawn is beside the target square, not on it.
                target = chess.square(chess.square_file(review.reply.to_square), chess.square_rank(review.reply.from_square))
            hanging_here = next((h for h in hanging_after if h[0] == target), None)
            square_name = chess.square_name(target)
            if hanging_here and target == move.to_square:
                reasons.append(
                    f"You moved your {name(reply_victim)} to {square_name}, where it "
                    f"{hanging_phrase(after, target, hanging_here[2], mover)}. "
                    f"Your opponent can play {review.reply_san}."
                )
            elif hanging_here and not any(h[0] == target for h in hanging_pieces(board, mover)):
                # It was safe before this move and is not any more:
                # the moved piece used to protect it.
                reasons.append(
                    f"Your {name(reply_victim)} on {square_name} is no longer protected after this move. "
                    f"Your opponent can play {review.reply_san}."
                )
            elif hanging_here:
                reasons.append(
                    f"Your {name(reply_victim)} on {square_name} "
                    f"{hanging_phrase(after, target, hanging_here[2], mover)}. "
                    f"Your opponent can play {review.reply_san}."
                )
            else:
                reasons.append(f"Your opponent can now win your {name(reply_victim)} on {square_name} with {review.reply_san}.")

        # Rule 4: a piece is left hanging even if the reply does something else.
        elif hanging_after and review.label in ("Mistake", "Blunder") and not reasons:
            sq, piece_type, why = hanging_after[0]
            reasons.append(f"Your {name(piece_type)} on {chess.square_name(sq)} {hanging_phrase(after, sq, why, mover)}.")

        # Rule 5: a free capture was available and not taken.
        best_victim = captured_piece_type(board, review.best_move)
        # Pawns only count if the engine says it really mattered (1+ pawn lost).
        if best_victim is not None and (best_victim != chess.PAWN or review.loss >= 100):
            undefended = not board.attackers(not mover, review.best_move.to_square)
            if undefended and not any("missed a checkmate" in r for r in reasons):
                reasons.append(
                    f"You missed a free {name(best_victim)} on "
                    f"{chess.square_name(review.best_move.to_square)} ({review.best_san})."
                )

        # Fallback: nothing specific matched, so show the engine's refutation.
        # Skipped for inaccuracies, where the reason is usually positional and
        # the opening tips or the "Better was" line say more.
        if not reasons and review.reply_san and review.label != "Inaccuracy":
            reasons.append(f"After this move your opponent's strongest reply is {review.reply_san}.")

        if move != review.best_move:
            feedback.better = f"Better was {review.best_san}: it {describe_move_idea(board, review.best_move)}."

    feedback.tips = opening_tips(board, move)
    return feedback


# ---------------------------------------------------------------------------
# Opening principles (general advice, not engine-based)
# ---------------------------------------------------------------------------

def opening_tips(board: chess.Board, move: chess.Move) -> list[str]:
    tips = []
    if board.fullmove_number > 10:
        return tips

    mover = board.turn
    piece_type = board.piece_type_at(move.from_square)
    back_rank = 0 if mover == chess.WHITE else 7
    home_minors = sum(
        1
        for sq in board.pieces(chess.KNIGHT, mover) | board.pieces(chess.BISHOP, mover)
        if chess.square_rank(sq) == back_rank
    )

    if piece_type == chess.QUEEN and home_minors >= 2:
        tips.append(
            "You brought your queen out early. Develop your knights and bishops first; "
            "an early queen gets chased around and you lose time."
        )

    if piece_type == chess.KING and not board.is_castling(move) and board.has_castling_rights(mover):
        tips.append("Moving your king gives up the right to castle. Castling is usually the safest home for your king.")

    if piece_type == chess.KNIGHT and chess.square_file(move.to_square) in (0, 7):
        tips.append('"A knight on the rim is dim": on the edge a knight controls far fewer squares than in the center.')

    return tips
