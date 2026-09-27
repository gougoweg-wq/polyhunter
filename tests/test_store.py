from polyhunter.store import Store

W1 = "0x23d81ba9371e576015c1e562db09c689f56b0288"
W2 = "0xabc0000000000000000000000000000000000001"


def mk(tmp_path):
    return Store(tmp_path / "t.db")


def test_user_defaults_and_toggles(tmp_path):
    st = mk(tmp_path)
    u = st.user(42, "ru")
    assert u["lang"] == "ru" and u["threshold"] == 5000 and u["alerts"]["smart"] is True
    st.toggle_alert(42, "fresh")
    assert st.user(42)["alerts"]["fresh"] is False
    st.set_threshold(42, 2500)
    assert st.user(42)["threshold"] == 2500


def test_follow_unfollow(tmp_path):
    st = mk(tmp_path)
    st.follow(1, W1); st.follow(1, W1); st.follow(2, W1)
    assert st.following(1) == [W1]
    assert sorted(st.followers(W1)) == [1, 2]
    st.unfollow(1, W1)
    assert st.following(1) == []


def test_scores_upsert_top_and_lookup(tmp_path):
    st = mk(tmp_path)
    st.save_scores("news", [dict(wallet=W1, name="flawfence", tier="S", score=87, post_edge=.03, edge=.04, q=.003,
                                 n=163, events=107, wins=92, exp=74.4, roi=.26, pnl=154178, stake=590000,
                                 best_category="news", timing6h=None),
                            dict(wallet=W2, name="", tier="F", score=10, post_edge=-.05, edge=-.06, q=.5,
                                 n=40, events=30, wins=5, exp=12, roi=-.4, pnl=-9000, stake=20000,
                                 best_category="news", timing6h=None)])
    assert [r["wallet"] for r in st.top("news", 10)] == [W1]
    assert st.score(W1, "news")["tier"] == "S"
    assert st.find_wallet("FlawFence") == W1
    assert st.find_wallet(W2.upper()) == W2.lower()
    assert st.find_wallet("0xabc0") == W2


def test_seen_trades_dedup_and_signal_log(tmp_path):
    st = mk(tmp_path)
    k = ("0xtx", "A", W1, "BUY")
    assert st.mark_seen(k) is True
    assert st.mark_seen(k) is False
    st.log_signal("smart", "<b>msg</b>", 1790516400)
    assert st.recent_signals(5)[0]["text"] == "<b>msg</b>"


def test_top_orders_by_tier_then_score(tmp_path):
    st = mk(tmp_path)
    base = dict(post_edge=.05, edge=.05, q=.01, n=100, events=90, wins=60, exp=55, roi=.1, pnl=1, stake=10,
                best_category="news", timing6h=None, name="")
    st.save_scores("news", [dict(base, wallet="0xb", tier="B", score=95), dict(base, wallet="0xs", tier="S", score=80),
                            dict(base, wallet="0xa", tier="A", score=90), dict(base, wallet="0xs2", tier="S", score=85)])
    assert [r["wallet"] for r in st.top("news", 10)] == ["0xs2", "0xs", "0xa", "0xb"]


def test_quick_actions_and_ai_alert_type(tmp_path):
    st = mk(tmp_path)
    qid = st.put_quick({"a": "buy", "asset": "7" * 77, "usd": 50})
    assert len(f"q:{qid}") < 64 and st.get_quick(qid)["asset"] == "7" * 77
    assert st.get_quick(999999) is None
    u = st.user(9, "ru")
    assert u["alerts"]["ai"] is False
    st.toggle_alert(9, "ai")
    assert st.user(9)["alerts"]["ai"] is True


def test_store_creates_missing_directory(tmp_path):
    st = Store(tmp_path / "no" / "such" / "dir" / "b.db")
    assert st.user(1)["lang"] == "en"
