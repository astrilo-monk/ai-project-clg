"""
Streamlit interface for the AI Chess Assistant.

Run with:  streamlit run app.py

Phase 3 version: the beginner assistant.
    - Difficulty levels (Easy / Medium / Hard / Expert)
    - Coach reviews every move you play: Best / Good / Inaccuracy / Mistake / Blunder
    - Plain-English explanation of mistakes, with the better move drawn on a board
    - Hint button with the reason behind the suggested move
    - Take back, so you can retry after a mistake
    - Move history annotated with chess symbols (!, ?!, ?, ??)
"""

import html
from pathlib import Path

import chess
import chess.svg
import streamlit as st
import streamlit.components.v1 as components

from assistant.blunder import LABELS, review_move
from assistant.explain import explain_move
from assistant.hints import get_hint
from engine.search import describe_score, find_best_move
from engine.strong import search_best_move

st.set_page_config(page_title="AI Chess Assistant", page_icon="♟", layout="wide")

# Easy and Medium use the original engine at a fixed, shallow depth. Easy has
# no quiescence, so it can grab a pawn and lose a piece to the recapture,
# exactly the kind of mistake a beginner can punish.
# Hard and Expert use the stronger Phase 5 engine (engine/strong.py) with a
# time limit per move instead of a fixed depth.
DIFFICULTY = {
    "Easy": dict(depth=1, use_quiescence=False),
    "Medium": dict(depth=2, use_quiescence=True),
    "Hard": dict(time_limit=0.5, min_depth=3),
    "Expert": dict(time_limit=2.0, min_depth=4),
}

LABEL_COLORS = {
    "Best": "#1a7f37",
    "Good": "#57606a",
    "Inaccuracy": "#9a6700",
    "Mistake": "#bc4c00",
    "Blunder": "#cf222e",
}

ARROW_BETTER = "#15781b"
ARROW_PLAYED = "#c62828"

# Clickable board: a small HTML/JavaScript page in board_component/ (Streamlit has
# no built-in one). It draws the pieces with python-chess's own SVG pictures and
# only allows moves from the legal list we pass in.
chessboard = components.declare_component("chessboard", path=str(Path(__file__).parent / "board_component"))
PIECE_SVGS = {s: chess.svg.piece(chess.Piece.from_symbol(s)) for s in "PNBRQKpnbrqk"}


# ---------------------------------------------------------------------------
# Game state
# ---------------------------------------------------------------------------
# Streamlit re-runs this whole script on every click, so anything that must
# survive between clicks goes in st.session_state.

def new_game(player_color: chess.Color) -> None:
    st.session_state.board = chess.Board()
    st.session_state.player_color = player_color
    st.session_state.last_search = None   # stats of the engine's last move
    st.session_state.reviews = {}         # ply index -> MoveReview of the player's move
    st.session_state.feedback = None      # (review, feedback, fen_before) of the last move
    st.session_state.hint = None


if "board" not in st.session_state:
    new_game(chess.WHITE)

board: chess.Board = st.session_state.board
player_color: chess.Color = st.session_state.player_color


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Settings")
    level = st.radio(
        "Opponent difficulty", list(DIFFICULTY), index=1,
        help="Easy: looks 1 half-move ahead. Medium: 2. Hard and Expert: the stronger engine, "
             "thinking 0.5 s and 2 s per move.",
    )
    coach_on = st.toggle("Coach mode", value=True, help="Review every move you play and explain mistakes.")
    st.caption(
        "The coach always searches at depth 3, whatever the opponent's difficulty, "
        "so your moves are judged the same way on every level."
    )


def computer_move(board: chess.Board) -> chess.Move:
    """Ask our engine for its move at the chosen difficulty."""
    settings = DIFFICULTY[level]
    with st.spinner("Engine is thinking..."):
        if "time_limit" in settings:
            result = search_best_move(board, **settings)
        else:
            result = find_best_move(board, algorithm="alphabeta", use_ordering=True, **settings)
    st.session_state.last_search = result
    return result.move


