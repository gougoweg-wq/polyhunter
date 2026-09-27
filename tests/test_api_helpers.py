from polyhunter import api


def test_parse_link():
    assert api.parse_link("https://polymarket.com/event/nfl-kc-mia-2026-09-27") == ("nfl-kc-mia-2026-09-27", None)
    assert api.parse_link("polymarket.com/event/ev-x/market-y?tid=1") == ("ev-x", "market-y")
    assert api.parse_link("https://polymarket.com/market/some-market") == (None, "some-market")
    assert api.parse_link("hello") == (None, None)


def test_normalize_trade():
    raw = {"transactionHash": "0xt", "asset": "A", "proxyWallet": "0xABC", "side": "BUY", "size": 100,
           "price": 0.25, "timestamp": 5, "title": "T", "slug": "s", "eventSlug": "e", "outcome": "Yes",
           "conditionId": "C", "name": "n"}
    t = api.normalize_trade(raw)
    assert t["wallet"] == "0xabc" and t["usd"] == 25 and t["event_slug"] == "e" and t["condition_id"] == "C"


def test_pick_market_prefers_slug_then_volume():
    ev = {"markets": [{"slug": "a", "volume": "5", "closed": False},
                      {"slug": "b", "volume": "50", "closed": False},
                      {"slug": "c", "volume": "500", "closed": True}]}
    assert api.pick_market(ev, "a")["slug"] == "a"
    assert api.pick_market(ev, None)["slug"] == "b"   # открытый с наибольшим объёмом


def test_smart_money_by_outcome():
    market = {"outcomes": '["Yes", "No"]', "outcomePrices": '["0.4", "0.6"]', "clobTokenIds": '["t1", "t2"]'}
    holders = [{"token": "t1", "holders": [{"proxyWallet": "0xS", "amount": 10000, "outcomeIndex": 0, "name": "s"},
                                           {"proxyWallet": "0xN", "amount": 5000, "outcomeIndex": 0, "name": ""}]},
               {"token": "t2", "holders": [{"proxyWallet": "0xF", "amount": 1000, "outcomeIndex": 1, "name": "f"}]}]
    scores = {"0xs": {"tier": "S", "score": 90, "wallet": "0xs", "name": "s"},
              "0xf": {"tier": "F", "score": 10, "wallet": "0xf", "name": "f"}}
    out = api.smart_money(market, holders, scores)
    yes, no = out["outcomes"]
    assert yes["outcome"] == "Yes" and yes["price"] == 0.4 and yes["smart_usd"] == 4000
    assert no["fade_usd"] == 600
    assert out["lean"] == "Yes"
    assert yes["top"][0]["wallet"] == "0xs"
