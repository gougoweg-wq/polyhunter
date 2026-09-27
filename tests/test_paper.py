import pytest
from polyhunter.paper import Paper, PaperError, walk_book
from polyhunter.store import Store

MK = dict(asset="A1", condition_id="C1", outcome="Yes", title="Will X?", slug="will-x", event_slug="ev")


def mk(tmp_path):
    return Paper(Store(tmp_path / "p.db"), start_cash=1000)


def test_walk_book_buy_by_usd_and_sell_by_shares():
    sh, cost = walk_book([(0.40, 100), (0.42, 200)], usd=100)
    assert sh == pytest.approx(100 + 60 / 0.42) and cost == pytest.approx(100)
    sh, got = walk_book([(0.50, 30), (0.45, 100)], shares=50)
    assert sh == 50 and got == pytest.approx(30 * 0.50 + 20 * 0.45)
    sh, cost = walk_book([(0.40, 10)], usd=100)            # мелкий стакан — частичное исполнение
    assert sh == 10 and cost == pytest.approx(4)


def test_buy_updates_cash_position_and_log(tmp_path):
    p = mk(tmp_path)
    r = p.buy("u:1", MK, asks=[(0.40, 100), (0.42, 200)], usd=100)
    assert r["shares"] == pytest.approx(100 + 60 / 0.42) and r["price"] == pytest.approx(100 / r["shares"])
    assert p.account("u:1")["cash"] == pytest.approx(900)
    pos = p.positions("u:1")[0]
    assert pos["asset"] == "A1" and pos["cost"] == pytest.approx(100) and pos["outcome"] == "Yes"
    assert p.trades("u:1")[0]["side"] == "BUY"


def test_buy_guards(tmp_path):
    p = mk(tmp_path)
    with pytest.raises(PaperError):
        p.buy("u:1", MK, asks=[(0.4, 10000)], usd=5000)     # денег нет
    with pytest.raises(PaperError):
        p.buy("u:1", MK, asks=[], usd=10)                   # стакан пуст
    with pytest.raises(PaperError):
        p.buy("u:1", MK, asks=[(0.995, 1000)], usd=10)      # почти решённый исход
    assert p.account("u:1")["cash"] == 1000


def test_sell_half_and_settle(tmp_path):
    p = mk(tmp_path)
    p.buy("u:1", MK, asks=[(0.50, 1000)], usd=100)          # 200 акций
    r = p.sell("u:1", "A1", bids=[(0.60, 1000)], fraction=0.5)
    assert r["shares"] == pytest.approx(100) and r["pnl"] == pytest.approx(60 - 50)
    assert p.account("u:1")["cash"] == pytest.approx(900 + 60)
    out = p.settle("A1", won=True)
    assert out == [("u:1", pytest.approx(100), pytest.approx(50))]
    assert p.positions("u:1") == [] and p.account("u:1")["cash"] == pytest.approx(1060)


def test_equity_leaderboard_reset(tmp_path):
    p = mk(tmp_path)
    p.buy("u:1", MK, asks=[(0.50, 1000)], usd=100)
    p.account("u:2")
    assert p.equity("u:1", {"A1": 0.70}) == pytest.approx(900 + 200 * 0.70)
    lb = p.leaderboard({"A1": 0.70})
    assert lb[0][0] == "u:1" and lb[0][2] == pytest.approx(40)
    p.reset("u:1")
    assert p.account("u:1")["cash"] == 1000 and p.positions("u:1") == []
