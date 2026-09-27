import pytest
from polyhunter import news, brain

RSS = """<rss><channel>
<item><title>Ukraine ready for ceasefire &apos;right now&apos; - dw.com</title><link>https://n/1</link>
<pubDate>Sun, 27 Sep 2026 12:30:57 GMT</pubDate><source url="https://dw.com">DW</source></item>
<item><title>US seeks to revive talks - Al Jazeera</title><link>https://n/2</link>
<pubDate>Fri, 25 Sep 2026 18:32:40 GMT</pubDate><source url="https://aljazeera.com">Al Jazeera</source></item>
</channel></rss>"""


def test_parse_google_news_rss():
    items = news.parse_rss(RSS)
    assert len(items) == 2 and items[0]["title"] == "Ukraine ready for ceasefire 'right now'"
    assert items[0]["source"] == "DW" and items[0]["ts"] > items[1]["ts"]


def test_query_from_question():
    q = news.query_for("Will the U.S. invade Iran before 2027?")
    assert "invade" in q and "Iran" in q and "Will" not in q and "2027" not in q
    assert news.query_for("US-Iran ceasefire continues through...?") == "US-Iran ceasefire continues"


def test_dossier_and_prompt_are_bounded():
    items = [dict(title=f"headline {i}", source="S", ts=1790000000 + i, link="l") for i in range(80)]
    m = dict(question="Will X happen by Dec 31?", yes_price=0.23, end_date="2026-12-31", description="Resolves YES if X." * 200)
    prompt = brain.forecast_prompt(m, items, now_ts=1790100000)
    assert "Will X happen by Dec 31?" in prompt and "0.23" not in prompt   # цену модели не показываем: пусть думает сама
    import re
    assert len(re.findall(r"^\d+\. \[", prompt, re.M)) == 40 and len(prompt) < 12000


def test_parse_forecast_json_robustly():
    ok = brain.parse_forecast('Думаю...\n```json\n{"p_yes": 0.31, "confidence": "high", "reasoning": "r", "key_news": ["a"]}\n```')
    assert ok["p_yes"] == 0.31 and ok["confidence"] == "high"
    assert brain.parse_forecast('{"p_yes": 1.4}')["p_yes"] == 0.99          # вне диапазона — зажимаем
    assert brain.parse_forecast("no json here") is None


def test_news_decision():
    d = news.decide(p_yes=0.40, yes_ask=0.25, no_ask=0.76, confidence="high", bankroll=1000)
    assert d["side"] == "YES" and 0 < d["usd"] <= 15
    d = news.decide(p_yes=0.10, yes_ask=0.25, no_ask=0.76, confidence="high", bankroll=1000)
    assert d["side"] == "NO"
    assert news.decide(0.30, 0.25, 0.76, "high", 1000)["side"] is None       # перевес < 8 п.п.
    assert news.decide(0.60, 0.25, 0.76, "low", 1000)["side"] is None        # неуверенный прогноз не торгуем


def test_forecast_scoring_vs_market():
    rows = [dict(p_yes=0.8, price=0.6, outcome=1), dict(p_yes=0.3, price=0.5, outcome=0)]
    s = news.score_forecasts(rows)
    assert s["n"] == 2 and s["brier_model"] == pytest.approx(((0.2) ** 2 + 0.3 ** 2) / 2)
    assert s["brier_market"] == pytest.approx(((0.4) ** 2 + 0.5 ** 2) / 2) and s["model_better"]


def test_query_drops_polymarket_x_and_adds_recency():
    assert news.query_for("US x Iran ceasefire continues through September 30?") == "US Iran ceasefire continues"
    assert news.search_params("US Iran ceasefire")["q"] == "US Iran ceasefire when:7d"


def test_keyless_default_brain(monkeypatch):
    for k in ("BRAIN_PROVIDER", "BRAIN_API_KEY", "BRAIN_MODEL", "BRAIN_BASE_URL"):
        monkeypatch.delenv(k, raising=False)
    c = brain.config()
    assert c["provider"] == "pollinations" and brain.ready()            # без ключа работает сразу
    assert "Authorization" not in brain.headers(c)
    monkeypatch.setenv("BRAIN_PROVIDER", "groq")
    assert not brain.ready()                                             # groq без ключа — не готов
    monkeypatch.setenv("BRAIN_API_KEY", "k")
    assert brain.ready() and brain.headers(brain.config())["Authorization"] == "Bearer k"
