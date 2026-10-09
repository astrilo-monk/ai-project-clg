# Benchmark: Our Engine vs Stockfish (low skill levels)

Stockfish 16, Skill Level 0, 1, 2 of 20, 0.05s per move, 1 thread. Our engine: alpha-beta + ordering + quiescence. 5 openings x 2 colours per pairing. Games over 200 half-moves are scored as draws.

Score = wins + 0.5 x draws, as a percentage of games played.

| Our depth | Stockfish skill | Games | Wins | Draws | Losses | Score | Avg time per move | Avg nodes per move |
|---|---|---|---|---|---|---|---|---|
| 2 | 0 | 10 | 3 | 3 | 4 | 45% | 0.05s | 885 |
| 2 | 1 | 10 | 3 | 1 | 6 | 35% | 0.04s | 705 |
| 2 | 2 | 10 | 1 | 2 | 7 | 20% | 0.07s | 1,187 |
| 3 | 0 | 10 | 6 | 2 | 2 | 70% | 0.30s | 7,441 |
| 3 | 1 | 10 | 5 | 2 | 3 | 60% | 0.35s | 7,903 |
| 3 | 2 | 10 | 6 | 1 | 3 | 65% | 0.38s | 8,484 |
| 4 | 0 | 10 | 7 | 2 | 1 | 80% | 2.41s | 43,247 |
| 4 | 1 | 10 | 8 | 2 | 0 | 90% | 1.94s | 36,712 |
| 4 | 2 | 10 | 6 | 2 | 2 | 70% | 2.35s | 44,446 |

## Totals by depth

| Our depth | Games | Wins | Draws | Losses | Score |
|---|---|---|---|---|---|
| 2 | 30 | 7 | 6 | 17 | 33% |
| 3 | 30 | 17 | 5 | 8 | 65% |
| 4 | 30 | 21 | 6 | 3 | 80% |

Draw reasons: move limit 1, threefold repetition 16

Every game's moves are in `benchmark_games.csv` (column `pgn_moves`), so any game can be replayed.
