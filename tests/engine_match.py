"""
Matches between engine versions, and against Stockfish (Phase 5).

Players are written as  kind:setting
    old:D              the Phase 4 engine: alpha-beta + ordering + quiescence at depth D
    strong:T           engine/strong.py with T seconds per move
    strong:T:M         the same, but always finishing at least depth M (the app's Hard is strong:0.5:3)
    strong-oldeval:T   engine/strong.py with the ORIGINAL evaluation, to measure
                       the search and the evaluation improvements separately
    sf:S               Stockfish at Skill Level S (0 to 20), 0.05 s per move

Each match plays every opening twice (once with each colour), several games
at a time in separate processes.

Run:
    python -m tests.engine_match strong:0.5 old:3
    python -m tests.engine_match strong:1 sf:3 --workers 4
Output: one line per game, a summary, and docs/results/match_<A>_vs_<B>.csv
"""

import argparse
import csv
import math
from multiprocessing import Pool

import chess
import chess.engine

from engine.evaluate import evaluate
from engine.search import find_best_move
from engine.strong import search_best_move
from tests.benchmark import MAX_PLIES, OPENINGS, RESULTS_DIR, STOCKFISH_MOVE_TIME, find_stockfish

MATCH_OPENINGS = {
    **OPENINGS,
    "Ruy Lopez (1.e4 e5 2.Nf3 Nc6 3.Bb5)": ["e2e4", "e7e5", "g1f3", "b8c6", "f1b5"],
    "French (1.e4 e6)": ["e2e4", "e7e6"],
    "Caro-Kann (1.e4 c6)": ["e2e4", "c7c6"],
    "English (1.c4)": ["c2c4"],
    "King's Indian (1.d4 Nf6 2.c4 g6)": ["d2d4", "g8f6", "c2c4", "g7g6"],
}


def make_player(spec: str):
    """Turn 'kind:setting[:min_depth]' into a function board -> move. Opens Stockfish if needed."""
    kind, setting, *rest = spec.split(":")
    min_depth = int(rest[0]) if rest else 1
    if kind == "old":
        return lambda board: find_best_move(board, int(setting)).move, None
    if kind == "strong":
        return lambda board: search_best_move(board, float(setting), min_depth=min_depth).move, None
    if kind == "strong-oldeval":
        return lambda board: search_best_move(board, float(setting), evaluate_fn=evaluate,
                                              min_depth=min_depth).move, None
    if kind == "sf":
        sf = chess.engine.SimpleEngine.popen_uci(find_stockfish(None))
        sf.configure({"Threads": 1, "Hash": 16, "Skill Level": int(setting)})
        return lambda board: sf.play(board, chess.engine.Limit(time=STOCKFISH_MOVE_TIME)).move, sf
    raise ValueError(f"unknown player {spec!r}")


def play_one(job: tuple) -> dict:
    """One game. Runs in a worker process. Result is from player A's point of view."""
    spec_a, spec_b, opening_name, a_is_white = job
    a, sf_a = make_player(spec_a)
    b, sf_b = make_player(spec_b)
    try:
        board = chess.Board()
        for uci in MATCH_OPENINGS[opening_name]:
            board.push_uci(uci)
        a_color = chess.WHITE if a_is_white else chess.BLACK
        while not board.is_game_over(claim_draw=True) and len(board.move_stack) < MAX_PLIES:
            board.push((a if board.turn == a_color else b)(board))
    finally:
        for sf in (sf_a, sf_b):
            if sf:
                sf.quit()

    outcome = board.outcome(claim_draw=True)
    if outcome is None:
        result, reason = "draw", "move limit"
    elif outcome.winner is None:
        result, reason = "draw", outcome.termination.name.lower()
    else:
        result = "win" if outcome.winner == a_color else "loss"
        reason = outcome.termination.name.lower()
    return {"a": spec_a, "b": spec_b, "opening": opening_name, "a_color": "white" if a_is_white else "black",
            "result": result, "reason": reason, "plies": len(board.move_stack),
            "moves": chess.Board().variation_san(board.move_stack)}


def elo_difference(score: float) -> str:
    """Rating difference implied by a score fraction (standard Elo formula)."""
    if score <= 0 or score >= 1:
        return "out of range (all games won or lost)"
    return f"{-400 * math.log10(1 / score - 1):+.0f}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("a")
    parser.add_argument("b")
    parser.add_argument("--workers", type=int, default=4,
                        help="games at once. Keep below your CPU core count: time-limited engines get slower when the CPU is shared")
    args = parser.parse_args()

    jobs = [(args.a, args.b, name, a_white) for name in MATCH_OPENINGS for a_white in (True, False)]
    rows = []
    with Pool(args.workers) as pool:
        for row in pool.imap_unordered(play_one, jobs):
            rows.append(row)
            print(f"{row['opening']:38} A as {row['a_color']:5} | {row['result']:4} ({row['reason']}, {row['plies']} plies)",
                  flush=True)

    w = sum(r["result"] == "win" for r in rows)
    d = sum(r["result"] == "draw" for r in rows)
    l = sum(r["result"] == "loss" for r in rows)
    score = (w + 0.5 * d) / len(rows)
    print(f"\n{args.a} vs {args.b}: +{w} ={d} -{l}  score {100 * score:.0f}%  "
          f"Elo difference {elo_difference(score)}  ({len(rows)} games)")

    out = RESULTS_DIR / f"match_{args.a}_vs_{args.b}.csv".replace(":", "-")
    with open(out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
