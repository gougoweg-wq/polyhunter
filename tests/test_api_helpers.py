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


def test_parse_book_sorts_best_first():
    raw = {"bids": [{"price": "0.001", "size": "65"}, {"price": "0.40", "size": "10"}, {"price": "0.45", "size": "5"}],
           "asks": [{"price": "0.999", "size": "7"}, {"price": "0.55", "size": "3"}, {"price": "0.50", "size": "8"}]}
    bids, asks = api.parse_book(raw)
    assert bids[0] == (0.45, 5.0) and asks[0] == (0.50, 8.0) and asks[-1] == (0.999, 7.0)


def test_winner_token_and_fee_rate():
    m = {"closed": True, "outcomePrices": '["0", "1"]', "clobTokenIds": '["t1", "t2"]',
         "feeSchedule": {"exponent": 1, "rate": 0.05, "takerOnly": True}}
    assert api.winner_token(m) == "t2"
    assert api.winner_token(dict(m, closed=False)) is None
    assert api.winner_token(dict(m, outcomePrices='["0.5", "0.5"]')) is None
    assert api.fee_rate(m) == 0.05 and api.fee_rate({}) == 0.0
