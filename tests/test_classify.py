from polyhunter.classify import category


def test_sports_variants():
    assert category("Falcons vs. Packers", "nfl-atl-gb-2026-09-25") == "sports"
    assert category("Will Alexander Zverev win the 2026 Men's US Open?", "x") == "sports"
    assert category("RW Oberhausen leading at halftime?", "x") == "sports"
    assert category("Will PSG win the 2025–26 Champions League?", "x") == "sports"


def test_crypto():
    assert category("Bitcoin Up or Down - September 27, 9:40AM-9:45AM ET", "btc-updown-5m-1") == "crypto"


def test_news_default():
    assert category("US forces enter Iran by April 30?", "x") == "news"
    assert category("Will the Fed increase interest rates by 25 bps?", "x") == "news"
