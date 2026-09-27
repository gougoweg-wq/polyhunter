import asyncio
import json
import pytest
from polyhunter.newstrader import NewsTrader
from polyhunter.paper import Paper
from polyhunter.store import Store

EVENT = {"slug": "iran", "title": "Will the U.S. invade Iran before 2027?", "markets": [
    {"conditionId": "C1", "question": "Will the U.S. invade Iran before 2027?", "outcomes": '["Yes", "No"]',
     "outcomePrices": '["0.20", "0.80"]', "clobTokenIds": '["Y1", "N1"]', "liquidity": "50000", "volume24hr": "9000",
     "endDate": "2026-12-31T00:00:00Z", "description": "Resolves YES if...", "active": True, "closed": False,
     "slug": "invade-iran", "feeSchedule": {}}]}
RSS = "<rss>" + "".join(f"<item><title>Iran news {i} - Src</title><link>l</link><pubDate>Sun, 27 Sep 2026 1{i}:00:00 GMT</pubDate>"
                        f"<source url='s'>Src</source></item>" for i in range(5)) + "</rss>"


class Resp:
    def __init__(self, text):
        self.status_code, self.text = 200, text


class FakeHttp:
    async def get(self, url, params=None, timeout=None):
        return Resp(RSS)


class FakeClient:
    def __init__(self):
        self.winner = None

    async def get(self, url, **params):
        return [EVENT]

    async def book(self, token):
        return ([(0.19, 5000)], [(0.20, 5000)]) if token == "Y1" else ([(0.79, 5000)], [(0.80, 5000)])

    async def market_by_condition(self, cid):
        m = dict(EVENT["markets"][0])
        if self.winner:
            m["closed"] = True
            m["outcomePrices"] = '["1", "0"]' if self.winner == "Y1" else '["0", "1"]'
        return m


def make(tmp_path, answer):
    st = Store(tmp_path / "n.db")
    paper = Paper(st)
    calls = []

    async def ask(http, prompt):
        calls.append(prompt)
        return json.dumps(answer)
    return st, paper, NewsTrader(st, paper, FakeClient(), FakeHttp(), ask), calls


def run(c):
    return asyncio.run(c)


def test_cycle_forecasts_trades_and_mirrors(tmp_path):
    st, paper, nt, calls = make(tmp_path, {"p_yes": 0.40, "confidence": "high", "reasoning": "talks collapsed", "key_news": [1]})
    st.set_copy(3, "news", 10)
    ev = run(nt.cycle())
    assert len(calls) == 1 and "invade Iran" in calls[0]
    f = nt.forecasts()[0]
    assert f["p_yes"] == 0.40 and f["price"] == 0.20 and f["reasoning"] == "talks collapsed"
    pos = paper.positions("news")
    assert len(pos) == 1 and pos[0]["outcome"] == "Yes" and pos[0]["asset"] == "Y1"
    assert paper.positions("u:3")[0]["cost"] == pytest.approx(10)
    assert {e["kind"] for e in ev} == {"news_buy", "copy_buy"}
    assert run(nt.cycle()) == [] and len(calls) == 1          # повторно тот же рынок раньше 12 ч не спрашиваем


def test_low_confidence_is_recorded_but_not_traded(tmp_path):
    st, paper, nt, calls = make(tmp_path, {"p_yes": 0.9, "confidence": "low", "reasoning": "r"})
    assert run(nt.cycle()) == [] and paper.positions("news") == [] and len(nt.forecasts()) == 1


def test_resolution_scores_forecasts(tmp_path):
    st, paper, nt, calls = make(tmp_path, {"p_yes": 0.05, "confidence": "high", "reasoning": "r"})
    run(nt.cycle())
    nt.client.winner = "N1"
    run(nt.resolve())
    s = nt.track_record()
    assert s["n"] == 1 and s["brier_model"] == pytest.approx(0.05 ** 2) and s["model_better"] is True
