import math
import pytest
from polyhunter import scoring as s


def test_poisson_binomial_tail_matches_binomial():
    # 10 монет по 0.5: P(X>=8) = 56/1024
    assert s.poisson_binomial_tail([0.5] * 10, 8) == pytest.approx(56 / 1024)
    assert s.poisson_binomial_tail([0.3, 0.6], 0) == pytest.approx(1.0)


def test_bh_qvalues_known_example():
    q = s.bh_qvalues([0.01, 0.04, 0.03, 0.2])
    # отсортированные p: .01 .03 .04 .2 → q: .04 .0533 .0533 .2
    assert q == pytest.approx([0.04, 0.0533333, 0.0533333, 0.2], rel=1e-4)
    assert all(qi >= pi for qi, pi in zip(q, [0.01, 0.04, 0.03, 0.2]))


def test_eb_shrink_pulls_noisy_estimates_to_zero():
    edges = [0.10, 0.10, -0.02, 0.0, 0.01]
    ses = [0.20, 0.01, 0.02, 0.02, 0.02]
    post, tau2 = s.eb_shrink(edges, ses)
    assert tau2 >= 0
    assert abs(post[0]) < 0.03           # шумная оценка сильно сжата
    assert post[1] == pytest.approx(0.10, abs=0.02)  # точная почти не меняется


def test_smart_score_and_tiers():
    assert s.smart_score(0.0) == 50
    assert 85 <= s.smart_score(0.10) <= 90      # сильный реальный край ~10 п.п.
    assert 65 <= s.smart_score(0.04) <= 72
    assert s.smart_score(-0.10) <= 15
    assert s.smart_score(0.17) < 100             # шкала не упирается в потолок
    assert s.tier(q=0.01, post_edge=0.04, roi=0.1, n=100) == "S"
    assert s.tier(q=0.01, post_edge=0.04, roi=-0.1, n=100) != "S"   # без денег не элита
    assert s.tier(q=0.15, post_edge=0.025, roi=0.05, n=60) == "A"
    assert s.tier(q=0.9, post_edge=0.0, roi=0.0, n=60) == "C"
    assert s.tier(q=0.9, post_edge=-0.04, roi=-0.2, n=60) == "F"
    assert s.tier(q=0.9, post_edge=0.05, roi=0.5, n=5) == "?"        # мало данных
    assert s.tier(q=0.01, post_edge=0.08, roi=0.5, n=28) == "B"      # S и A требуют истории
    assert s.tier(q=0.01, post_edge=0.08, roi=0.5, n=35) == "A"


def test_held_to_resolution():
    # 100$ по 0.5 = 200 акций; выигрыш +100, проигрыш −100
    assert s.held_to_resolution(0.5, 100, 100, 1)
    assert s.held_to_resolution(0.5, 100, -100, 0)
    assert not s.held_to_resolution(0.5, 100, 20, 1)  # продал раньше


def test_wallet_stats_cluster_and_categories():
    # (price, won, stake, pnl, event, category)
    pos = [(0.5, 1, 100, 100, "e1", "news"), (0.5, 1, 100, 100, "e2", "news"),
           (0.5, 0, 100, -100, "e3", "sports"), (0.2, 1, 50, 200, "e4", "news")]
    st = s.wallet_stats(pos)
    assert st["n"] == 4 and st["wins"] == 3
    assert st["exp"] == pytest.approx(1.7)
    assert st["roi"] == pytest.approx(300 / 350)
    assert st["best_category"] == "news"
    assert st["edge"] == pytest.approx((3 - 1.7) / 4)
    assert st["se"] > 0 and 0 <= st["p"] <= 1
