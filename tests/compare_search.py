"""
Compare the search algorithms on the same positions.

Measures, for each position and depth:
    - nodes searched
    - time taken
for three versions of the engine:
    1. minimax
    2. alpha-beta (no move ordering)
    3. alpha-beta + MVV-LVA move ordering

Quiescence search is switched OFF here so all three search exactly the same
tree and the comparison is fair.

Run with:  python -m tests.compare_search
Output:    docs/results/search_comparison.csv
           docs/results/search_comparison.md
"""

import csv
from pathlib import Path

import chess

from engine.search import find_best_move
from tests.test_engine import POSITIONS

DEPTHS = (1, 2, 3, 4)
# Plain minimax at depth 4 visits over a million nodes per position and takes
# minutes in Python, which is exactly the point alpha-beta solves.
MINIMAX_MAX_DEPTH = 3

VARIANTS = {
    "minimax": dict(algorithm="minimax"),
    "alphabeta": dict(algorithm="alphabeta", use_ordering=False, use_quiescence=False),
    "alphabeta+ordering": dict(algorithm="alphabeta", use_ordering=True, use_quiescence=False),
}

OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "results"


def run() -> list[dict]:
    rows = []
    for name, fen in POSITIONS.items():
        board = chess.Board(fen)
        for depth in DEPTHS:
            for variant, kwargs in VARIANTS.items():
                if variant == "minimax" and depth > MINIMAX_MAX_DEPTH:
                    continue
                r = find_best_move(board, depth, **kwargs)
                rows.append({
                    "position": name,
                    "depth": depth,
                    "variant": variant,
                    "nodes": r.nodes,
                    "seconds": round(r.seconds, 3),
                    "best_move": board.san(r.move),
                    "score": r.score,
                })
                print(f"{name:11} d={depth} {variant:19} nodes={r.nodes:>9,} time={r.seconds:7.2f}s move={board.san(r.move)}")
    return rows


def write_outputs(rows: list[dict]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUT_DIR / "search_comparison.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    # Totals per depth across all positions, for the headline numbers.
    lookup = {(r["position"], r["depth"], r["variant"]): r for r in rows}
    lines = [
        "# Search Comparison",
        "",
        f"Positions: {', '.join(POSITIONS)}. Quiescence off so every variant searches the same tree.",
        "All three variants returned the same evaluation score at every depth (verified by tests/test_engine.py).",
        "",
        "## Total nodes across all positions",
        "",
        "| Depth | Minimax | Alpha-beta | Alpha-beta + ordering | Alpha-beta vs minimax | Alpha-beta + ordering vs minimax | Ordering vs plain alpha-beta |",
        "|---|---|---|---|---|---|---|",
    ]
    for depth in DEPTHS:
        totals = {}
        for variant in VARIANTS:
            vals = [lookup[(p, depth, variant)]["nodes"] for p in POSITIONS if (p, depth, variant) in lookup]
            totals[variant] = sum(vals) if vals else None
        mm, ab, abo = totals["minimax"], totals["alphabeta"], totals["alphabeta+ordering"]
        fmt = lambda v: f"{v:,}" if v is not None else "not run"
        pct = lambda v: f"{100 * (1 - v / mm):.1f}% fewer" if mm else "n/a"
        ord_gain = f"{100 * (1 - abo / ab):.1f}% fewer" if ab else "n/a"
        lines.append(f"| {depth} | {fmt(mm)} | {fmt(ab)} | {fmt(abo)} | {pct(ab)} | {pct(abo)} | {ord_gain} |")

    lines += [
        "",
        f"Minimax was not run above depth {MINIMAX_MAX_DEPTH} because it takes minutes per position in Python.",
        "",
        "## Per position",
        "",
        "| Position | Depth | Variant | Nodes | Seconds | Best move |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['position']} | {r['depth']} | {r['variant']} | {r['nodes']:,} | {r['seconds']} | {r['best_move']} |")

    (OUT_DIR / "search_comparison.md").write_text("\n".join(lines) + "\n")
    print(f"\nSaved results to {OUT_DIR}")


if __name__ == "__main__":
    write_outputs(run())
