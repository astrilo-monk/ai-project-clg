"""
Streamlit interface for the AI Chess Assistant.

Run with:  streamlit run app.py

Phase 1 version: you play against a computer that picks a RANDOM legal move.
The real engine replaces the random mover in Phase 2.
"""

import random

import chess
import chess.svg
import streamlit as st

st.set_page_config(page_title="AI Chess Assistant", page_icon="♟", layout="wide")


# ---------------------------------------------------------------------------
# Game state
# ---------------------------------------------------------------------------
# Streamlit re-runs this whole script on every click, so anything that must
# survive between clicks (the board, the player's colour) goes in
# st.session_state.

def new_game(player_color: chess.Color) -> None:
    st.session_state.board = chess.Board()
    st.session_state.player_color = player_color


if "board" not in st.session_state:
    new_game(chess.WHITE)

board: chess.Board = st.session_state.board
player_color: chess.Color = st.session_state.player_color


def computer_move(board: chess.Board) -> chess.Move:
    """Phase 1 placeholder: choose any legal move at random."""
    return random.choice(list(board.legal_moves))


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
    side = "White" if board.turn == chess.WHITE else "Black"
    return f"{side} to move" + (" (in check)" if board.is_check() else "")


# If it is the computer's turn (for example the player chose Black), move now.
if not board.is_game_over() and board.turn != player_color:
    board.push(computer_move(board))


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
st.title("AI Chess Assistant for Beginners")

left, right = st.columns([3, 2])

with left:
    last_move = board.peek() if board.move_stack else None
    check_square = board.king(board.turn) if board.is_check() else None
    svg = chess.svg.board(
        board,
        orientation=player_color,
        lastmove=last_move,
        check=check_square,
        size=480,
    )
    st.markdown(f'<div style="max-width:480px">{svg}</div>', unsafe_allow_html=True)

with right:
    st.subheader(game_status(board))

    if not board.is_game_over() and board.turn == player_color:
        # Show legal moves in standard notation (e.g. "Nf3"), sorted A to Z.
        moves = {board.san(m): m for m in board.legal_moves}
        choice = st.selectbox("Your move", sorted(moves))
        if st.button("Play move", type="primary"):
            board.push(moves[choice])
            if not board.is_game_over():
                board.push(computer_move(board))
            st.rerun()

    st.divider()
    color_label = st.radio("Play as", ["White", "Black"], horizontal=True)
    if st.button("New game"):
        new_game(chess.WHITE if color_label == "White" else chess.BLACK)
        st.rerun()

    if board.move_stack:
        st.divider()
        st.caption("Moves")
        st.text(chess.Board().variation_san(board.move_stack))
