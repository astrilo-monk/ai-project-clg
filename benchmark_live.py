"""
Watch the Stockfish benchmark live in the browser.

Run with:  streamlit run benchmark_live.py

The same games as tests/benchmark.py (our engine vs Stockfish at a low skill
level), but every move is drawn on the board as it is played. Stockfish only
plays the other side; it never chooses our moves. Needs Stockfish installed
(see tests/benchmark.py). Local only: the free Streamlit Cloud has no Stockfish.
"""

import time

import chess
import chess.engine
import chess.svg
import streamlit as st

from engine.strong import search_best_move
from tests.benchmark import OPENINGS, STOCKFISH_MOVE_TIME, find_stockfish, play_game

st.set_page_config(page_title="Live Benchmark", page_icon="♟", layout="wide")
st.title("Live benchmark: our engine vs Stockfish")

with st.sidebar:
    st.header("Settings")
    version = st.radio("Our engine", ["New (Phase 5)", "Old (Phase 4)"], horizontal=True)
    if version.startswith("New"):
        think = st.select_slider("Thinking time per move (seconds)", [0.25, 0.5, 1.0, 2.0, 4.0], value=1.0,
                                 help="0.5 = Hard, 2 = Expert in the main app.")
        depth, our_search = 0, lambda b: search_best_move(b, time_limit=think, min_depth=3)
    else:
        depth = st.radio("Search depth", [2, 3, 4], index=1, horizontal=True,
                         help="What the main app used for Medium, Hard and Expert before Phase 5.")
        our_search = None  # play_game's default: the Phase 4 engine
    skill = st.slider("Stockfish skill level", 0, 20, 0, help="0 is the weakest, 20 is full strength.")
    openings = st.multiselect("Openings", list(OPENINGS), default=list(OPENINGS))
    delay = st.slider("Pause after each move (seconds)", 0.0, 2.0, 0.3, 0.1,
                      help="Only slows the display down so you can follow the game. Not counted in the timings.")
    start = st.button("Start", type="primary", disabled=not openings, use_container_width=True)

total = len(openings) * 2
st.caption(
    f"{total} games: each opening once with each colour. Stockfish gets {STOCKFISH_MOVE_TIME}s per move. "
    "Press Stop (top right) to end early."
)
if not start:
    st.info("Choose the settings in the sidebar and press Start.")
    st.stop()

try:
    stockfish_path = find_stockfish(None)
except SystemExit as e:
    st.error(f"{e} On Windows: winget install Stockfish.Stockfish")
    st.stop()

left, right = st.columns([3, 2], gap="large")
title_box = left.empty()
board_box = left.empty()
score_box = right.empty()
table_box = right.empty()
rows = []


def show_move(board: chess.Board, our_color: chess.Color) -> None:
    svg = chess.svg.board(board, orientation=our_color, size=480,
                          lastmove=board.peek() if board.move_stack else None,
                          check=board.king(board.turn) if board.is_check() else None)
    board_box.markdown(f'<div style="max-width:480px">{svg}</div>', unsafe_allow_html=True)
    time.sleep(delay)


def show_results() -> None:
    w = sum(r["result"] == "win" for r in rows)
    d = sum(r["result"] == "draw" for r in rows)
    l = sum(r["result"] == "loss" for r in rows)
    with score_box.container():
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Wins", w)
        c2.metric("Draws", d)
        c3.metric("Losses", l)
        c4.metric("Score", f"{100 * (w + 0.5 * d) / len(rows):.0f}%" if rows else "-",
                  help="Wins + half the draws, as a percentage of games played.")
    table_box.dataframe(
        [{"Opening": r["opening"], "We played": r["our_color"], "Result": r["result"], "How": r["reason"],
          "Half-moves": r["plies"], "Our avg time": f"{r['avg_move_seconds']}s"} for r in rows],
        hide_index=True, use_container_width=True,
    )


show_results()
sf = chess.engine.SimpleEngine.popen_uci(stockfish_path)
sf.configure({"Threads": 1, "Hash": 16})
try:
    for name in openings:
        for color in (chess.WHITE, chess.BLACK):
            side = "White" if color == chess.WHITE else "Black"
            title_box.subheader(f"Game {len(rows) + 1} of {total}: {name}, our engine is {side}")
            row = play_game(sf, depth, skill, OPENINGS[name], color, on_move=lambda b: show_move(b, color),
                            our_search=our_search)
            row["opening"] = name
            rows.append(row)
            show_results()
finally:
    sf.quit()  # also runs when you press Stop, so no Stockfish process is left behind

st.success(f"Done: {total} games played.")
