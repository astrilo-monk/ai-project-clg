"""
Correctness tests for the engine.

Run with either:
    python -m pytest tests/
    python -m tests.test_engine
"""

import chess

from engine.evaluate import MATE_SCORE, evaluate
from engine.search import find_best_move

# A few positions of different kinds, written as FEN strings.
POSITIONS = {
    "start": chess.STARTING_FEN,
    "italian": "r1bqk1nr/pppp1ppp/2n5/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
    "middlegame": "r2q1rk1/ppp2ppp/2np1n2/2b1p1B1/2B1P1b1/2NP1N2/PPP2PPP/R2Q1RK1 w - - 4 8",
    "endgame": "8/5pk1/6p1/8/3R4/6P1/5PK1/3r4 w - - 0 1",
}


def test_start_position_is_balanced():
    assert evaluate(chess.Board()) == 0


def test_evaluation_is_symmetric():
    # Mirroring the board (swap colours, flip ranks) must negate the score.
    for fen in POSITIONS.values():
        board = chess.Board(fen)
        assert evaluate(board) == -evaluate(board.mirror()), fen


def test_minimax_and_alphabeta_agree():
    # Alpha-beta must return exactly the same score as plain minimax.
    for name, fen in POSITIONS.items():
        board = chess.Board(fen)
        for depth in (1, 2, 3):
            mm = find_best_move(board, depth, "minimax")
            ab = find_best_move(board, depth, "alphabeta", use_ordering=False, use_quiescence=False)
            abo = find_best_move(board, depth, "alphabeta", use_ordering=True, use_quiescence=False)
            assert mm.score == ab.score == abo.score, (name, depth, mm.score, ab.score, abo.score)
            assert ab.nodes <= mm.nodes and abo.nodes <= mm.nodes


def test_finds_mate_in_one_for_white():
    board = chess.Board("6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1")  # back-rank mate
    result = find_best_move(board, 2)
    assert board.san(result.move) == "Ra8#"
    assert result.score == MATE_SCORE - 1


def test_finds_mate_in_one_for_black():
    board = chess.Board("r5k1/8/8/8/8/8/5PPP/6K1 b - - 0 1")
    result = find_best_move(board, 2)
    assert board.san(result.move) == "Ra1#"
    assert result.score == -(MATE_SCORE - 1)


def test_finds_mate_in_two():
    # White: Re8+ Rxe8, Rxe8#  (classic back-rank combination)
    board = chess.Board("r5k1/5ppp/8/8/8/8/4RPPP/4R1K1 w - - 0 1")
    # Make sure there is no mate in 1, so the test really needs 2 moves.
    for move in board.legal_moves:
        board.push(move)
        assert not board.is_checkmate()
        board.pop()
    result = find_best_move(board, 4)
    assert board.san(result.move) == "Re8+"
    assert result.score == MATE_SCORE - 3, result.score


def test_takes_free_queen():
    # Black queen on d5 is attacked by the knight on c3 and defended by nothing.
    board = chess.Board("rnb1kbnr/ppp1pppp/8/3q4/8/2N5/PPPP1PPP/R1BQKBNR w KQkq - 0 3")
    result = find_best_move(board, 3)
    assert board.san(result.move) == "Nxd5"


def test_does_not_take_poisoned_pawn():
    # Qxd5 grabs a pawn but the queen is then lost to ...Qxd5 (pawn on d5 defended by queen d8).
    board = chess.Board("rnbqkbnr/ppp2ppp/8/3pp3/8/5Q2/PPPP1PPP/RNB1KBNR w KQkq - 0 3")
    result = find_best_move(board, 2)
    assert board.san(result.move) != "Qxd5"


def test_board_is_not_modified():
    board = chess.Board(POSITIONS["italian"])
    fen_before = board.fen()
    find_best_move(board, 3)
    assert board.fen() == fen_before


if __name__ == "__main__":
    tests = [(n, f) for n, f in globals().items() if n.startswith("test_") and callable(f)]
    for name, fn in tests:
        fn()
        print(f"PASS  {name}")
    print(f"\nAll {len(tests)} tests passed.")
