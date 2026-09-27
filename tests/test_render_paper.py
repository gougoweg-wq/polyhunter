from polyhunter import render

ACC = dict(cash=880.0, start=1000.0)
POS = [dict(asset="A1", outcome="Yes", title="Will <X>?", shares=200.0, cost=100.0, slug="s", event_slug="ev")]


def test_paper_card_shows_equity_pnl_and_positions():
    txt = render.paper_card(ACC, POS, {"A1": 0.62}, "ru")
    assert "$1,004" in txt and "+$4" in txt                 # 880 + 200×0.62 = 1004
    assert "Will &lt;X&gt;?" in txt and "0.62" in txt and "+24.0%" in txt
    assert "Счёт" in render.paper_card(ACC, [], {}, "ru")


def test_ai_card_honest_about_backtest():
    rep = dict(kind="fade", roi=0.083, roi_lo=0.078, roi_hi=0.089, bets=295722, log_loss=0.5235,
               market_log_loss=0.5322, tradable=True, periods={"test": ["2026-08-15", "2026-09-28"]})
    txt = render.ai_card(rep, dict(cash=950, start=1000), POS, {"A1": 0.5}, [], "ru")
    assert "+8.3%" in txt and "эксперимент" in txt.lower() and "2026-08-15" in txt
    assert "$1,050" in txt                                  # 950 + 200×0.5
    en = render.ai_card(dict(rep, tradable=False), dict(cash=1000, start=1000), [], {}, [], "en")
    assert "not trading" in en.lower()


def test_desk_card_and_leaders():
    d = dict(equity=1887.9, realized=883.6, markets=754, won=610, fills_24h=120, start=1000,
             last=[dict(slug="btc-updown-5m-1790535000", pnl=12.5)])
    txt = render.desk_card(d, "ru")
    assert "$1,888" in txt and "+$884" in txt and "754" in txt and "81%" in txt
    lb = render.leaders([("u:1", 1100.0, 100.0), ("ai", 1050.0, 50.0)], {"u:1": "Матвей"}, "ru")
    assert "1." in lb and "Матвей" in lb and "🤖" in lb


def test_trade_events():
    mk = dict(asset="A2", outcome="No", title="T", slug="s", event_slug="ev")
    a = render.paper_event(dict(kind="ai_buy", side="fade", mk=mk, price=0.52, usd=20, p_model=0.3,
                                edge=0.18, leader_outcome="Yes", leader_price=0.5, leader_tier="C"), "ru")
    assert "🤖" in a and "No" in a and "0.52" in a and "Yes" in a
    b = render.paper_event(dict(kind="copy_buy", chat=1, leader="ai", mk=mk, price=0.52, usd=20), "en")
    assert "Copied" in b and "$20" in b
    c = render.paper_event(dict(kind="settle", owner="u:1", won=True, payout=40, pnl=20, title="T", outcome="No"), "ru")
    assert "+$20" in c and "✅" in c


def test_signed_money_zero_has_no_sign():
    assert render.signed_money(-0.3) == "$0" and render.signed_money(0.2) == "$0"
    assert render.signed_money(-4) == "−$4" and render.signed_money(12) == "+$12"


def test_news_card_and_event():
    fc = [dict(question="Will the U.S. invade Iran before 2027?", p_yes=0.12, price=0.20, confidence="high",
               reasoning="Talks <continue>.", slug="s", event_slug="iran", ts=1790500000)]
    txt = render.news_card(dict(provider="groq", model="llama", ready=True), fc, dict(cash=990, start=1000), [], {},
                           dict(n=0, brier_model=None, brier_market=None, model_better=None), "ru")
    assert "invade Iran" in txt and "12%" in txt and "20%" in txt and "Talks &lt;continue&gt;." in txt and "llama" in txt
    off = render.news_card(dict(provider="groq", model="llama", ready=False), [], dict(cash=1000, start=1000), [], {},
                           dict(n=0), "en")
    assert "BRAIN_API_KEY" in off
    ev = render.paper_event(dict(kind="news_buy", mk=dict(outcome="No", title="T", slug="s", event_slug="e"), price=0.81,
                                 usd=15, p_yes=0.12, confidence="high", reasoning="r", market_price=0.2), "ru")
    assert "📰" in ev and "0.81" in ev and "12%" in ev
