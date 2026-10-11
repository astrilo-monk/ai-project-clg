# AI Chess Assistant for Beginners: The Whole Project in One File

Read this before you present. It explains what the project is, how every part works, what the results are, and what you will be asked. Details live in `docs/JOURNAL.md` (architecture and history) and `docs/REPORT.md` (the formal report).

**Live app: https://chessassist.streamlit.app/** · **Code: https://github.com/astrilo-monk/ai-project-clg**

---

## 1. The 30-Second Pitch

> Beginners lose chess games to simple mistakes, and strong engines like Stockfish only show a number like "-3.2" that teaches them nothing. We built an AI that **plays against you**, **catches your mistakes**, and **explains them in plain English** with a better move. The chess engine (search and evaluation) is written from scratch; a library is only used for the rules of chess. It beats the weakest Stockfish settings, and our improved engine scores 42% against Stockfish at skill level 6.

Three ideas carry the whole project:
1. **Adversarial search** (minimax + alpha-beta) decides moves.
2. **A heuristic evaluation function** encodes chess knowledge.
3. **A rule-based expert system** turns engine numbers into explanations.

---

## 2. The Problem

- Beginners lose mostly to **tactical mistakes**: undefended pieces, missed captures, walking into checkmate.
- They rarely know **why** a move was bad. Human coaches cost money; engines give numbers, not reasons.
- **Goal:** an agent that (1) plays at an adjustable level, (2) detects the user's mistakes, (3) explains them in words a beginner understands.

