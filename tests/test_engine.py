import asyncio
from polyhunter.engine import RadarEngine
from polyhunter.store import Store

S = "0x" + "5" * 40
C = "0x" + "c" * 40
NEW = "0x" + "e" * 40


def tr(wallet, tx, usd=6000, price=0.3, asset="A", ts=1000, title="Will X resign?", slug="will-x"):
    return dict(tx=tx, asset=asset, wallet=wallet, side="BUY", price=price, usd=usd, ts=ts, title=title,
                slug=slug, event_slug="ev", outcome="Yes", condition_id="cond-" + asset, name="")


def setup(tmp_path):
    st = Store(tmp_path / "b.db")
    st.save_scores("all", [dict(wallet=S, name="shark", tier="S", score=90, post_edge=.1, edge=.1, q=.001, n=100,
                                events=80, wins=70, exp=60, roi=.2, pnl=1e5, stake=5e5, best_category="news",
                                timing6h=None),
                           dict(wallet=C, name="mid", tier="C", score=50, post_edge=0, edge=0, q=.9, n=100,
                                events=80, wins=60, exp=60, roi=0, pnl=0, stake=5e5, best_category="news",
                                timing6h=None)])
    st.user(1, "ru"); st.user(2, "en")
    st.toggle_alert(2, "smart")            # у второго умные деньги выключены
    st.follow(2, C)

    async def hist(wallet, cond):
        return 0 if wallet == NEW else 40
    return st, RadarEngine(st, hist)


def run(coro):
    return asyncio.run(coro)


def test_smart_signal_routing_and_dedup(tmp_path):
    st, eng = setup(tmp_path)
    out = run(eng.step([tr(S, "t1")]))
    assert [(s["kind"], sorted(s["to"])) for s in out] == [("smart", [1])]
    assert run(eng.step([tr(S, "t1")])) == []           # та же сделка второй раз


def test_follow_and_threshold(tmp_path):
    st, eng = setup(tmp_path)
    out = run(eng.step([tr(C, "t2", usd=6000)]))
    assert [(s["kind"], s["to"]) for s in out] == [("follow", [2])]
    st.set_threshold(2, 10000)
    assert run(eng.step([tr(C, "t3", usd=6000)])) == []


def test_fresh_whale(tmp_path):
    st, eng = setup(tmp_path)
    out = run(eng.step([tr(NEW, "t4", usd=7000, price=0.2)]))
    assert out and out[0]["kind"] == "fresh" and out[0]["history_n"] == 0 and 1 in out[0]["to"]


def test_cluster_once(tmp_path):
    st, eng = setup(tmp_path)
    ws = ["0x" + c * 40 for c in "123"]
    batch = [tr(w, f"c{i}", usd=8000, price=0.5, asset="Z", ts=1000 + 60 * i) for i, w in enumerate(ws)]
    out = run(eng.step(batch))
    assert [s["kind"] for s in out] == ["cluster"]
    more = run(eng.step([tr("0x" + "4" * 40, "c9", usd=8000, price=0.5, asset="Z", ts=1300)]))
    assert [s["kind"] for s in more] == []                # тот же кластер не дублируем


def test_sports_cluster_needs_more_money(tmp_path):
    st, eng = setup(tmp_path)
    ws = ["0x" + c * 40 for c in "123"]
    batch = [tr(w, f"s{i}", usd=9000, price=0.5, asset="Q", ts=1000 + 60 * i, title="Lakers vs. Celtics", slug="nba-y")
             for i, w in enumerate(ws)]
    assert run(eng.step(batch)) == []                      # $27k в спорте — шум
    news = [tr(w, f"n{i}", usd=9000, price=0.5, asset="N", ts=1000 + 60 * i) for i, w in enumerate(ws)]
    assert [s["kind"] for s in run(eng.step(news))][-1] == "cluster"
