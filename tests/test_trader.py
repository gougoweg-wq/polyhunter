import asyncio
import pytest
from polyhunter.paper import Paper
from polyhunter.store import Store
from polyhunter.trader import Trader

W = "0x" + "a" * 40
L = "0x" + "b" * 40


def tr(wallet=W, tx="t1", price=0.5, usd=5000, asset="A1", side="BUY"):
    return dict(tx=tx, asset=asset, wallet=wallet, side=side, price=price, usd=usd, ts=1000, title="Will X?",
                slug="will-x", event_slug="ev", outcome="Yes", condition_id="C1", name="")


class FakeClient:
    def __init__(self):
        self.acts = {}
        self.remaining = 0.0
        self.winner = None

    async def book(self, token):
        return [(0.49, 10000)], [(0.50, 10000)]

    async def leader_activity(self, wallet, limit=50):
        return self.acts.get(wallet, [])

    async def leader_position(self, wallet, cond, asset):
        return self.remaining

    async def market_by_token(self, token):
        return {"closed": self.winner is not None, "outcomePrices": '["1", "0"]' if self.winner == "A1" else '["0", "1"]',
                "clobTokenIds": '["A1", "A2"]', "outcomes": '["Yes", "No"]', "feeSchedule": {}}

    async def midpoints(self, tokens):
        return {t: 0.5 for t in tokens}


class FakeModel:
    def __init__(self, p):
        self.p = p
        self.report = {"tradable": True}

    def prob(self, p, stake, cat, wf):
        return self.p


def setup(tmp_path, p_model=0.7):
    st = Store(tmp_path / "t.db")
    st.save_scores("all", [dict(wallet=W, name="w", tier="B", score=60, post_edge=.02, edge=.03, q=.3, n=80,
                                events=60, wins=45, exp=42, roi=.05, pnl=100, stake=2000, best_category="news",
                                timing6h=None)])
    paper = Paper(st)
    return st, paper, Trader(st, paper, FakeClient(), FakeModel(p_model))


def run(c):
    return asyncio.run(c)


def test_ai_buys_on_model_edge_and_mirrors_copiers(tmp_path):
    st, paper, t = setup(tmp_path)
    st.set_copy(5, "ai", 20)
    ev = run(t.on_trades([tr()]))
    ai = paper.positions("ai")
    assert len(ai) == 1 and ai[0]["cost"] == pytest.approx(20)          # ¼ Келли 0.1 → потолок 2% от $1000
    assert paper.positions("u:5")[0]["cost"] == pytest.approx(20)
    assert {e["kind"] for e in ev} == {"ai_buy", "copy_buy"}
    assert run(t.on_trades([tr(tx="t2")])) == []                          # второй раз в тот же исход не входит


def test_ai_skips_without_edge(tmp_path):
    st, paper, t = setup(tmp_path, p_model=0.51)       # перевес 1 п.п. < порога 2 п.п.
    assert run(t.on_trades([tr()])) == [] and paper.positions("ai") == []


def test_ai_skips_unknown_wallet_and_small_trades(tmp_path):
    st, paper, t = setup(tmp_path, p_model=0.9)
    assert run(t.on_trades([tr(wallet="0x" + "c" * 40)])) == []          # кошелька нет в рейтинге
    assert run(t.on_trades([tr(usd=200, tx="small")])) == []              # мелкая сделка — не сигнал


def test_copy_wallet_buy_then_proportional_sell(tmp_path):
    st, paper, t = setup(tmp_path, p_model=0.0)
    st.set_copy(7, L, 25)
    c = t.client
    c.acts[L] = [dict(timestamp=100, transactionHash="h0", side="BUY", asset="A1", size=10, price=.5,
                      conditionId="C1", title="Will X?", slug="will-x", eventSlug="ev", outcome="Yes")]
    assert run(t.copy_step()) == []                                        # первый проход ставит курсор
    c.acts[L].append(dict(timestamp=200, transactionHash="h1", side="BUY", asset="A1", size=100, price=.5,
                          conditionId="C1", title="Will X?", slug="will-x", eventSlug="ev", outcome="Yes"))
    ev = run(t.copy_step())
    assert [e["kind"] for e in ev] == ["copy_buy"] and paper.positions("u:7")[0]["cost"] == pytest.approx(25)
    c.acts[L].append(dict(timestamp=300, transactionHash="h2", side="SELL", asset="A1", size=50, price=.6,
                          conditionId="C1", title="Will X?", slug="will-x", eventSlug="ev", outcome="Yes"))
    c.remaining = 50
    ev = run(t.copy_step())
    assert [e["kind"] for e in ev] == ["copy_sell"]
    assert paper.positions("u:7")[0]["shares"] == pytest.approx(25)       # продал половину из 50 акций


def test_settlement(tmp_path):
    st, paper, t = setup(tmp_path)
    run(t.on_trades([tr()]))
    t.client.winner = "A1"
    ev = run(t.settle_step())
    assert ev and ev[0]["kind"] == "settle" and ev[0]["won"] is True
    assert paper.positions("ai") == [] and paper.account("ai")["cash"] == pytest.approx(1000 - 20 + 40)


def test_ai_fades_when_model_says_whale_overpays(tmp_path):
    st, paper, t = setup(tmp_path, p_model=0.30)       # модель: сторона кита выигрывает лишь в 30%
    ev = run(t.on_trades([tr()]))                      # кит купил A1 по 0.5 → противоположный A2 по 0.5
    pos = paper.positions("ai")
    assert len(pos) == 1 and pos[0]["asset"] == "A2" and pos[0]["outcome"] == "No"
    assert ev[0]["kind"] == "ai_buy" and ev[0]["side"] == "fade"


def test_ai_never_fades_elite_wallets(tmp_path):
    st, paper, t = setup(tmp_path, p_model=0.30)
    s = st.score(W, "all"); s["tier"] = "S"; st.upsert_score("all", s)
    assert run(t.on_trades([tr()])) == []


def test_ai_one_position_per_event_and_hourly_cap(tmp_path):
    st, paper, t = setup(tmp_path, p_model=0.7)
    t.max_new_per_hour = 2
    same_event = [tr(tx="e1", asset="A1"), dict(tr(tx="e2", asset="B1"), condition_id="C2")]   # один event_slug «ev»
    run(t.on_trades(same_event))
    assert len(paper.positions("ai")) == 1
    others = [dict(tr(tx=f"o{i}", asset=f"X{i}"), condition_id=f"CX{i}", event_slug=f"ev{i}") for i in range(5)]
    run(t.on_trades(others))
    assert len(paper.positions("ai")) == 2                          # потолок 2 новые позиции в час
