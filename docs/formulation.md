# Problem Formulation: AI Chess Assistant for Beginner Players

## 1. Problem Statement

Beginner chess players lose games mostly because of simple tactical mistakes: leaving pieces undefended, missing free captures, and walking into checkmate. They rarely know *why* a move was bad. Human coaches are expensive, and strong engines like Stockfish show a number (for example "-3.2") without explaining it in words a beginner understands.

This project builds an AI system that:

1. Plays chess against the user at an adjustable difficulty.
2. Detects when the user makes a mistake or blunder.
3. Explains the mistake in plain English and suggests a better move.

The move-selection AI (search and evaluation) is written from scratch. The `python-chess` library is used only for the rules of the game (legal move generation, check and checkmate detection), in the same way a robotics project uses a physics simulator.

---

## 2. Formulation as a Search Problem

Chess is formulated as a **two-player, zero-sum game** and solved with **adversarial search**.

| Component | Definition in this project |
|---|---|
| **Initial state** | The standard starting position, White to move |
| **State** | A full board position: placement of all pieces, side to move, castling rights, en passant square, halfmove clock (stored as a `chess.Board`, written as a FEN string) |
| **Players** | `PLAYER(s)` returns White or Black, whoever is to move in state `s` |
| **Actions** | `ACTIONS(s)` returns every legal move in state `s` (on average about 35) |
| **Transition model** | `RESULT(s, a)` returns the new position after move `a` is played in `s` |
| **Terminal test** | `TERMINAL(s)` is true on checkmate, stalemate, insufficient material, threefold repetition, or the 50-move rule |
| **Utility** | `UTILITY(s)` = +1 if White wins, -1 if Black wins, 0 for a draw. In code, a win is scored as +100000 and a loss as -100000 so it always dominates the heuristic scores |
| **Heuristic evaluation** | `EVAL(s)` estimates how good a non-terminal position is for White, in centipawns (100 = one pawn). Used when the search reaches its depth limit |

### Why adversarial search and not ordinary search?

In ordinary search (for example A* on a map), the agent controls every action and simply looks for the cheapest path to a goal. In chess, every other move is chosen by an **opponent who is actively trying to make us lose**. A path that looks good is worthless if the opponent can refute it. So the agent must assume the opponent plays its best reply, which is exactly what **minimax** models: White maximizes the score, Black minimizes it.

---

## 3. PEAS Description

| | Description |
|---|---|
| **Performance measure** | Win rate against reference opponents; nodes searched per move; time per move; accuracy of blunder detection; clarity of explanations for the user |
| **Environment** | An 8x8 chessboard, a human opponent (the beginner), the rules of chess |
| **Actuators** | Choosing and playing a move; displaying hints, warnings, and explanations on screen |
| **Sensors** | The current board position and the move the user just played |

---

## 4. Properties of the Task Environment

| Property | Value | Reason |
|---|---|---|
| Observable | **Fully observable** | Both players see the whole board; no hidden information |
| Agents | **Multi-agent, competitive** | Two players with exactly opposite goals |
| Deterministic | **Deterministic** | A move always produces the same next position; no dice or randomness |
| Episodic / Sequential | **Sequential** | Every move affects all future positions |
| Static / Dynamic | **Static** (semi-dynamic with a clock) | The board does not change while the agent is thinking |
| Discrete / Continuous | **Discrete** | Finite squares, pieces, and moves |
| Known / Unknown | **Known** | The rules are fully specified |

---

## 5. Knowledge Required

| Knowledge type | What it is in this project | Where it lives in code |
|---|---|---|
| **Declarative (facts)** | Rules of chess: how each piece moves, check, castling, promotion, en passant, draw rules | `python-chess` library |
| **Declarative (facts)** | Relative piece values: Pawn 100, Knight 320, Bishop 330, Rook 500, Queen 900 | `engine/evaluate.py` |
| **Heuristic (rules of thumb)** | Positional principles: control the center, develop knights and bishops early, keep the king safe behind pawns in the middlegame, activate the king in the endgame, push passed pawns | Piece-square tables in `engine/evaluate.py` |
| **Procedural (how to)** | How to look ahead: generate moves, search the game tree, prune branches that cannot affect the decision, order moves so the best ones are tried first | `engine/search.py`, `engine/ordering.py` |
| **Meta-knowledge (teaching)** | What counts as a beginner mistake and how to explain it (hanging pieces, missed captures, early queen moves, walking into mate) | `assistant/` (Phase 3) |

---

## 6. Why AI Is Required

1. **The search space is enormous.** Chess has an average branching factor of about 35 and games last about 80 plies (half-moves). The number of possible games is estimated at around 10^120 (the Shannon number), more than the number of atoms in the observable universe. Checking every possible continuation is impossible, so the agent needs **heuristic search** that looks a limited number of moves ahead and estimates the rest.
2. **There is an intelligent opponent.** A fixed set of if-then rules cannot anticipate every plan the opponent might try. The agent must reason about the opponent's best reply, which requires **adversarial reasoning**.
3. **Positions must be judged, not just counted.** Two positions with equal material can be very different. The agent needs **domain knowledge encoded as a heuristic** to judge them.
4. **Teaching needs reasoning, not just play.** Explaining *why* a move is bad requires comparing what happened with what the best move would have achieved, which is a reasoning task on top of search.

---

## 7. AI Techniques Selected

| Technique | Purpose | Why this one |
|---|---|---|
| **Minimax** | Choose the move that is best assuming the opponent also plays its best | The standard, provably correct algorithm for deterministic, two-player, zero-sum, fully observable games |
| **Alpha-beta pruning** | Skip branches that cannot change the final decision | Returns exactly the same move as minimax while searching far fewer nodes |
| **Heuristic evaluation function** | Score positions at the depth limit | Encodes chess knowledge (material and piece placement) that the search cannot see on its own |
| **Move ordering (MVV-LVA)** | Search the most promising moves first | Alpha-beta prunes much more when good moves are tried first |
| **Quiescence search** | Keep searching captures past the depth limit | Reduces the horizon effect, where the engine stops looking just before it loses a piece |
| **Rule-based expert system** (Phase 3) | Turn engine output into plain-English explanations | Explanations must be transparent and predictable for a teaching tool |

### Alternatives considered and rejected

- **Monte Carlo Tree Search (MCTS):** strong in games like Go with huge branching factors, but it needs many random playouts per move, which is slow in Python and harder to explain to a beginner.
- **Reinforcement learning / neural networks (AlphaZero style):** requires millions of self-play games and GPU training. Not feasible for a student project and not needed to beat beginners.
- **Using Stockfish directly:** would make the project a wrapper, not an AI system. Stockfish is used only as a benchmark opponent in Phase 4.

---

## 8. Scope

**In scope:** a playable web interface, an engine written from scratch (minimax, alpha-beta, evaluation, move ordering, quiescence), difficulty levels, blunder detection, hints, and rule-based explanations, plus an experimental evaluation.

**Out of scope (future work):** opening book, endgame tablebases, machine-learned evaluation, time management, online multiplayer.
