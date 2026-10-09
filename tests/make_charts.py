"""
Charts for the final report, built from the CSV results.

    python -m tests.make_charts

Reads:  docs/results/search_comparison.csv   (from tests.compare_search)
        docs/results/benchmark_games.csv     (from tests.benchmark, optional)
Writes: docs/results/chart_nodes.png
        docs/results/chart_time.png
        docs/results/chart_benchmark.png
"""

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RESULTS = Path(__file__).resolve().parent.parent / "docs" / "results"

# Colour-blind-checked categorical palette (validated: CVD dE >= 9.2, normal >= 27.6).
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
MARKERS = ["o", "s", "^"]
SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
GRID = "#e4e3df"

VARIANT_LABELS = {
    "minimax": "Minimax",
    "alphabeta": "Alpha-beta",
    "alphabeta+ordering": "Alpha-beta + move ordering",
}


def style(ax, title: str, subtitle: str) -> None:
    ax.set_facecolor(SURFACE)
    ax.figure.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=TEXT_2, labelsize=10)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.figure.text(0.07, 0.95, title, fontsize=14, fontweight="bold", color=TEXT, ha="left")
    ax.figure.text(0.07, 0.905, subtitle, fontsize=10, color=TEXT_2, ha="left")


def read_comparison():
    totals = defaultdict(lambda: defaultdict(float))  # variant -> depth -> value
    times = defaultdict(lambda: defaultdict(float))
    with open(RESULTS / "search_comparison.csv") as f:
        for r in csv.DictReader(f):
            totals[r["variant"]][int(r["depth"])] += int(r["nodes"])
            times[r["variant"]][int(r["depth"])] += float(r["seconds"])
    return totals, times


def line_chart(data, filename: str, title: str, subtitle: str, ylabel: str, fmt) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    fig.subplots_adjust(top=0.82, right=0.72, left=0.12, bottom=0.12)
    for i, (variant, label) in enumerate(VARIANT_LABELS.items()):
        depths = sorted(data[variant])
        values = [data[variant][d] for d in depths]
        ax.plot(depths, values, color=SERIES[i], linewidth=2, marker=MARKERS[i], markersize=8,
                markeredgecolor=SURFACE, markeredgewidth=2, label=label)
        # Direct label at the end of each line (identity never by colour alone).
        ax.annotate(f"{label}\n{fmt(values[-1])}", (depths[-1], values[-1]), xytext=(10, 0),
                    textcoords="offset points", va="center", fontsize=9.5, color=TEXT)
    ax.set_yscale("log")
    ax.set_xticks([1, 2, 3, 4])
    ax.set_xlabel("Search depth (half-moves)", color=TEXT_2)
    ax.set_ylabel(ylabel, color=TEXT_2)
    ax.legend(frameon=False, fontsize=9, loc="upper left", labelcolor=TEXT)
    style(ax, title, subtitle)
    fig.savefig(RESULTS / filename, dpi=160)
    plt.close(fig)


def benchmark_chart() -> bool:
    path = RESULTS / "benchmark_games.csv"
    if not path.exists():
        return False
    score = defaultdict(lambda: [0.0, 0])  # (depth, skill) -> [points, games]
    with open(path) as f:
        for r in csv.DictReader(f):
            key = (int(r["depth"]), int(r["skill"]))
            score[key][0] += {"win": 1, "draw": 0.5, "loss": 0}[r["result"]]
            score[key][1] += 1
    depths = sorted({d for d, _ in score})
    skills = sorted({s for _, s in score})

    fig, ax = plt.subplots(figsize=(8, 5))
    fig.subplots_adjust(top=0.82, left=0.1, bottom=0.12)
    width = 0.8 / len(skills)
    for i, s in enumerate(skills):
        xs, ys = [], []
        for j, d in enumerate(depths):
            if (d, s) in score:
                pts, n = score[(d, s)]
                xs.append(j + (i - (len(skills) - 1) / 2) * width)
                ys.append(100 * pts / n)
        bars = ax.bar(xs, ys, width=width - 0.03, color=SERIES[i], label=f"Stockfish skill {s}")
        for b, y in zip(bars, ys):
            ax.text(b.get_x() + b.get_width() / 2, y + 1.5, f"{y:.0f}%", ha="center", fontsize=9, color=TEXT)
    ax.axhline(50, color=TEXT_2, linewidth=1, linestyle=(0, (4, 3)))
    ax.text(-0.45, 52, "50% = even match", fontsize=8.5, color=TEXT_2, ha="left")
    ax.set_xticks(range(len(depths)), [f"Depth {d}" for d in depths])
    ax.set_ylim(0, 105)
    ax.set_ylabel("Score (win = 1, draw = 0.5)", color=TEXT_2)
    ax.legend(frameon=False, fontsize=9, loc="upper left", labelcolor=TEXT, ncols=len(skills))
    n_games = score[(depths[0], skills[0])][1]
    style(ax, "Our engine vs Stockfish at its lowest skill levels",
          f"{n_games} games per bar: 5 openings x both colours. Higher is better for our engine.")
    fig.savefig(RESULTS / "chart_benchmark.png", dpi=160)
    plt.close(fig)
    return True


def main() -> None:
    totals, times = read_comparison()
    line_chart(totals, "chart_nodes.png",
               "Alpha-beta and move ordering cut the search tree",
               "Positions searched, total over 4 test positions (log scale). Same best score in every case.",
               "Nodes searched (log scale)", lambda v: f"{v:,.0f}")
    line_chart(times, "chart_time.png",
               "Time to choose a move",
               "Seconds, total over 4 test positions (log scale). Minimax depth 4 not run: minutes per position.",
               "Seconds (log scale)", lambda v: f"{v:.2f}s")
    print("Saved chart_nodes.png, chart_time.png")
    if benchmark_chart():
        print("Saved chart_benchmark.png")
    else:
        print("No benchmark_games.csv yet, skipped chart_benchmark.png")


if __name__ == "__main__":
    main()
