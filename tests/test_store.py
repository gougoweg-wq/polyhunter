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
