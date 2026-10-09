# AI Chess Assistant for Beginner Players

A chess engine built from scratch, plus a teaching layer that helps beginners improve. It plays against you, catches your blunders, explains mistakes in plain English, and suggests better moves.

- Cost: free
- Hardware: none
- Data needed: none
- Timeline: about 3 weeks, 4 phases
- Team: buildable solo

---

## 1. The Golden Rule

**Do not use Stockfish as your AI.** Your engine (minimax, alpha-beta, evaluation) must be your own code. Stockfish is allowed only in Phase 4, as an opponent to benchmark against.

**Understand every line before you commit it.** Your professor will ask you to explain alpha-beta pruning and your evaluation function. If an AI agent wrote code you can't explain, rewrite it or ask the agent to explain it until you can.

---

## 2. Tech Stack

| Tool | Purpose |
|---|---|
| Python 3.10+ | Language |
| python-chess | Board, legal moves, check, checkmate, SVG drawing |
| Streamlit | Web interface |
| Stockfish (free binary) | Benchmark opponent in Phase 4 only |
| matplotlib | Charts for the report |
| Git + GitHub | Version control and proof of your work |

---

## 3. Setup

```bash
# 1. Create the project folder
mkdir chess-assistant
cd chess-assistant

# 2. Create a virtual environment
python -m venv venv

# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

# 3. Install packages
pip install python-chess streamlit matplotlib

# 4. Save dependencies
pip freeze > requirements.txt

# 5. Start Git
git init
```

Create a GitHub repo and push on day one. **Commit at least once every day you work.** If teammates don't contribute, the commit history proves who did the work.

---

## 4. Folder Structure

```
chess-assistant/
├── app.py                 # Streamlit interface
├── engine/
│   ├── __init__.py
│   ├── evaluate.py        # Evaluation function
│   ├── search.py          # Minimax + alpha-beta
│   └── ordering.py        # Move ordering
├── assistant/
│   ├── __init__.py
│   ├── blunder.py         # Blunder detection
│   ├── hints.py           # Best move suggestions
│   └── explain.py         # Plain-English explanations
├── tests/
│   └── benchmark.py       # Engine vs Stockfish, node counts
├── docs/
│   ├── formulation.md     # Phase 1 write-up
│   └── results/           # Charts and tables
├── requirements.txt
└── README.md
```

---

## 5. The Four Phases

### Phase 1: Formulation + Board (Days 1 to 4)

**Goal:** a written problem formulation and a playable board.

Tasks:
- [ ] Write `docs/formulation.md` covering:
  - **State:** a board position (piece placement, side to move, castling rights, en passant)
  - **Actions:** all legal moves in that position
  - **Transition model:** applying a move produces a new position
  - **Terminal test:** checkmate, stalemate, draw by repetition or 50-move rule
  - **Utility:** +1 win, 0 draw, -1 loss
  - **Problem type:** two-player, zero-sum, deterministic, fully observable, adversarial search
  - **Knowledge types:**
    - Declarative: rules of chess, piece values
    - Heuristic: positional principles (control the center, develop pieces, king safety)
    - Procedural: how to search the game tree
  - **Why AI:** chess has roughly 10^120 possible games, so brute force is impossible. Heuristic search is required.
- [ ] Build `app.py`: draw the board with `chess.svg`, choose your move from a dropdown of legal moves, and have the computer reply with a random legal move for now.

Note: Streamlit has no built-in clickable chessboard. A dropdown of legal moves is simple and reliable. If you want click-to-move later, switch to pygame.

**Progress line for your professor:** "We formulated chess as a two-player adversarial search problem and built a playable board with full rule enforcement."

---

### Phase 2: The Engine (Days 5 to 10)

**Goal:** an engine that plays sensible chess. This is the core. If you finish this phase, you pass.

Tasks:
- [ ] `evaluate.py`: material count (P=100, N=320, B=330, R=500, Q=900, K=20000) plus piece-square tables
- [ ] `search.py`: plain minimax with depth limit
- [ ] `search.py`: add alpha-beta pruning
- [ ] `search.py`: count nodes searched, for your report
- [ ] `ordering.py`: search captures and checks first (MVV-LVA ordering) to speed up alpha-beta
- [ ] Connect the engine to `app.py`, replacing the random mover

Warning: Python is slow. Depth 3 to 4 is realistic. Depth 6 will freeze. Move ordering is your speed fix.

**Progress line:** "Our engine plays at depth 4. Alpha-beta reduced nodes searched by X% compared to plain minimax." Use your real numbers.

---

### Phase 3: The Beginner Assistant (Days 11 to 16)

**Goal:** the teaching layer. This is what earns top marks and makes the project different from every other chess bot.

Tasks:
- [ ] `blunder.py`: after each player move, compare the evaluation before and after. A drop of more than about 200 centipawns is a blunder, 100 to 200 is a mistake.
- [ ] `hints.py`: a "Hint" button that shows the engine's best move
- [ ] `explain.py`: rule-based explanations, for example:
  - "Your knight on f3 is now undefended and can be captured."
  - "You missed a free bishop on c4."
  - "This move walks into checkmate in 2."
  - "You moved your queen out early. Develop knights and bishops first."
