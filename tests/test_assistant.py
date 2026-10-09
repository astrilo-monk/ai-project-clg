"""
Tests for the beginner assistant (Phase 3).

Run with either:
    python -m pytest tests/
    python -m tests.test_assistant
"""

import chess

from assistant.blunder import review_move
from assistant.explain import explain_move
from assistant.hints import get_hint


def review(fen: str, san: str):
    board = chess.Board(fen)
    move = board.parse_san(san)
    r = review_move(board, move)
    return r, explain_move(board, r)


def all_text(feedback) -> str:
    return " ".join([feedback.headline, *feedback.reasons, feedback.better or "", *feedback.tips])


AFTER_E4_E5 = "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"
FREE_QUEEN = "rnb1kbnr/ppp1pppp/8/3q4/8/2N5/PPPP1PPP/R1BQKBNR w KQkq - 0 3"
BACK_RANK = "6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1"
FOOLS_MATE = "rnbqkbnr/pppp1ppp/8/4p3/8/5P2/PPPPP1PP/RNBQKBNR w KQkq - 0 2"


def test_hanging_a_bishop_is_a_blunder():
    r, fb = review(AFTER_E4_E5, "Ba6")  # bishop walks into ...bxa6 / ...Nxa6
    assert r.label == "Blunder", r
    text = all_text(fb)
    assert "bishop" in text and "a6" in text, text


def test_missing_a_free_queen():
    r, fb = review(FREE_QUEEN, "a3")
    assert r.label == "Blunder", r
    text = all_text(fb)
    assert "Nxd5" in text and "queen" in text, text


def test_walking_into_mate():
    r, fb = review(FOOLS_MATE, "g4")  # the famous Fool's Mate: ...Qh4#
    assert r.label == "Blunder", r
    assert r.reply_san == "Qh4#"
    assert any("checkmate" in reason for reason in fb.reasons), fb


def test_missing_mate_in_one():
    r, fb = review(BACK_RANK, "Kf2")
    assert r.label == "Blunder", r
    assert any("missed a checkmate" in reason and "Ra8#" in reason for reason in fb.reasons), fb


def test_best_move_is_praised():
    r, fb = review(BACK_RANK, "Ra8#")
    assert r.label == "Best"
    assert "checkmate" in fb.headline


def test_early_queen_tip():
    _, fb = review(AFTER_E4_E5, "Qh5")
    assert any("queen out early" in tip for tip in fb.tips), fb


def test_knight_on_rim_tip():
    _, fb = review(chess.STARTING_FEN, "Na3")
    assert any("rim" in tip for tip in fb.tips), fb


def test_good_opening_move_has_no_complaints():
    r, fb = review(chess.STARTING_FEN, "e4")
    assert r.label in ("Best", "Good"), r
    assert not fb.reasons


def test_black_moves_are_reviewed_too():
    # Black to move; Qxd2+?? hands the queen to the bishop/knight/queen.
    fen = "rnb1kbnr/pppp1ppp/8/4p3/4P2q/2N5/PPPPQPPP/R1B1KBNR b KQkq - 3 3"
    r, fb = review(fen, "Qxf2+")
    assert r.label == "Blunder", r
    assert "queen" in all_text(fb)


SCHOLARS_THREAT = "r1bqkbnr/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 3 3"


def test_scholars_mate_defence_is_explained():
    # White threatens Qxf7#. ...Nf6?? allows it; ...g6 stops it.
    r, fb = review(SCHOLARS_THREAT, "Nf6")
    assert r.label == "Blunder" and r.reply_san == "Qxf7#"
    assert "stops your opponent's checkmate threat" in fb.better, fb


def test_piece_no_longer_protected():
    # ...Nd4 moves the knight that was defending e5.
    fen = "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3"
    r, fb = review(fen, "Nd4")
    assert r.label in ("Mistake", "Blunder"), r
    assert any("no longer protected" in reason for reason in fb.reasons), fb


def test_hint_finds_free_queen():
    hint = get_hint(chess.Board(FREE_QUEEN))
    assert hint.san == "Nxd5"
    assert "queen" in hint.text


def test_hint_finds_mate():
    hint = get_hint(chess.Board(BACK_RANK))
    assert hint.san == "Ra8#"
    assert "checkmate" in hint.text


if __name__ == "__main__":
    tests = [(n, f) for n, f in globals().items() if n.startswith("test_") and callable(f)]
    for name, fn in tests:
        fn()
        print(f"PASS  {name}")
    print(f"\nAll {len(tests)} tests passed.")
