# 5-Minute Demo Script

Rehearse this at least twice. Every position below is reproducible, so nothing depends on luck.

## Before you start (10 minutes early)

- [ ] `streamlit run app.py` running locally, or https://chessassist.streamlit.app/ opened so it is awake
- [ ] Browser zoom at 100 to 110%, sidebar visible
- [ ] Difficulty on **Medium**, Coach mode **on**, playing **White**
- [ ] `docs/results/chart_nodes.png` and `chart_benchmark.png` open in another tab
- [ ] Terminal ready with `python -m tests.test_engine` typed but not run

---

## 0:00 to 0:40: The problem (talk, no clicking)

> "Beginners lose chess games to simple mistakes and engines like Stockfish only show a number like minus 3.2. We built an AI that plays against you, detects your mistakes and explains them in plain English. We formulated chess as a two-player, zero-sum, adversarial search problem. The engine, search and evaluation are written from scratch; we only use a library for the rules of chess."

## 0:40 to 1:40: A blunder, caught and explained

1. Play **e4**. The coach shows a grey **Good** badge. Engine replies (on Medium it plays **Nf6**).
2. Play **Qh5**. This hangs the queen to the knight.
3. Point at the coach panel:
   - Red **Blunder** badge, "This costs you about 8.5 pawns"
   - "You moved your queen to h5, where it is undefended and can be captured for free. Your opponent can play Nxh5."
   - "Better was e5: it moves your pawn out of danger."
   - Tip about bringing the queen out early
4. Open **Show the position before your move**: red arrow = your move, green arrow = the better move.

> "The engine decides IF a move is bad by comparing it with its own best move. That difference is called centipawn loss. A rule-based expert system then explains WHY."

## 1:40 to 2:20: Take back and hint

1. Click **Take back**. Both moves disappear.
2. Click **Hint**. A green arrow appears with "Try e5: it moves your pawn out of danger."

> "A coach doesn't just say what to play, it says why."

## 2:20 to 3:10: Checkmate threat (the best moment)

Click **New game**, choose **Black** in "Play as" if you want, but the quickest version is to describe the test:

> "Here is the Scholar's Mate trap. White threatens Qxf7 checkmate. If the player answers Nf6, the coach says: 'This move walks into checkmate: your opponent plays Qxf7#', and suggests g6, because it 'stops your opponent's checkmate threat'. It finds threats by letting the opponent move twice, a technique called a null move."

(If you want it live: run `python -m tests.test_assistant` and point at `test_scholars_mate_defence_is_explained` passing.)

## 3:10 to 4:10: Evidence

1. Show **chart_nodes.png**.

> "Minimax searches every position. Alpha-beta pruning skips branches that cannot change the decision. With move ordering it searched 96% fewer positions at depth 3, and returned the identical result every time. Our tests prove that."

2. Show **chart_benchmark.png** and say the real score from `docs/results/benchmark_summary.md`.

3. Run `python -m tests.test_engine` live: 9 tests pass in a few seconds.

## 4:10 to 5:00: Honest limitations and close

> "Limitations: the coach looks 3 half-moves ahead, so it can misjudge long-term sacrifices; the evaluation does not yet understand king safety or pawn structure; and Python limits us to depth 4. Next steps would be a transposition table, iterative deepening, and detecting named tactics like forks and pins."

> "To summarise: adversarial search, a heuristic evaluation function, and an expert system working together to teach, not just to play."

---

## If something goes wrong

| Problem | What to do |
|---|---|
| Deployed app is asleep or slow | Switch to the local version |
| Engine takes long on Expert | Say "Expert searches 4 half-moves deep, around 40,000 positions per move in Python" and switch to Medium |
| Engine plays a different reply than expected | Everything still works: any hanging-piece blunder shows the same coach behaviour. Try putting a piece where a pawn can take it |
| Asked "did you use AI tools?" | Answer honestly, then show you understand the code by explaining alpha-beta on the whiteboard |
