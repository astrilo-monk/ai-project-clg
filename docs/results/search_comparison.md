# Search Comparison

Positions: start, italian, middlegame, endgame. Quiescence off so every variant searches the same tree.
All three variants returned the same evaluation score at every depth (verified by tests/test_engine.py).

## Total nodes across all positions

| Depth | Minimax | Alpha-beta | Alpha-beta + ordering | Alpha-beta vs minimax | Alpha-beta + ordering vs minimax | Ordering vs plain alpha-beta |
|---|---|---|---|---|---|---|
| 1 | 113 | 113 | 113 | 0.0% fewer | 0.0% fewer | 0.0% fewer |
| 2 | 3,627 | 1,320 | 461 | 63.6% fewer | 87.3% fewer | 65.1% fewer |
| 3 | 117,954 | 15,895 | 4,296 | 86.5% fewer | 96.4% fewer | 73.0% fewer |
| 4 | not run | 182,963 | 19,722 | n/a | n/a | 89.2% fewer |

Minimax was not run above depth 3 because it takes minutes per position in Python.

## Per position

| Position | Depth | Variant | Nodes | Seconds | Best move |
|---|---|---|---|---|---|
| start | 1 | minimax | 20 | 0.001 | Nf3 |
| start | 1 | alphabeta | 20 | 0.001 | Nf3 |
| start | 1 | alphabeta+ordering | 20 | 0.001 | Nf3 |
| start | 2 | minimax | 420 | 0.021 | Nf3 |
| start | 2 | alphabeta | 83 | 0.004 | Nf3 |
| start | 2 | alphabeta+ordering | 83 | 0.006 | Nf3 |
| start | 3 | minimax | 9,322 | 0.402 | Nf3 |
| start | 3 | alphabeta | 777 | 0.039 | Nf3 |
| start | 3 | alphabeta+ordering | 776 | 0.051 | Nf3 |
| start | 4 | alphabeta | 3,154 | 0.14 | Nf3 |
| start | 4 | alphabeta+ordering | 3,108 | 0.21 | Nf3 |
| italian | 1 | minimax | 33 | 0.001 | Nxe5 |
| italian | 1 | alphabeta | 33 | 0.001 | Nxe5 |
| italian | 1 | alphabeta+ordering | 33 | 0.002 | Nxe5 |
| italian | 2 | minimax | 1,183 | 0.047 | Nc3 |
| italian | 2 | alphabeta | 554 | 0.023 | Nc3 |
| italian | 2 | alphabeta+ordering | 210 | 0.015 | Nc3 |
| italian | 3 | minimax | 38,322 | 1.76 | Bd5 |
| italian | 3 | alphabeta | 3,036 | 0.13 | Bd5 |
| italian | 3 | alphabeta+ordering | 1,458 | 0.08 | Bd5 |
| italian | 4 | alphabeta | 36,918 | 1.599 | Bb5 |
| italian | 4 | alphabeta+ordering | 6,506 | 0.583 | Bb5 |
| middlegame | 1 | minimax | 40 | 0.002 | Bxf6 |
| middlegame | 1 | alphabeta | 40 | 0.002 | Bxf6 |
| middlegame | 1 | alphabeta+ordering | 40 | 0.002 | Bxf6 |
| middlegame | 2 | minimax | 1,609 | 0.069 | Bxf6 |
| middlegame | 2 | alphabeta | 494 | 0.022 | Bxf6 |
| middlegame | 2 | alphabeta+ordering | 120 | 0.014 | Bxf6 |
| middlegame | 3 | minimax | 62,794 | 2.852 | Bxf6 |
| middlegame | 3 | alphabeta | 10,595 | 0.487 | Bxf6 |
| middlegame | 3 | alphabeta+ordering | 1,810 | 0.121 | Bxf6 |
| middlegame | 4 | alphabeta | 126,126 | 4.891 | Bb3 |
| middlegame | 4 | alphabeta+ordering | 9,407 | 0.809 | Bb3 |
| endgame | 1 | minimax | 20 | 0.001 | Rxd1 |
| endgame | 1 | alphabeta | 20 | 0.001 | Rxd1 |
| endgame | 1 | alphabeta+ordering | 20 | 0.001 | Rxd1 |
| endgame | 2 | minimax | 415 | 0.012 | Rxd1 |
| endgame | 2 | alphabeta | 189 | 0.005 | Rxd1 |
| endgame | 2 | alphabeta+ordering | 48 | 0.004 | Rxd1 |
| endgame | 3 | minimax | 7,516 | 0.25 | Rxd1 |
| endgame | 3 | alphabeta | 1,487 | 0.059 | Rxd1 |
| endgame | 3 | alphabeta+ordering | 252 | 0.016 | Rxd1 |
| endgame | 4 | alphabeta | 16,765 | 0.501 | Rxd1 |
| endgame | 4 | alphabeta+ordering | 701 | 0.053 | Rxd1 |
