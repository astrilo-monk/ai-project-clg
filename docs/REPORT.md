# AI Chess Assistant for Beginner Players

**Course project report: Artificial Intelligence**

Group members: ____________________ (fill in names and roll numbers)

Repository: https://github.com/astrilo-monk/ai-project-clg

---

## Abstract

Beginner chess players lose most games to simple tactical errors, yet existing engines report only a numerical evaluation that beginners cannot interpret. We present an AI chess assistant that plays against the user at four difficulty levels, judges every move the user makes, and explains mistakes in plain English. The system combines **adversarial search** (minimax with alpha-beta pruning, MVV-LVA move ordering and quiescence search), a **heuristic evaluation function** (material and piece-square tables), and a **rule-based expert system** that converts engine output into explanations. Alpha-beta pruning with move ordering searched **96.4% fewer positions** than plain minimax at depth 3 while returning identical results. Against Stockfish 16 at its three lowest skill levels (90 games), the engine's score rose with search depth from 33% at depth 2 to 65% at depth 3 and 80% at depth 4. A suite of 22 automated tests verifies the engine's correctness and the coach's explanations, including detection of the Fool's Mate and Scholar's Mate patterns.

---

## 1. Introduction

### 1.1 Problem

A beginner who blunders a piece usually does not know which move was the mistake, what the better move was, or why. Human coaches are expensive. Strong engines such as Stockfish play far above human level, but they communicate through numbers ("-3.2") and long move sequences, which do not teach a beginner anything.

### 1.2 Objectives

1. Build a chess-playing agent from scratch using classical AI search.
2. Let the user play against it at adjustable strength.
3. Automatically classify every user move as Best, Good, Inaccuracy, Mistake or Blunder.
4. Explain mistakes in plain language and suggest a better move with its reason.
5. Evaluate the system experimentally.

### 1.3 Scope

In scope: a web interface, an engine written from scratch, a move-review and explanation layer, hints, take-back, and an experimental evaluation. Out of scope: opening books, endgame tablebases, machine-learned evaluation, time controls and online play.

---

## 2. Problem Formulation

Chess is formulated as a **two-player, zero-sum, deterministic, fully observable game**, solved by **adversarial search**.

| Component | Definition |
|---|---|
| Initial state | Standard starting position, White to move |
| State | Piece placement, side to move, castling rights, en passant square, halfmove clock |
| PLAYER(s) | The side to move |
| ACTIONS(s) | All legal moves (about 35 on average) |
| RESULT(s, a) | The position after playing move a |
| TERMINAL(s) | Checkmate, stalemate, insufficient material, threefold repetition, 50-move rule |
| UTILITY(s) | +1 White wins, 0 draw, -1 Black wins (implemented as ±100000 minus distance to mate) |
| EVAL(s) | Heuristic estimate in centipawns from White's point of view, used at the depth limit |

### 2.1 PEAS

| | |
|---|---|
| Performance | Win rate against reference opponents, nodes searched, time per move, correctness of move classification, clarity of explanations |
| Environment | 8x8 board, the rules of chess, a human opponent |
| Actuators | Playing a move; displaying grades, explanations, hints and arrows |
| Sensors | The current position and the move the user played |

### 2.2 Environment properties

Fully observable, multi-agent and competitive, deterministic, sequential, static, discrete, known.

The full formulation is in `docs/formulation.md`.

---

## 3. Knowledge Representation

| Knowledge type | Content | Representation |
|---|---|---|
| Declarative | Rules of chess | python-chess board model and legal move generator |
| Declarative | Piece values (P 100, N 320, B 330, R 500, Q 900) | Constant table |
| Heuristic | Positional principles: centralise knights, control the center, castle, activate the king in the endgame, push passed pawns | Six 64-entry piece-square tables, with separate middlegame and endgame king tables |
| Procedural | How to look ahead and prune | Search algorithms |
| Expert (teaching) | What beginner mistakes look like and how to describe them | If-then rules in `assistant/explain.py` |

---

## 4. Why AI Is Appropriate

1. **Search space.** With a branching factor of about 35 and games of about 80 plies, chess has around 10^120 possible games (Shannon, 1950). Exhaustive search is impossible, so depth-limited heuristic search is required.
2. **An adversary.** The opponent's moves are chosen to defeat us, which fixed rules cannot anticipate; the agent must reason about the opponent's best replies.
3. **Judgement under uncertainty about the future.** Positions must be evaluated before the game ends, which requires encoded domain knowledge.
4. **Explanation.** Teaching requires reasoning about why one move is worse than another, not only choosing a move.

---

## 5. Techniques

### 5.1 Minimax

```
function MINIMAX(s, depth):
    if TERMINAL(s): return UTILITY(s)
    if depth = 0:   return EVAL(s)
    if PLAYER(s) = White: return max over a in ACTIONS(s) of MINIMAX(RESULT(s, a), depth - 1)
    else:                 return min over a in ACTIONS(s) of MINIMAX(RESULT(s, a), depth - 1)
```

Minimax is complete and optimal against a perfect opponent within its depth limit, but its cost grows as b^d.

### 5.2 Alpha-beta pruning

