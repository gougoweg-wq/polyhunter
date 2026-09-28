import pytest
from polyhunter import stats, render


def test_live_record_ci_and_needed_n():
    r = stats.live_record([1.0, -1.0] * 50, expected=0.075)        # 100 ставок, среднее 0, разброс 1
    assert r["n"] == 100 and r["mean"] == pytest.approx(0) and r["lo"] < 0 < r["hi"]
    assert 600 < r["needed"] < 800                                  # (2·1/0.075)² ≈ 711
    assert stats.live_record([], expected=0.075)["n"] == 0


def test_returns_from_settlements():
    trades = [dict(side="WIN", usd=40, pnl=20), dict(side="LOSS", usd=0, pnl=-15), dict(side="BUY", usd=15, pnl=None)]
    assert stats.settled_returns(trades) == [pytest.approx(1.0), pytest.approx(-1.0)]


def test_render_live_line():
    txt = render.live_line(stats.live_record([0.5] * 30 + [-1.0] * 10, expected=0.075), "ru")
    assert "40" in txt and "95%" in txt and "нужно" in txt
