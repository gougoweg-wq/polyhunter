from polyhunter import render

SCORE = dict(wallet="0x23d81ba9371e576015c1e562db09c689f56b0288", name="flawfence", tier="S", score=87,
             post_edge=0.031, edge=0.042, q=0.003, n=163, events=107, wins=92, exp=74.4, roi=0.261,
             pnl=154178.0, best_category="news", timing6h=0.054)


def test_money_and_pp_format():
    assert render.money(154178) == "$154,178"
    assert render.money(-41220.4) == "−$41,220"
    assert render.pp(0.031) == "+3.1"
    assert render.pct(0.261) == "+26.1%"


def test_wallet_card_ru_and_en():
    ru = render.wallet_card(SCORE, "ru")
    assert "flawfence" in ru and "https://polymarket.com/profile/0x23d81ba9" in ru
    assert "+26.1%" in ru and "87" in ru and "новост" in ru
    en = render.wallet_card(SCORE, "en")
    assert "news" in en and "Edge" in en


def test_escaping_titles():
    tr = dict(side="BUY", price=0.32, usd=12400, title="A < B & C", slug="s", event_slug="ev",
              outcome="Yes", wallet=SCORE["wallet"], name="x<y", ts=1790516400)
    msg = render.alert("smart", tr, SCORE, "ru")
    assert "A &lt; B &amp; C" in msg and "x&lt;y" not in msg  # имя берётся из рейтинга
    assert "https://polymarket.com/event/ev" in msg and "0.32" in msg and "$12,400" in msg


def test_fresh_whale_and_cluster_alerts():
    tr = dict(side="BUY", price=0.18, usd=25000, title="Will X resign?", slug="s", event_slug="",
              outcome="Yes", wallet="0xabc0000000000000000000000000000000000001", name="", ts=1790516400)
    msg = render.alert("fresh", tr, None, "en", history_n=0)
    assert "Fresh whale" in msg and "https://polymarket.com/market/s" in msg
    cl = dict(asset="A", title="T", slug="s", outcome="No", wallets=4, usd=58000, vwap=0.41,
              first_ts=1790516000, last_ts=1790516400)
    m2 = render.cluster_alert(cl, "ru")
    assert "4" in m2 and "$58,000" in m2 and "0.41" in m2


def test_top_list_numbered():
    rows = [dict(SCORE), dict(SCORE, name="", wallet="0xabc0000000000000000000000000000000000001", tier="A", score=74)]
    txt = render.top_list(rows, "news", "ru")
    assert "1." in txt and "2." in txt and "0xabc0…0001" in txt


def test_market_card():
    sm = {"outcomes": [dict(outcome="Yes", price=0.4, smart_usd=4000, fade_usd=0,
                            top=[dict(wallet="0xs" + "0" * 39, name="shark", usd=4000, tier="S")]),
                       dict(outcome="No", price=0.6, smart_usd=0, fade_usd=600, top=[])],
          "lean": "Yes"}
    txt = render.market_card("Will <X> happen?", "https://polymarket.com/event/x", sm, "ru")
    assert "Will &lt;X&gt; happen?" in txt and "$4,000" in txt and "shark" in txt
    assert "«Yes»" in txt and "0.40" in txt
    txt2 = render.market_card("T", "u", dict(sm, lean=None), "en")
    assert "no clear lean" in txt2


def test_follow_alert_with_and_without_score():
    tr_ = dict(side="BUY", price=0.55, usd=9000, title="T", slug="s", event_slug="ev", outcome="No",
               wallet=SCORE["wallet"], name="", ts=1790516400)
    a = render.alert("follow", tr_, SCORE, "ru")
    assert a.startswith("⭐") and "flawfence" in a and "0.55" in a and "Рейтинг 87" in a
    b = render.alert("follow", tr_, None, "en")
    assert b.startswith("⭐") and "0x23d8…0288" in b and "$9,000" in b


def test_russian_plural_wallets():
    assert render.plural_ru(1, "кошелёк", "кошелька", "кошельков") == "1 кошелёк"
    assert render.plural_ru(3, "кошелёк", "кошелька", "кошельков") == "3 кошелька"
    assert render.plural_ru(9, "кошелёк", "кошелька", "кошельков") == "9 кошельков"
    assert render.plural_ru(11, "кошелёк", "кошелька", "кошельков") == "11 кошельков"
    assert render.plural_ru(22, "кошелёк", "кошелька", "кошельков") == "22 кошелька"
    cl = dict(asset="A", title="T", slug="s", outcome="No", wallets=9, usd=58000, vwap=0.41,
              first_ts=1790516000, last_ts=1790516400)
    assert "9 кошельков" in render.cluster_alert(cl, "ru")
    assert "9 wallets" in render.cluster_alert(cl, "en")
