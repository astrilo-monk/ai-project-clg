"""
Benchmark: our engine vs Stockfish at its weakest skill levels.

Stockfish is used ONLY as a measuring stick here, never to choose our moves.

Setup
    - Our engine: alpha-beta + move ordering + quiescence, at depths 2, 3, 4
      (the same settings as the app's Medium / Hard / Expert levels).
    - Stockfish 16 at "Skill Level" 0, 1 and 2 (out of 20), 0.05 s per move,
      1 thread. Low skill levels make Stockfish deliberately play weaker
      moves with some randomness.
    - 10 games per pairing: 5 different openings x both colours, so the games
      are not all identical and colour advantage is balanced.
    - A game still running after 200 half-moves is scored as a draw.

Install Stockfish:  Windows/Mac: download from https://stockfishchess.org
                    Ubuntu/Debian: sudo apt install stockfish

Run all (about 30 to 60 minutes):
    python -m tests.benchmark
Run a subset (e.g. in two terminals at once), then merge:
    python -m tests.benchmark --depths 4 --out docs/results/bench_d4.csv
    python -m tests.benchmark --depths 2 3 --out docs/results/bench_d23.csv
    python -m tests.benchmark --summarize docs/results/bench_d4.csv docs/results/bench_d23.csv
"""

import argparse
import csv
import os
import shutil
import statistics
import time
from pathlib import Path

import chess
import chess.engine

from engine.search import find_best_move

RESULTS_DIR = Path(__file__).resolve().parent.parent / "docs" / "results"

# Openings as move lists, so each pair of games starts from a different position.
OPENINGS = {
    "Start position": [],
    "Open Game (1.e4 e5)": ["e2e4", "e7e5"],
    "Queen's Pawn (1.d4 d5)": ["d2d4", "d7d5"],
    "Sicilian (1.e4 c5)": ["e2e4", "c7c5"],
    "Indian (1.d4 Nf6)": ["d2d4", "g8f6"],
}

MAX_PLIES = 200
STOCKFISH_MOVE_TIME = 0.05


def find_stockfish(path: str | None) -> str:
    candidates = [path, shutil.which("stockfish"), "/usr/games/stockfish", "/usr/local/bin/stockfish"]
    # Windows: `winget install Stockfish.Stockfish` unpacks it here.
    winget = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    candidates += sorted(str(p) for p in winget.glob("Stockfish*/**/stockfish*.exe"))
    for c in candidates:
        if c and Path(c).exists():
            return c
    raise SystemExit("Stockfish not found. Install it or pass --stockfish PATH.")


def play_game(sf: chess.engine.SimpleEngine, depth: int, skill: int, opening: list[str], our_color: chess.Color,
              on_move=None, our_search=None) -> dict:
    """
    Play one game. `on_move(board)`, if given, is called after every move (the live viewer uses it).
    `our_search(board)` replaces our engine's search, e.g. the Phase 5 engine; the default is the Phase 4 one.
    """
    if our_search is None:
        our_search = lambda b: find_best_move(b, depth, "alphabeta", use_ordering=True, use_quiescence=True)
    sf.configure({"Skill Level": skill})
    board = chess.Board()
    for uci in opening:
        board.push_uci(uci)

    our_times, our_nodes = [], []
    while not board.is_game_over(claim_draw=True) and len(board.move_stack) < MAX_PLIES:
        if board.turn == our_color:
            r = our_search(board)
            our_times.append(r.seconds)
            our_nodes.append(r.nodes)
            board.push(r.move)
        else:
            board.push(sf.play(board, chess.engine.Limit(time=STOCKFISH_MOVE_TIME)).move)
        if on_move:
            on_move(board)

    outcome = board.outcome(claim_draw=True)
    if outcome is None:
        result, reason = "draw", "move limit"
    elif outcome.winner is None:
        result, reason = "draw", outcome.termination.name.lower()
    else:
        result = "win" if outcome.winner == our_color else "loss"
        reason = outcome.termination.name.lower()

    return {
        "depth": depth,
        "skill": skill,
        "our_color": "white" if our_color == chess.WHITE else "black",
        "result": result,
        "reason": reason,
        "plies": len(board.move_stack),
        "avg_move_seconds": round(statistics.mean(our_times), 3) if our_times else 0,
        "avg_nodes": round(statistics.mean(our_nodes)) if our_nodes else 0,
        "pgn_moves": chess.Board().variation_san(board.move_stack),
    }


def game_key(depth, skill, opening, color: str) -> tuple:
    return (int(depth), int(skill), opening, color)