Alpha (best value guaranteed to MAX) and beta (best value guaranteed to MIN) are passed down the tree; when alpha ≥ beta the remaining children of a node are skipped. The result is provably identical to minimax (Knuth and Moore, 1975). With perfect move ordering the cost falls from b^d to about b^(d/2).

### 5.3 Move ordering (MVV-LVA)

Captures are searched first, ordered by Most Valuable Victim, Least Valuable Attacker (score = 10 × victim value − attacker value), then promotions, then checks. Better ordering produces earlier cut-offs.

### 5.4 Quiescence search

At depth 0 the search continues through captures only until the position is quiet, using the static evaluation as a "stand pat" bound. This reduces the **horizon effect**, where the engine stops searching just before a recapture.

### 5.5 Mate-distance scoring

Checkmate is scored as MATE − ply, so the engine prefers faster mates when winning and slower ones when losing.

### 5.6 Move review by centipawn loss

```
best  = SEARCH(position, depth 3)                     # best move and its score
after = RESULT(position, played move)
value = SEARCH(after, depth 2)                         # same subtree, one ply already played
loss  = max(0, score(best) − score(played))            # from the player's point of view
label = Best (same move) | Good (<50) | Inaccuracy (50–99) | Mistake (100–199) | Blunder (≥200)
```

### 5.7 Rule-based expert system for explanations

The engine decides whether a move is bad; rules explain why. Rules fire only on moves the engine has already labelled inaccuracy, mistake or blunder:

| Rule | Condition |
|---|---|
| Walking into mate | The played move's value is a forced mate for the opponent |
| Missed mate | The best move's value was a forced mate for the player |
| Piece lost | The opponent's best reply captures material; subcases for the moved piece, a piece whose defender moved away, and other pieces |
| Hanging piece | A piece is attacked and undefended, or attacked by a cheaper piece |
| Missed capture | The best move captured an undefended piece |
| Opening tips | Early queen moves, king moves that lose castling rights, knights on the edge |

To explain good moves, threats are detected with a **null move**: the side to move "passes", and the system checks whether the opponent would then have a mate in one.

Rules were chosen over machine learning because a teaching tool must never give a wrong explanation, every sentence must be traceable to a fact about the board, and no labelled dataset of chess explanations is freely available.

---

## 6. System Design

The system has four layers; each only depends on the layers below it.

| Layer | Module | Responsibility |
|---|---|---|
| 4. Interface | `app.py` (Streamlit) | Board, move input, coach panel, hints, take back, move history |
| 3. Assistant | `assistant/blunder.py`, `explain.py`, `hints.py` | Judge moves, explain them, suggest moves |
| 2. Engine | `engine/search.py`, `ordering.py`, `evaluate.py` | Search and evaluation |
| 1. Rules | python-chess | Legal moves, terminal tests, board drawing |

When the user plays a move, the assistant runs two engine searches to review it, the expert system produces feedback, the move is played, and the engine replies at the selected difficulty. Diagrams of this flow are in `docs/JOURNAL.md`, section 2.

### 6.1 Difficulty levels

| Level | Depth | Quiescence |
|---|---|---|
| Easy | 1 | Off |
| Medium | 2 | On |
| Hard | 3 | On |
| Expert | 4 | On |

The coach always reviews at depth 3, so the user's moves are judged consistently at every difficulty.

---

## 7. Implementation

- Language: Python 3.10+
- Libraries: python-chess (rules and board drawing), Streamlit (web interface), matplotlib (charts), Stockfish 16 (benchmark opponent only)
- Size: about 2,000 lines of Python across engine, assistant, interface and tests (counted with `wc -l`)
- Running: `pip install -r requirements.txt` then `streamlit run app.py`

---

## 8. Experimental Evaluation

### 8.1 Correctness

22 automated tests (`tests/test_engine.py`, `tests/test_assistant.py`) all pass. They verify, among other things:

- The evaluation is exactly 0 in the starting position and changes sign when colours are swapped.
- **Alpha-beta, with and without move ordering, returns the same score as minimax** on four positions at depths 1 to 3.
- Mate in 1 is found for both colours, and mate in 2 is found and scored correctly.
- The engine captures a free queen and refuses a pawn capture that loses its queen.
- The coach labels a hanging bishop, a missed free queen, the Fool's Mate (...Qh4#) and a missed back-rank mate as blunders, with the correct squares and moves in the explanation.
- The coach praises a mating move as Best and explains that ...g6 stops the Scholar's Mate threat Qxf7#.

### 8.2 Search efficiency

Total nodes over four test positions (start, Italian opening, middlegame, endgame), quiescence off so all variants search the same tree:

| Depth | Minimax | Alpha-beta | Alpha-beta + ordering | Reduction vs minimax |
|---|---|---|---|---|
| 1 | 113 | 113 | 113 | 0% |
| 2 | 3,627 | 1,320 | 461 | 87.3% |
| 3 | 117,954 | 15,895 | 4,296 | 96.4% |
| 4 | not run | 182,963 | 19,722 | ordering vs plain alpha-beta: 89.2% |

![Nodes searched](results/chart_nodes.png)

![Time per move](results/chart_time.png)

