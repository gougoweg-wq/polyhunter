from polyhunter import radar


def t(**kw):
    base = dict(tx="0x1", asset="A", wallet="0xw1", side="BUY", price=0.2, usd=6000, ts=1000,
                title="Will X resign by Friday?", slug="will-x-resign", outcome="Yes",
                condition_id="C", name="anon")
    base.update(kw)
    return base


def test_signal_kind_smart_and_fade():
    assert radar.signal_kind(t(usd=3000), {"tier": "S"}, min_usd=2000) == "smart"
    assert radar.signal_kind(t(usd=3000), {"tier": "A"}, min_usd=2000) == "smart"
    assert radar.signal_kind(t(usd=3000), {"tier": "F"}, min_usd=2000) == "fade"
    assert radar.signal_kind(t(usd=3000), {"tier": "C"}, min_usd=2000) is None
    assert radar.signal_kind(t(usd=500), {"tier": "S"}, min_usd=2000) is None
    assert radar.signal_kind(t(side="SELL"), {"tier": "S"}, min_usd=2000) is None
    assert radar.signal_kind(t(), None, min_usd=2000) is None


def test_fresh_whale_pattern():
    assert radar.is_fresh_whale(t(), history_n=0)
    assert not radar.is_fresh_whale(t(), history_n=50)                  # опытный игрок
    assert not radar.is_fresh_whale(t(price=0.8), history_n=0)          # не аутсайдер
    assert not radar.is_fresh_whale(t(usd=900), history_n=0)            # мелко
    assert not radar.is_fresh_whale(t(title="Lakers vs. Celtics", slug="nba-lal-bos"), history_n=0)  # спорт


def test_clusters_need_distinct_wallets_within_window():
    trades = [t(wallet="a", ts=1000, usd=8000, price=0.30), t(wallet="b", ts=1200, usd=7000, price=0.32),
              t(wallet="c", ts=1500, usd=9000, price=0.34), t(wallet="d", ts=5000, usd=9000),
              t(wallet="a", ts=1100, usd=8000, asset="B")]
    cl = radar.clusters(trades, window=600, min_wallets=3, min_usd=20000)
    assert len(cl) == 1
    c = cl[0]
    assert c["asset"] == "A" and c["wallets"] == 3 and c["usd"] == 24000
    assert abs(c["vwap"] - (8000 * .30 + 7000 * .32 + 9000 * .34) / 24000) < 1e-9


def test_trade_key_dedup():
    assert radar.trade_key(t()) == radar.trade_key(t(usd=1))
    assert radar.trade_key(t()) != radar.trade_key(t(tx="0x2"))


def test_signal_kind_skips_near_certain_prices():
    assert radar.signal_kind(t(usd=3000, price=0.99), {"tier": "S"}, min_usd=2000) is None
    assert radar.signal_kind(t(usd=3000, price=0.02), {"tier": "S"}, min_usd=2000) is None
    assert radar.signal_kind(t(usd=3000, price=0.95), {"tier": "S"}, min_usd=2000) == "smart"
