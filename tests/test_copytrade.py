import pytest
from polyhunter import copytrade as ct
from polyhunter.store import Store


def test_copy_subscriptions(tmp_path):
    st = Store(tmp_path / "c.db")
    st.set_copy(1, "0xAbC", 20)
    st.set_copy(1, "ai", 50)
    st.set_copy(2, "0xabc", 10)
    st.set_copy(1, "0xabc", 30)                        # повтор меняет сумму
    assert sorted(st.copies_of(1)) == [("0xabc", 30), ("ai", 50)]
    assert sorted(st.copiers("0xabc")) == [(1, 30), (2, 10)]
    assert sorted(st.copy_leaders()) == ["0xabc", "ai"]
    st.remove_copy(1, "0xabc")
    assert st.copies_of(1) == [("ai", 50)]


def test_sell_fraction():
    assert ct.sell_fraction(sold=50, remaining=50) == pytest.approx(0.5)
    assert ct.sell_fraction(sold=50, remaining=0) == 1.0
    assert ct.sell_fraction(sold=0, remaining=10) == 0.0
    assert ct.sell_fraction(sold=10, remaining=None) == 1.0   # позиция лидера неизвестна — закрываем


def test_new_leader_trades_only_after_cursor():
    acts = [dict(timestamp=100, transactionHash="a", side="BUY", asset="X", size=10, price=.5),
            dict(timestamp=200, transactionHash="b", side="SELL", asset="X", size=5, price=.6),
            dict(timestamp=200, transactionHash="c", side="BUY", asset="Y", size=1, price=.2)]
    new, cursor = ct.new_trades(acts, cursor=100)
    assert [a["transactionHash"] for a in new] == ["b", "c"] and cursor == 200
    assert ct.new_trades(acts, cursor=None)[0] == []        # первый запуск не повторяет историю