- [ ] Difficulty levels: Easy (depth 1), Medium (depth 2), Hard (depth 3 or 4)
- [ ] Show a move history with blunders highlighted

**Progress line:** "The assistant now detects mistakes, explains them in plain English, and offers hints."

---

### Phase 4: Testing + Report (Days 17 to 21)

**Goal:** evidence and presentation.

Tasks:
- [ ] Download Stockfish from stockfishchess.org (free). Use it through `chess.engine` at its lowest skill levels.
- [ ] `benchmark.py`: play 10 games at each of your depths (2, 3, 4) against low-level Stockfish. Record wins, losses, draws.
- [ ] Measure nodes searched and time per move: minimax vs alpha-beta vs alpha-beta with move ordering
- [ ] Make charts with matplotlib, save to `docs/results/`
- [ ] Write the final report
- [ ] Build slides and rehearse a 5-minute live demo

**Future scope (for the report, do not build):** opening book, endgame tablebases, machine-learned evaluation, Monte Carlo Tree Search.

**Progress line:** "The system is evaluated, documented, and ready to present."

---

## 6. How to Use Your AI Agent

### Step 1: Paste this context first, at the start of every new session

```
I'm building an AI Chess Assistant for Beginner Players as a university AI course project.

Rules for you:
- Python 3, python-chess for board rules, Streamlit for the UI.
- I must write my own engine: minimax, alpha-beta pruning, evaluation function. Never use Stockfish for move selection. Stockfish is only for benchmarking.
- Explain every function you write in simple terms, because I have to defend this code in front of my professor.
- Keep code simple and readable over clever and fast.
- Follow this folder structure: [paste section 4 of the README]
- Do one task at a time. After each task, tell me how to test it.

Current phase: [Phase number and name]
What's already done: [list completed tasks]
```

### Step 2: Use these prompts, one at a time

**Phase 1**
1. `Help me write docs/formulation.md. Ask me questions if needed, but cover state, actions, transition model, terminal test, utility, problem type, knowledge types, and why AI is needed.`
2. `Write app.py: a Streamlit app that shows the board using chess.svg, lets me pick a move from a dropdown of legal moves, and replies with a random legal move. Store the board in st.session_state.`

**Phase 2**
3. `Write engine/evaluate.py with material values and piece-square tables for all pieces. Explain what a piece-square table is.`
4. `Write plain minimax in engine/search.py with a depth limit and a node counter. Explain how it works with a small example.`
5. `Add alpha-beta pruning to search.py as a separate function so I can compare both. Explain alpha and beta in simple terms.`
6. `Write engine/ordering.py using MVV-LVA so captures and checks are searched first. Show me how much it reduces nodes.`
7. `Connect the engine to app.py so the computer plays the best move at a chosen depth.`

**Phase 3**
8. `Write assistant/blunder.py that classifies my last move as good, inaccuracy, mistake, or blunder based on the evaluation change.`
9. `Write assistant/explain.py with rule-based explanations: hanging pieces, missed captures, walking into mate, early queen moves. Return a plain-English sentence.`
10. `Add a Hint button, a difficulty selector (Easy/Medium/Hard), and a move history with blunders highlighted to app.py.`

**Phase 4**
11. `Write tests/benchmark.py that plays my engine against Stockfish at skill level 0 to 2 for N games at depths 2, 3, and 4, and saves results to CSV.`
12. `Write a script that compares nodes searched and time per move for minimax, alpha-beta, and alpha-beta with move ordering, and plots the results.`
13. `Help me write the final report structure for an AI course: introduction, problem formulation, knowledge representation, techniques, implementation, results, limitations, future scope.`

### Step 3: When something breaks

```
This code gives this error: [paste error]
Here is the file: [paste file]
Explain what caused it before fixing it.
```

### Step 4: Before every progress meeting

```
Quiz me on [topic, e.g. alpha-beta pruning] like a strict professor would. Ask one question at a time and correct my answers.
```

---

## 7. Viva Questions You Must Be Able to Answer

1. Why is chess an adversarial search problem and not a regular search problem?
2. How does minimax work? Draw a small tree.
3. What does alpha-beta pruning cut, and why doesn't it change the result?
4. Why does move ordering make alpha-beta faster?
5. What is your evaluation function, and why those piece values?
6. What is the horizon effect? Does your engine suffer from it?
7. How do you decide something is a blunder?
8. Why didn't you just use Stockfish?
9. What are the limitations of your engine?
10. What would you add with more time?

If you can't answer one of these confidently, that's your study task for the day.

---

## 8. Daily Checklist

- [ ] Worked on the current phase task
- [ ] Tested it
- [ ] Understood every line written today
- [ ] Committed and pushed to GitHub
