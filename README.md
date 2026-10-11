# AI Chess Assistant for Beginners

**Live app: https://chessassist.streamlit.app/**

A chess engine we wrote from scratch, plus a coach that watches your moves and tells you, in plain English, what you did wrong and what you should have played instead.

We built this for our AI course. The idea came from a simple frustration: when you're learning chess and you lose a piece, Stockfish will happily tell you the position is "-3.2", which is useless if you don't know *why*. So we wanted something that plays against you at your level, catches the blunder, and explains it like a friend who's a bit better at chess would.

The engine itself (search and evaluation) is all our own code. We only use the `python-chess` library for the rules (legal moves, check, checkmate), and Stockfish only shows up as an opponent to benchmark against.

## What it does

- **Play on a real board.** Click a piece and it shows you every square it can go to (rings mean captures). Click a square to move. You can also click any of the engine's pieces to see where *they* can go (blue dots).
- **Four difficulty levels.** Easy and Medium are deliberately beatable. Hard and Expert use our improved engine.
- **A coach that reviews every move.** Each move gets a label: Best, Good, Inaccuracy, Mistake or Blunder.
- **Explanations, not numbers.** Things like *"You moved your queen to h5, where it is undefended and can be captured for free. Your opponent can play Nxh5."* plus the better move drawn as an arrow.
- **Hints** that come with a reason ("Try Nf3: it develops your knight toward the center").
- **Take back**, so you can try again after a blunder.
- **Step through the game** with ⏮ ◀ ▶ ⏭ under the board, to look at what each side just played without undoing anything.
- **Move history** coloured by how good each of your moves was.

## How it works (short version)

```
app.py + board_component/     the web app and the clickable board
assistant/                    the coach: judges moves, explains them, gives hints
engine/                       the AI: search + evaluation
python-chess                  the rules of chess
```

**The engine.** Chess is a two-player, zero-sum game, so we treat it as an adversarial search problem:

- **Minimax** with **alpha-beta pruning** to look ahead.
- **MVV-LVA move ordering**, so captures get searched first and alpha-beta prunes more.
- **Quiescence search**, to deal with the horizon effect.
- An **evaluation function** built from material plus piece-square tables.

For Hard and Expert we later added the techniques real engines use: iterative deepening, a transposition table, null-move pruning, principal variation search, late move reductions, killer moves, and a richer evaluation (pawn structure, king safety, endgame mop-up).

**The coach.** To judge your move, it asks the engine two questions:

1. What's the best move here?
2. How good is the move you played?

The difference, in hundredths of a pawn ("centipawns"), gives the label. A 200+ drop is a blunder. Then a rule-based expert system figures out *why* the move was bad: you hung a piece, walked into mate, missed a free capture, and so on. We used rules instead of ML on purpose: a teaching tool should never confidently explain something wrong.

## Results

- **Alpha-beta + move ordering searched 96.4% fewer positions** than plain minimax at depth 3, with exactly the same result every time.
- **Against Stockfish 16 at its weakest settings (90 games):** 33% at depth 2, 65% at depth 3, 80% at depth 4.
- **The improved engine beat our original one 75%** of the time head to head.
- **Expert vs Stockfish 19 at skill level 6:** went from 12% to 42% after the improvements.

All the numbers, tables and the story behind them are in [`docs/JOURNAL.md`](docs/JOURNAL.md) and [`docs/REPORT.md`](docs/REPORT.md).

## Running it locally

You need Python 3.10 or newer.

```bash
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # Mac / Linux
pip install -r requirements.txt

streamlit run app.py
```

## Tests and experiments

```bash
python -m tests.test_engine        # 12 engine tests
python -m tests.test_assistant     # 13 coach tests
python -m tests.compare_search     # minimax vs alpha-beta node counts
python -m tests.make_charts        # charts for the report
```

These need Stockfish installed (`winget install Stockfish.Stockfish` on Windows, `sudo apt install stockfish` on Linux):

```bash
python -m tests.benchmark                                   # original benchmark, 30 to 60 min
python -m tests.engine_match strong:0.5 old:3 --workers 3   # new engine vs old engine
python -m tests.engine_match strong:2:4 sf:6 --workers 3    # Expert vs Stockfish skill 6
streamlit run benchmark_live.py                             # watch our engine play Stockfish live
```

## Project layout

```
app.py                     Streamlit app
board_component/           click-to-move board (plain HTML + JavaScript, no build step)
benchmark_live.py          live engine-vs-Stockfish viewer
engine/
  evaluate.py              evaluation functions (basic and advanced)
  search.py                minimax, alpha-beta, quiescence (the textbook version)
  strong.py                improved engine used on Hard and Expert
  ordering.py              MVV-LVA move ordering
assistant/
  blunder.py               move review: centipawn loss -> label
  explain.py               rule-based explanations
  hints.py                 hints with reasons
tests/                     tests, benchmarks, matches, chart scripts
docs/
  formulation.md           problem formulation (state, actions, PEAS...)
  JOURNAL.md               how everything works + our development log
  REPORT.md                final report
  DEMO.md                  5-minute demo script
  results/                 CSVs, tables, charts, every benchmark game
gist.md                    the whole project on one page, for presenting
```

## Deployment

The live app runs on Streamlit Community Cloud (free) straight from this repo's `main` branch. Every push to `main` redeploys it. If the app has been idle for a while, it goes to sleep and takes about 30 seconds to wake up on the first visit.

## What we'd add next

- Naming tactics in explanations (forks, pins, skewers)
- An opening book (a lot of our engine's losses start with an early opening mistake)
- Tuning the evaluation weights on real games instead of using textbook values
- Letting you upload your own games (PGN) and have the coach review them

## Credits

- [python-chess](https://python-chess.readthedocs.io) for the rules and board drawing
- [Stockfish](https://stockfishchess.org), only as a benchmark opponent, never to pick our moves
- Piece values and piece-square tables from Tomasz Michniewski's *Simplified Evaluation Function* (Chess Programming Wiki)
- We used an AI coding assistant (Claude) while building this; the commit history and the journal say where.