def play_player_move(move: chess.Move) -> None:
    """Review the player's move (coach), play it, then let the engine reply."""
    if coach_on:
        before = board.copy()
        with st.spinner("Coach is reviewing your move..."):
            review = review_move(before, move)
            feedback = explain_move(before, review)
        st.session_state.reviews[len(board.move_stack)] = review
        st.session_state.feedback = (review, feedback, before.fen())
    else:
        st.session_state.feedback = None

    st.session_state.hint = None
    board.push(move)
    if not board.is_game_over():
        board.push(computer_move(board))


def take_back() -> None:
    """Undo the engine's reply and the player's last move."""
    if board.move_stack and board.turn == player_color:
        board.pop()  # engine's reply
    if board.move_stack:
        board.pop()  # player's move
    st.session_state.reviews = {k: v for k, v in st.session_state.reviews.items() if k < len(board.move_stack)}
    st.session_state.feedback = None
    st.session_state.hint = None
    st.session_state.last_search = None


def game_status(board: chess.Board) -> str:
    if board.is_checkmate():
        winner = "Black" if board.turn == chess.WHITE else "White"
        return f"Checkmate. {winner} wins."
    if board.is_stalemate():
        return "Stalemate. Draw."
    if board.is_insufficient_material():
        return "Draw by insufficient material."
    if board.can_claim_threefold_repetition():
        return "Draw by threefold repetition."
    if board.can_claim_fifty_moves():
        return "Draw by the 50-move rule."
    if board.turn == player_color:
        return "Your move" + (" (you are in check)" if board.is_check() else "")
    return "Engine to move"


def badge(label: str, count: int | None = None) -> str:
    text = label if count is None else f"{label} {count}"
    return (
        f'<span style="background:{LABEL_COLORS[label]};color:#fff;padding:2px 8px;white-space:nowrap;'
        f'border-radius:10px;font-size:0.8rem;font-weight:600;display:inline-block;margin:2px">{text}</span>'
    )


def annotated_moves_html() -> str:
    """Move list like '1. e4! e5 2. Qh5?! Nc6', with the player's moves coloured by quality."""
    replay = chess.Board()
    parts = []
    for i, move in enumerate(board.move_stack):
        if replay.turn == chess.WHITE:
            parts.append(f"<b>{replay.fullmove_number}.</b>")
        elif i == 0:
            parts.append(f"<b>{replay.fullmove_number}...</b>")
        san = html.escape(replay.san(move))
        review = st.session_state.reviews.get(i)
        if review:
            color = LABEL_COLORS[review.label]
            parts.append(f'<span style="color:{color};font-weight:600" title="{review.label}">{san}{review.symbol}</span>')
        else:
            parts.append(san)
        replay.push(move)
    return '<div style="line-height:1.9;font-family:monospace">' + " ".join(parts) + "</div>"


# If it is the computer's turn (for example the player chose Black), move now.
if not board.is_game_over() and board.turn != player_color:
    board.push(computer_move(board))


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
st.title("AI Chess Assistant for Beginners")

left, right = st.columns([3, 2], gap="large")