The growth rates match theory: each extra ply multiplies minimax's work by roughly the branching factor (about 32x from depth 2 to 3), whereas alpha-beta with ordering grows by about 9x and 4.6x per ply, consistent with the b^(d/2) best case.

### 8.3 Playing strength against Stockfish

Our engine played Stockfish 16 at Skill Levels 0, 1 and 2 (out of 20; 0.05 s per move, 1 thread). Each pairing is 10 games: 5 openings, each played once with each colour, because our engine is deterministic and would otherwise repeat games. Score = wins + 0.5 × draws.

| Our depth | vs Skill 0 | vs Skill 1 | vs Skill 2 | Total (30 games) | W / D / L |
|---|---|---|---|---|---|
| 2 (Medium) | 45% | 35% | 20% | **33%** | 7 / 6 / 17 |
| 3 (Hard) | 70% | 60% | 65% | **65%** | 17 / 5 / 8 |
| 4 (Expert) | 80% | 90% | 70% | **80%** | 21 / 6 / 3 |

![Benchmark against Stockfish](results/chart_benchmark.png)

**Findings**
- **Search depth is what makes the engine stronger.** Each extra ply raised the score substantially (33% → 65% → 80%), which is the practical payoff of the efficiency gains in section 8.2: alpha-beta and move ordering are what make depth 4 affordable (about 2 seconds per move).
- **Differences between skill levels are within noise.** With 10 games per bar, a single game moves a score by 5 to 10 points; for example, depth 4 scored higher against Skill 1 than against Skill 0. The depth trend holds at every skill level, so it is the reliable conclusion.
- **16 of the 17 draws were threefold repetitions** (one more hit the 200 half-move cap). This matches a known limitation: the engine has no endgame plan and only recognises a draw by repetition when it happens, so it can shuffle pieces in winning positions.
- **This is not an absolute strength rating.** Skill Levels 0 to 2 are deliberately weakened settings, so the results show relative improvement between our own configurations, not an Elo rating.

All 90 games, with full move lists, are in `docs/results/benchmark_games.csv`; the summary is `docs/results/benchmark_summary.md`.

### 8.4 Coach response time

Reviewing one move (two searches) took 0.02 to 1.1 seconds on the test positions, averaging 0.84 seconds in the busiest middlegame. A complete turn on Expert (review plus engine reply) stays within about 3 seconds.

---

## 9. Discussion and Limitations

1. **Depth-limited judgement.** The coach searches 3 plies, so it can misjudge long-term sacrifices; for example it labels the sound 4.Ng5 in the Two Knights Defence an inaccuracy.
2. **Simple evaluation.** Material and piece placement only; no king safety, pawn structure or mobility terms.
3. **Explanations cover common patterns.** Forks, pins and skewers are not yet named; the coach falls back to describing the material the opponent wins.
4. **Speed.** Pure Python limits practical search to depth 4.
5. **No opening or endgame knowledge.** The engine calculates from move 1 and may shuffle pieces in won endgames; 16 of the 17 benchmark draws were threefold repetitions.

---

## 10. Future Scope

- Transposition table and iterative deepening for deeper, faster search
- Named tactic detection (forks, pins, skewers, discovered attacks)
- Richer evaluation (king safety, pawn structure, mobility), possibly tuned or learned from games
- Opening book for variety and endgame tablebases for perfect endgame play
- Game import (PGN) so users can have their own past games reviewed

---

## 11. Conclusion

We formulated chess as an adversarial search problem and built a complete engine from scratch, showing experimentally that alpha-beta pruning with move ordering preserves minimax's decisions while removing over 96% of the search at depth 3. On top of the engine, a rule-based expert system turns numerical evaluations into specific, verifiable explanations for beginners. The project demonstrates search, heuristic knowledge representation and expert-system reasoning working together in an interactive agent that teaches rather than only plays.

---

## References

1. Russell, S. and Norvig, P. (2020). *Artificial Intelligence: A Modern Approach*, 4th ed. Pearson. Chapter 5: Adversarial Search and Games.
2. Shannon, C. E. (1950). Programming a Computer for Playing Chess. *Philosophical Magazine*, 41(314), 256–275.
3. Knuth, D. E. and Moore, R. W. (1975). An Analysis of Alpha-Beta Pruning. *Artificial Intelligence*, 6(4), 293–326.
4. Michniewski, T. Simplified Evaluation Function. Chess Programming Wiki.
5. python-chess documentation. https://python-chess.readthedocs.io
6. Stockfish. https://stockfishchess.org

---

## Appendix A: Reproducing the Results

```bash
pip install -r requirements.txt
python -m tests.test_engine        # 9 tests
python -m tests.test_assistant     # 13 tests
python -m tests.compare_search     # section 8.2 (about 20 seconds)
python -m tests.benchmark          # section 8.3 (needs Stockfish, 30 to 60 minutes)
python -m tests.make_charts        # charts in docs/results/
```

## Appendix B: Tools Used

python-chess, Streamlit, matplotlib, Stockfish 16 (benchmark only), Git and GitHub. An AI coding assistant (Claude) was used during implementation; the commit history records this.