**Golden rule of the project:** Stockfish is never used to choose our moves. It is only an opponent for benchmarking (and, in Phase 5, a judge for analysing our engine's blunders).

---

## 3. What the App Does

Live at https://chessassist.streamlit.app/, or run locally with `streamlit run app.py`.

| Feature | What the user sees |
|---|---|
| **Click-to-move board** | Click a piece: dots show where it can go, rings show captures. Click a dot to move. Last move highlighted, check in red, promotion picker |
| **4 difficulty levels** | Easy, Medium (beatable on purpose), Hard, Expert (the improved engine) |
| **Coach** | Every move you play gets a label: **Best / Good / Inaccuracy / Mistake / Blunder**, with chess symbols (!, ?!, ?, ??) |
| **Explanations** | "You moved your queen to h5, where it is undefended and can be captured for free. Your opponent can play Nxh5." |
| **Better move** | "Better was e5: it moves your pawn out of danger." Shown as a green arrow on a small board, your move as a red arrow |
| **Hint** | Best move with its reason: "Try Nf3: it develops your knight toward the center." |
| **Take back** | Undo your move and the engine's reply, to retry after a mistake |
| **Move history** | Your moves coloured by quality, with a summary like `Best 3 Good 5 Inaccuracy 1 Mistake 0 Blunder 1` |
| **Engine stats** | Evaluation, positions searched, thinking time |

Extra: `streamlit run benchmark_live.py` shows our engine playing Stockfish move by move in the browser.

---

## 4. Problem Formulation (the AI-course part)

Chess is a **two-player, zero-sum, deterministic, fully observable, sequential, discrete** game, so it is solved with **adversarial search**.

| Component | In this project |
|---|---|
| State | A board position: pieces, side to move, castling rights, en passant, move clocks (a FEN string) |
| Initial state | The standard starting position |
| Actions | All legal moves (about 35 on average) |
| Transition model | Play the move, get the new position |
| Terminal test | Checkmate, stalemate, insufficient material, threefold repetition, 50-move rule |
| Utility | Win +1, draw 0, loss -1 (in code: ±100,000, minus the distance to mate so faster mates are preferred) |
| Heuristic | Evaluation in centipawns (100 = one pawn) from White's point of view |

**PEAS:** Performance = win rate, positions searched, time per move, blunder-detection accuracy. Environment = board, human opponent, rules. Actuators = playing moves, showing hints and explanations. Sensors = the current position and the user's move.

**Why AI is needed:** about 10^120 possible games (Shannon number), so brute force is impossible; the opponent is intelligent, so fixed rules cannot anticipate it; positions must be *judged*, not just counted; and explaining *why* a move is bad is reasoning on top of search.

**Knowledge types:** declarative (rules, piece values), heuristic (piece-square tables: center control, development, king safety), procedural (how to search), meta-knowledge (what beginner mistakes look like).

---

## 5. Architecture

```
Layer 4  User interface      app.py (Streamlit) + board_component/index.html (clickable board)
            |          \
Layer 3  Teaching layer   assistant/blunder.py   move review: centipawn loss -> label
            |             assistant/explain.py   rule-based expert system -> sentences
            |             assistant/hints.py     best move + its reason
Layer 2  Engine (AI core) engine/search.py       minimax, alpha-beta, quiescence   (basic, exact)
                          engine/strong.py       enhanced engine for Hard/Expert   (Phase 5)
                          engine/ordering.py     MVV-LVA move ordering
                          engine/evaluate.py     evaluate() and evaluate_advanced()
Layer 1  Rules            python-chess           legal moves, check, mate, drawing
```

**Why layers matter:** the engine knows nothing about the UI, so the same engine runs in the app, the tests and the benchmarks. Each layer is tested on its own.

**One move, end to end:**
1. You click a piece and a square. The board sends the move to Python, which checks it is legal.
2. The coach searches the position before your move (depth 3) for the best move and its score.
3. It searches the position after your move (depth 2, same subtree) for your move's score.
4. Score difference = **centipawn loss** -> label.
5. The expert system matches rules and writes the explanation, better move and tips.
6. Your move is played; the engine replies at the chosen difficulty.

---

## 6. The Basic Engine (Phases 2 to 4)

### Minimax
White maximises, Black minimises. Leaves get the heuristic score; each node backs up the max or min of its children. Visits every node: cost about 35^depth.

### Alpha-beta pruning
- **alpha** = best score White is already guaranteed elsewhere; **beta** = best score Black is already guaranteed.
- When alpha >= beta, the opponent would never allow this line, so the remaining moves here are skipped.
- **Same answer as minimax, proven** (Knuth and Moore 1975) and checked by our tests. Best case cost about b^(d/2).

### Move ordering (MVV-LVA)
Alpha-beta prunes more when good moves come first. Captures first, "Most Valuable Victim, Least Valuable Attacker" (pawn takes queen before queen takes pawn), then promotions, then checks.

### Quiescence search
The **horizon effect**: stopping right after "queen takes pawn" misses the recapture. Quiescence keeps searching **captures only** past the depth limit until the position is quiet. "Stand pat": the side to move may decline to capture.

### Evaluation function
Material (P 100, N 320, B 330, R 500, Q 900) + **piece-square tables** (a bonus or penalty for each piece on each square: center knights good, "a knight on the rim is dim", castled king safe, advanced pawns good). From Michniewski's Simplified Evaluation Function. Colour-symmetric (tested).

---

## 7. The Enhanced Engine (Phase 5): `engine/strong.py`

Used only by **Hard and Expert**. Written in **negamax** form: since min(a, b) = -max(-a, -b), one branch replaces minimax's two by scoring from the side to move's view.

| Technique | One-line explanation |
|---|---|
| **Iterative deepening** | Search depth 1, 2, 3... until time runs out; each pass tells the next which move to try first; always has a move ready |
| **Minimum depth** | Hard always finishes depth 3, Expert depth 4, however busy the computer is |
| **Partial results** | If time runs out mid-depth, a move that already beat the previous best is proven better, so it is played |
| **Transposition table** | Dictionary of positions already searched (depth, score, exact/bound, best move); different move orders reach the same position |
| **Killer moves, history heuristic** | Quiet moves that caused cut-offs elsewhere are tried early |
| **Null-move pruning** | "Pass"; if we still beat beta, cut the line after a shallow search. Not in check, not with only king and pawns (zugzwang) |
| **Principal variation search** | After the first move, only ask "is this better?" with a zero-width window |
| **Late move reductions** | Late quiet moves are searched one ply shallower; re-searched if they surprise |
| **Check extension** | Search one ply deeper when in check |
| **Delta pruning** | In quiescence, skip captures that cannot lift the score to alpha even if free |
| **Repetition at the first repeat** | A repeated position counts as a draw, so a winning engine stops shuffling |

**Advanced evaluation (`evaluate_advanced()`):**
- **Tapered:** blends a middlegame score and an endgame score by game phase (24 = all pieces, 0 = kings and pawns).
- **Pawn structure:** passed pawns (bigger bonus the further advanced, doubled in endgame), doubled -15, isolated -15.
- **Pieces:** bishop pair +30, rook on open file +20, half-open file +10.
- **King shelter:** +10 per pawn in front of the king (middlegame).
- **Mop-up:** when a rook or more ahead, push the enemy king to the edge and bring our king closer, so it can actually checkmate (tested with king and queen vs king).
- **Speed:** profiling showed evaluation took 70% of the time. Bitmask reading, precomputed tables and a **pawn hash table** (cache of pawn-structure scores) made it about 1.7x faster.

**Why the coach does NOT use the enhanced engine:** the coach compares two searches. Null-move pruning and reductions are not exact, so the searches could disagree and blame good moves. A teaching tool must never be wrong, so the coach keeps the exact basic search. For the same reason the basic `minimax()` and `alphabeta()` stay untouched, so the Phase 2 comparison still reproduces.

---

## 8. The Coach (Phase 3)

### Move labels by centipawn loss
`loss = score of best move - score of played move` (from the mover's view), both searched at depth 3.

| Label | Loss | Symbol |
|---|---|---|
| Best | the engine's own move, or 0 | ! |
| Good | under 50 | |
| Inaccuracy | 50 to 99 | ?! |
| Mistake | 100 to 199 | ? |
| Blunder | 200 or more | ?? |

The engine decides **if** a move is bad; the rules explain **why**.

### Explanation rules (expert system)
| Rule | Example sentence |
|---|---|
| Walking into mate | "This move walks into checkmate: your opponent plays Qh4#." |
| Missed mate | "You missed a checkmate in one move, starting with Ra8#." |
| Moved piece hangs | "You moved your bishop to a6, where it is undefended and can be captured for free." |
| Defender moved away | "Your pawn on e5 is no longer protected after this move." |
| Missed capture | "You missed a free queen on d5 (Nxd5)." |
| Opening tips | early queen moves, king moves, knights on the edge |

### Null-move threat detection
Let the side to move "pass", then check whether the opponent would have mate in one. If your move removes that, the coach says so: "g6 stops your opponent's checkmate threat (Qxf7#)."

**Why rules and not machine learning?** Every sentence traces to one rule and one verifiable board fact. An ML model would need labelled explanation data (which does not exist freely) and could produce confident nonsense.

---

## 9. Results (the numbers to quote)

### Alpha-beta efficiency (Phase 2)
Total positions searched over 4 test positions, quiescence off so all variants search the same tree:

| Depth | Minimax | Alpha-beta | Alpha-beta + ordering | Saving |
|---|---|---|---|---|
| 2 | 3,627 | 1,320 | 461 | 87.3% |
| 3 | 117,954 | 15,895 | 4,296 | **96.4%** |
| 4 | not run (minutes) | 182,963 | 19,722 | ordering alone: 89.2% |

Identical scores every time (tested).

### Depth vs strength (Phase 4, Stockfish 16, skill 0 to 2, 90 games)
| Depth | Score |
|---|---|
| 2 (Medium) | 33% |
| 3 (Hard) | 65% |
| 4 (Expert) | **80%** |

16 of 17 draws were threefold repetitions: the engine had no endgame plan (fixed in Phase 5).

### Enhanced engine (Phase 5, Stockfish 19, 20 games per match)
| Match | Result |
|---|---|
| Enhanced vs basic engine | **75%** (13 W, 4 D, 3 L), about +190 Elo |
| New evaluation vs old evaluation, same search | **80%** |
| Expert vs Stockfish skill 6 | **12% -> 42%** (about +285 Elo) |
| Hard vs Stockfish skill 4 | 30% -> 42% |
| Hard vs Stockfish skill 6 | 15% -> 20% |

Search depth in 2 seconds: depth 4 to 8 (was a fixed 4 that could take 4 seconds).

**Honest caveat:** 20 games gives about ±10 points per score. The direction is consistent across every comparison, which is the reliable conclusion.

### Tests
25 automated tests pass (12 engine, 13 coach): alpha-beta equals minimax, mate in 1 and 2, free queen taken, poisoned pawn refused, evaluations symmetric, king-and-queen mate, Fool's Mate and Scholar's Mate explained, hanging pieces named correctly.

---

## 10. Good Stories for the Presentation (real problems and fixes)

These show engineering judgement. Professors like them.

1. **"Test your tests."** The mate-in-2 test failed twice, and both times the *test* was wrong (once the position had a mate in 1, once a rook could not reach its square).
2. **Vague coaching fixed with reasoning.** The coach once praised ...g6 as "improves your position". Adding null-move threat detection made it say "stops your opponent's checkmate threat (Qxf7#)".
3. **Restartable experiments.** The computer restarted after 55 of 90 benchmark games. Results were saved after every game, and resume support was added.
4. **Profile before optimising.** The first enhanced engine was barely deeper. A profiler showed evaluation took 70% of the time; fixing that gave 1.7x.
5. **Compare directly, not through a third party.** The new search with the OLD evaluation seemed better (88% vs 75% against the old engine). A direct match showed the new evaluation actually wins 80%: the gap was noise.
6. **Diagnose with evidence.** The first enhanced engine did worse against Stockfish skill 4 and 6. Full Stockfish analysed its 42 blunders; replaying them with pruning off did not help, but more time did. The cause was **time management**, not pruning. A minimum depth and keeping partial results fixed it (20% -> 42% at skill 4).
7. **Fair measurement.** Running 4 games at once starved the time-limited engine of CPU, while a fixed-depth engine just runs longer. Matches now run 3 at a time.

---

## 11. Design Decisions (and why)

| Chose | Over | Why |
|---|---|---|
| python-chess for rules | Writing move generation | Rules are not AI; weeks of work and bugs |
| Minimax with explicit MAX/MIN (basic engine) | Negamax | Matches the textbook, easier to explain |
| Negamax (enhanced engine) | MAX/MIN | Many extra steps per node; writing them twice would double the code |
| Alpha-beta kept separate from minimax | Only alpha-beta | Lets us measure the saving on identical trees |
| Coach at fixed depth 3, exact search | Coach at opponent's level | Consistent, never-wrong judging; about 1 second |
| Rule-based explanations | ML or a language model | Correct, predictable, traceable, no data needed |
| Time limit + minimum depth (Hard/Expert) | Fixed depth | Predictable waiting time; deeper in simple positions |
| Easy/Medium keep the basic engine | Weakened enhanced engine | Its mistakes are the human-like ones beginners can punish |
| Streamlit + small custom board component | pygame | Runs in a browser, deployable for free |
| Python | C++ | Readability over speed for a course project |
| MCTS, reinforcement learning rejected | | MCTS needs many random playouts (slow in Python, weak at tactics); RL needs millions of games and GPUs, and is a black box |

---

## 12. Limitations and Future Work

**Limitations (say them before you are asked):**
1. The coach sees 3 half-moves ahead, so it can misjudge long-term sacrifices (it calls the sound 4.Ng5 in the Two Knights an inaccuracy).
2. Explanations cover common patterns; forks, pins and skewers are not named yet.
3. Python searches about 25,000 positions per second; C engines search millions.
4. No opening book or endgame tablebases; several losses come from early opening mistakes.
5. Evaluation weights are textbook values, not tuned; no mobility term.
6. Pruning is not exact, which is why the coach does not use the enhanced engine.

**Future work:** name tactics (forks, pins, skewers), an opening book, endgame tablebases, tuned or learned evaluation weights, importing the user's own games (PGN) for review.

---

## 13. Demo Plan (5 minutes)

Before: app running (local, or the deployed link opened 10 minutes early so it is awake), Medium, coach on, playing White.

1. **0:00 Problem** (talk): beginners, numbers vs explanations, adversarial search from scratch.
2. **0:40 A blunder caught:** play e4, then Qh5 (hangs the queen). Show the red Blunder badge, the explanation, "Better was e5", and the red/green arrows board.
3. **1:40 Take back and Hint:** both moves disappear; Hint draws a green arrow with its reason.
4. **2:20 Checkmate threat:** describe the Scholar's Mate test: Nf6 walks into Qxf7#, g6 "stops your opponent's checkmate threat", found with a null move.
5. **3:10 Evidence:** the node chart (96.4% fewer at depth 3), the benchmark chart, Phase 5 results (Expert 12% -> 42% vs Stockfish skill 6). Run `python -m tests.test_engine` live.
6. **4:10 Limitations and close.**

Optional wow moment: `streamlit run benchmark_live.py` to show the engine playing Stockfish live (local only).

If something goes wrong: deployed app slow -> use local; Expert too slow -> switch to Medium; engine plays a different reply -> any hanging piece shows the same coach behaviour.

---

## 14. Viva Cheat Sheet

1. **Why adversarial search?** Every other move is chosen by an opponent trying to make us lose, so we assume their best reply. A* assumes we control every action.
2. **How does minimax work?** Search to a depth, score leaves heuristically, White takes the max, Black the min, play the best backed-up move.
3. **What does alpha-beta cut, and why is the result unchanged?** Moves at a node once alpha >= beta: the opponent already has something better elsewhere, so this line is never reached with best play. Our test proves equal scores.
4. **Why does ordering help?** Cut-offs happen as soon as a good enough move is found; searching captures first finds them early. 89.2% fewer nodes at depth 4.
5. **Your evaluation function?** Material + piece-square tables (basic); plus tapered phase, pawn structure, bishop pair, rook files, king shelter, mop-up (advanced).
6. **Horizon effect?** Misjudging because the refutation is just past the depth limit. Quiescence search continues with captures until quiet.
7. **How do you decide a blunder?** Centipawn loss at depth 3: 200 or more is a blunder, 100 to 199 a mistake, 50 to 99 an inaccuracy.
8. **Why not just use Stockfish?** Then there is no AI of our own. Stockfish is only a benchmark opponent and analysis judge.
9. **Iterative deepening, isn't it wasteful?** Each depth costs several times the previous, so repeats are cheap, and each pass orders the next for better pruning. A move is always ready.
10. **Transposition table?** A dictionary from positions to what we found (depth, score, exact or bound, best move), so transposed positions are searched once.
11. **Null-move pruning?** Pass the turn; if still above beta, a real move would be too, so cut. Unsafe in zugzwang, so not used with only king and pawns.
12. **Why doesn't the coach use the stronger engine?** Its pruning is not exact, so the coach's two searches could disagree and blame good moves.
13. **Limitations / future work?** Sections 12 above.

---

## 15. Glossary

| Term | Meaning |
|---|---|
| Ply | One half-move. Depth 3 = 3 plies |
| Centipawn | 1/100 of a pawn, the unit of all scores |
| Node | One position visited in the search |
| Heuristic | A rule of thumb that estimates rather than proves |
| Static evaluation | Scoring a position without looking ahead |
| Quiescence search | Searching captures past the depth limit until quiet |
| Horizon effect | Misjudging because the key move is just past the depth |
| MVV-LVA | Most Valuable Victim, Least Valuable Attacker |
| Negamax | Minimax written with one branch, using min(a, b) = -max(-a, -b) |
| Transposition | The same position reached by a different move order |
| Null move | Passing the turn (illegal in chess, used as a search trick) |
| Zugzwang | A position where any move makes things worse, so passing would be best |
| Elo | Rating scale; a 75% score means about +190 Elo |
| FEN / SAN | One-line position format / move notation like Nf3, exd5, Qh4# |
| Expert system | AI reasoning with hand-written if-then rules |

---

## 16. Where Everything Is

| Path | Contents |
|---|---|
| `app.py` | The Streamlit app |
| `board_component/index.html` | Click-to-move board (HTML + JavaScript); only allows legal moves Python sends it |
| `benchmark_live.py` | Watch the engine play Stockfish live |
| `engine/search.py` | Minimax, alpha-beta, quiescence (basic, exact) |
| `engine/strong.py` | Enhanced engine (Hard, Expert) |
| `engine/evaluate.py` | `evaluate()` and `evaluate_advanced()` |
| `engine/ordering.py` | MVV-LVA |
| `assistant/` | Coach: `blunder.py`, `explain.py`, `hints.py` |
| `tests/` | Tests, search comparison, Stockfish benchmark, engine matches, charts |
| `docs/formulation.md` | Phase 1 problem formulation |
| `docs/JOURNAL.md` | Architecture, every module, development log, viva answers |
| `docs/REPORT.md` | Final report |
| `docs/DEMO.md` | Full timed demo script |
| `docs/results/` | Charts, CSVs, every benchmark and match game |

**Commands**
```bash
streamlit run app.py                                   # the app
python -m tests.test_engine                            # 12 engine tests
python -m tests.test_assistant                         # 13 coach tests
python -m tests.compare_search                         # minimax vs alpha-beta table
python -m tests.engine_match strong:0.5 old:3 --workers 3   # new engine vs old
python -m tests.engine_match strong:2:4 sf:6 --workers 3    # Expert vs Stockfish skill 6
streamlit run benchmark_live.py                        # live games vs Stockfish
```

---

## 17. How It Was Built (be honest)

Built in phases: formulation and board, engine, coach, testing and report, then engine improvements and the clickable board. An AI coding assistant (Claude) helped write the code, and the git history and journal say so. If asked, say yes, then prove the understanding is yours: explain alpha-beta on the whiteboard, compute a centipawn loss by hand, and walk through one function line by line. A good self-test: delete `alphabeta()`, rewrite it yourself, and run `python -m tests.test_engine`.