with left:
    hint = st.session_state.hint
    players_turn = not board.is_game_over() and board.turn == player_color
    last = board.peek() if board.move_stack else None
    clicked = chessboard(
        fen=board.fen(),
        orientation="white" if player_color == chess.WHITE else "black",
        interactive=players_turn,
        legal=[m.uci() for m in board.legal_moves] if players_turn else [],
        lastmove=[chess.square_name(last.from_square), chess.square_name(last.to_square)] if last else None,
        check=chess.square_name(board.king(board.turn)) if board.is_check() else None,
        arrows=[[chess.square_name(hint.move.from_square), chess.square_name(hint.move.to_square), ARROW_BETTER]]
        if hint and players_turn else [],
        pieces=PIECE_SVGS,
        key="board_clicks",  # not "board": that name already holds the game in session_state
        default=None,
    )
    # The board keeps returning its last click on every rerun, so only act on a new one.
    if clicked and clicked["id"] != st.session_state.get("last_click_id"):
        st.session_state.last_click_id = clicked["id"]
        move = chess.Move.from_uci(clicked["uci"])
        if players_turn and move in board.legal_moves:
            play_player_move(move)
            st.rerun()

    result = st.session_state.last_search
    if result is not None:
        c1, c2, c3 = st.columns(3)
        c1.metric("Evaluation", describe_score(result.score), help="Positive is good for White, in pawns.")
        c2.metric("Engine nodes searched", f"{result.nodes:,}")
        c3.metric("Engine time", f"{result.seconds:.2f}s")

with right:
    st.subheader(game_status(board))

    if players_turn:
        st.caption("Click a piece to see where it can go, then click a highlighted square to move it.")
        b1, b2 = st.columns(2)
        if b1.button("Hint", use_container_width=True):
            with st.spinner("Looking for a good move..."):
                st.session_state.hint = get_hint(board)
            st.rerun()
        if b2.button("Take back", disabled=not board.move_stack, use_container_width=True):
            take_back()
            st.rerun()
        # Keyboard fallback for anyone who can't use the mouse.
        with st.expander("Or type your move"):
            moves = {board.san(m): m for m in board.legal_moves}
            choice = st.selectbox("Your move", sorted(moves), index=None, placeholder="e.g. e4 or Nf3")
            if st.button("Play move", type="primary", disabled=choice is None):
                play_player_move(moves[choice])
                st.rerun()

        if hint:
            st.success(f"Hint: {hint.text}")
    elif board.is_game_over() and board.move_stack:
        if st.button("Take back last move"):
            take_back()
            st.rerun()

    # ---- Coach feedback on the last move --------------------------------
    if st.session_state.feedback:
        review, feedback, fen_before = st.session_state.feedback
        st.divider()
        st.markdown(f"**Coach** &nbsp; {badge(review.label)} &nbsp; on your move **{html.escape(review.san)}**",
                    unsafe_allow_html=True)
        st.write(feedback.headline)
        for reason in feedback.reasons:
            st.markdown(f"- {reason}")
        if feedback.better:
            st.markdown(f"**{feedback.better}**")
        for tip in feedback.tips:
            st.info(f"Tip: {tip}")

        if review.label in ("Inaccuracy", "Mistake", "Blunder"):
            with st.expander("Show the position before your move", expanded=review.label == "Blunder"):
                before = chess.Board(fen_before)
                small = chess.svg.board(
                    before,
                    orientation=player_color,
                    arrows=[
                        chess.svg.Arrow(review.move.from_square, review.move.to_square, color=ARROW_PLAYED),
                        chess.svg.Arrow(review.best_move.from_square, review.best_move.to_square, color=ARROW_BETTER),
                    ],
                    size=300,
                )
                st.markdown(f'<div style="max-width:300px">{small}</div>', unsafe_allow_html=True)
                st.caption("Red arrow: your move. Green arrow: the better move.")

    # ---- Move history and summary ---------------------------------------
    if board.move_stack:
        st.divider()
        st.caption("Moves (your moves are coloured by the coach)")
        st.markdown(annotated_moves_html(), unsafe_allow_html=True)

        reviews = list(st.session_state.reviews.values())
        if reviews:
            counts = {label: sum(r.label == label for r in reviews) for label in LABELS}
            st.markdown(" ".join(badge(l, counts[l]) for l in LABELS), unsafe_allow_html=True)

    st.divider()
    color_label = st.radio("Play as", ["White", "Black"], horizontal=True)
    if st.button("New game"):
        new_game(chess.WHITE if color_label == "White" else chess.BLACK)
        st.rerun()
