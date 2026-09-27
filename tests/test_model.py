import math
import pytest
from polyhunter import model as M

# (wallet, avg_price, stake, pnl, won, title, slug, event, end_date)
def row(w, p, won, end, title="Will X?", ev=None):
    stake = 100.0
    pnl = stake / p * (1 - p) if won else -stake
    return (w, p, stake, pnl, won, title, "s", ev or f"{w}-{end}-{p}", end)


def test_wallet_features_ignore_rows_after_cutoff():
    rows = [row("0xa", 0.5, 1, "2026-06-01"), row("0xa", 0.5, 1, "2026-06-02"),
            row("0xa", 0.5, 0, "2026-08-01")]
    f1 = M.wallet_features(rows, cutoff="2026-07-01")
    flipped = rows[:2] + [row("0xa", 0.5, 1, "2026-08-01")]
    f2 = M.wallet_features(flipped, cutoff="2026-07-01")
    assert f1 == f2                                   # исход после среза не влияет на признаки
    assert f1["0xa"]["n"] == 2


def test_feature_vector_is_stable():
    wf = {"0xa": dict(post_edge=0.05, n=40, roi=0.2, cats={"news": (0.06, 30)})}
    v = M.features(0.3, 500.0, "news", wf.get("0xa"))
    v0 = M.features(0.3, 500.0, "sports", None)       # незнакомый кошелёк
    assert len(v) == len(v0) == len(M.FEATURES)
    assert v[M.FEATURES.index("logit_p")] == pytest.approx(math.log(0.3 / 0.7))
    assert v[M.FEATURES.index("cat_news")] == 1 and v0[M.FEATURES.index("cat_sports")] == 1
    assert v0[M.FEATURES.index("known_wallet")] == 0


def test_decide_kelly_sizing_and_guards():
    d = M.decide(p_model=0.60, ask=0.50, bankroll=1000, margin=0.05, kelly_frac=0.25, cap=0.03)
    assert d["bet"] and d["usd"] == pytest.approx(min(1000 * 0.25 * 0.2, 30))   # Келли 0.2 → ¼ → 5% → потолок 3%
    assert not M.decide(0.53, 0.50, 1000)["bet"]      # край меньше порога
    assert not M.decide(0.99, 0.96, 1000)["bet"]      # почти решённый исход
    assert not M.decide(0.60, 0.50, 5)["bet"]         # слишком мало денег на ставку


def test_fade_features_and_predictor_kind(tmp_path):
    v = M.fade_features(0.3, "news")
    assert len(v) == len(M.FADE_FEATURES) and v[0] == pytest.approx(math.log(0.3 / 0.7))
    assert v[M.FADE_FEATURES.index("cat_news")] == 1


def test_fade_roi_uses_opposite_side_with_spread():
    # кит купил по 0.8 и проиграл: противоположный исход стоил 0.2 + спред 0.01 и выиграл
    r = M.fade_return(price=0.8, won=0, spread=0.01)
    assert r == pytest.approx(1 / 0.21 - 1)
    assert M.fade_return(price=0.8, won=1, spread=0.01) == -1.0


def test_fade_return_with_taker_fee():
    # цена противоположного 0.21, комиссия 0.05×0.21×0.79 за акцию
    cost = 0.21 + 0.05 * 0.21 * 0.79
    assert M.fade_return(price=0.8, won=0, spread=0.01, fee=0.05) == pytest.approx(1 / cost - 1)


def test_fade_model_json_matches_sklearn(tmp_path):
    from sklearn.linear_model import LogisticRegression
    import random
    random.seed(1)
    X = [M.fade_features(p, random.choice(["news", "sports", "crypto"])) for p in [random.uniform(.05, .95) for _ in range(400)]]
    y = [1 if random.random() < 0.9 * x[0] / 10 + 0.45 else 0 for x in X]
    lr = LogisticRegression(max_iter=500).fit(X, y)
    path = tmp_path / "fade_model.json"
    M.save_fade_json(lr, {"tradable": True}, path)
    pr = M.Predictor(path)
    for p, cat in [(0.2, "news"), (0.7, "sports"), (0.95, "crypto")]:
        assert pr.prob(p, 1000, cat, None) == pytest.approx(lr.predict_proba([M.fade_features(p, cat)])[0, 1], abs=1e-9)
    assert pr.report["tradable"] is True and pr.kind == "fade"