def run(depths: list[int], skills: list[int], stockfish_path: str, out: Path) -> list[dict]:
    # Resume: games already saved in `out` are kept and not replayed. A long run
    # can be stopped (or the computer restarted) and simply started again.
    rows = []
    if out.exists():
        with open(out) as f:
            rows = list(csv.DictReader(f))
        if rows:
            print(f"Resuming: {len(rows)} games already in {out}", flush=True)
    done = {game_key(r["depth"], r["skill"], r["opening"], r["our_color"]) for r in rows}

    sf = chess.engine.SimpleEngine.popen_uci(stockfish_path)
    sf.configure({"Threads": 1, "Hash": 16})
    try:
        for depth in depths:
            for skill in skills:
                for name, opening in OPENINGS.items():
                    for color in (chess.WHITE, chess.BLACK):
                        if game_key(depth, skill, name, "white" if color == chess.WHITE else "black") in done:
                            continue
                        t = time.perf_counter()
                        row = play_game(sf, depth, skill, opening, color)
                        row["opening"] = name
                        rows.append(row)
                        print(
                            f"depth {depth} vs skill {skill} | {name:24} | as {row['our_color']:5} | "
                            f"{row['result']:4} ({row['reason']}, {row['plies']} plies) | {time.perf_counter() - t:5.1f}s",
                            flush=True,
                        )
                        save_csv(rows, out)  # save after every game, so nothing is lost
    finally:
        sf.quit()
    return rows


FIELDS = ["depth", "skill", "opening", "our_color", "result", "reason", "plies", "avg_move_seconds", "avg_nodes", "pgn_moves"]


def save_csv(rows: list[dict], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def summarize(csv_paths: list[Path]) -> None:
    rows = []
    for p in csv_paths:
        with open(p) as f:
            rows.extend(csv.DictReader(f))

    all_csv = RESULTS_DIR / "benchmark_games.csv"
    if any(Path(p).resolve() != all_csv.resolve() for p in csv_paths):
        save_csv(rows, all_csv)

    depths = sorted({int(r["depth"]) for r in rows})
    skills = sorted({int(r["skill"]) for r in rows})
    lines = [
        "# Benchmark: Our Engine vs Stockfish (low skill levels)",
        "",
        f"Stockfish 16, Skill Level {', '.join(map(str, skills))} of 20, {STOCKFISH_MOVE_TIME}s per move, 1 thread. "
        f"Our engine: alpha-beta + ordering + quiescence. 5 openings x 2 colours per pairing. "
        f"Games over {MAX_PLIES} half-moves are scored as draws.",
        "",
        "Score = wins + 0.5 x draws, as a percentage of games played.",
        "",
        "| Our depth | Stockfish skill | Games | Wins | Draws | Losses | Score | Avg time per move | Avg nodes per move |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for d in depths:
        for s in skills:
            g = [r for r in rows if int(r["depth"]) == d and int(r["skill"]) == s]
            if not g:
                continue
            w = sum(r["result"] == "win" for r in g)
            dr = sum(r["result"] == "draw" for r in g)
            l = sum(r["result"] == "loss" for r in g)
            score = 100 * (w + 0.5 * dr) / len(g)
            t = statistics.mean(float(r["avg_move_seconds"]) for r in g)
            n = statistics.mean(float(r["avg_nodes"]) for r in g)
            lines.append(f"| {d} | {s} | {len(g)} | {w} | {dr} | {l} | {score:.0f}% | {t:.2f}s | {n:,.0f} |")

    lines += ["", "## Totals by depth", "", "| Our depth | Games | Wins | Draws | Losses | Score |", "|---|---|---|---|---|---|"]
    for d in depths:
        g = [r for r in rows if int(r["depth"]) == d]
        w = sum(r["result"] == "win" for r in g)
        dr = sum(r["result"] == "draw" for r in g)
        l = sum(r["result"] == "loss" for r in g)
        lines.append(f"| {d} | {len(g)} | {w} | {dr} | {l} | {100 * (w + 0.5 * dr) / len(g):.0f}% |")

    reasons = {}
    for r in rows:
        if r["result"] == "draw":
            reasons[r["reason"]] = reasons.get(r["reason"], 0) + 1
    if reasons:
        lines += ["", "Draw reasons: " + ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in sorted(reasons.items()))]

    lines += ["", "Every game's moves are in `benchmark_games.csv` (column `pgn_moves`), so any game can be replayed."]
    (RESULTS_DIR / "benchmark_summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--depths", type=int, nargs="+", default=[2, 3, 4])
    parser.add_argument("--skills", type=int, nargs="+", default=[0, 1, 2])
    parser.add_argument("--stockfish", default=None, help="path to the Stockfish executable")
    parser.add_argument("--out", type=Path, default=RESULTS_DIR / "benchmark_games.csv")
    parser.add_argument("--summarize", type=Path, nargs="+", help="merge CSV files and write the summary only")
    args = parser.parse_args()

    if args.summarize:
        summarize(args.summarize)
        return
    run(args.depths, args.skills, find_stockfish(args.stockfish), args.out)
    summarize([args.out])


if __name__ == "__main__":
    main()
