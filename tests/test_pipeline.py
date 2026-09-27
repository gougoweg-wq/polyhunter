import random
from polyhunter.pipeline import score_positions, score_single


def synth():
    random.seed(3)
    rows = []
    for w in range(40):
        wallet = f"0x{w:040x}"
        skill = 0.15 if w == 0 else (-0.15 if w == 1 else 0.0)
        for k in range(120):
            p = random.choice([0.3, 0.5, 0.7])
            won = 1 if random.random() < min(0.99, max(0.01, p + skill)) else 0
            stake = 100.0
            pnl = stake / p * (1 - p) if won else -stake
            title = "Will X happen?" if k % 2 else "Lakers vs. Celtics"
            rows.append((wallet, p, stake, pnl, won, title, "slug", f"ev{w}-{k}"))
        # позиция, проданная до исхода — должна быть отброшена
        rows.append((wallet, 0.5, 100.0, 7.0, 1, "Will Y?", "s", f"ev{w}-sold"))
    return rows


def test_skilled_wallet_ranks_first_and_bad_is_F():
    out, tau2 = score_positions(synth(), names={"0x" + "0" * 40: "genius"}, cat="all")
    by = {r["wallet"]: r for r in out}
    top = max(out, key=lambda r: r["score"])
    assert top["wallet"] == "0x" + "0" * 40 and top["name"] == "genius"
    assert top["tier"] in ("S", "A") and top["n"] == 120
    assert by["0x" + "0" * 39 + "1"]["tier"] == "F"
    assert tau2 > 0
    assert sum(r["tier"] in ("S", "A") for r in out) <= 3   # шумные нули не становятся элитой


def test_category_filter():
    out, _ = score_positions(synth(), names={}, cat="sports")
    assert all(r["n"] == 60 for r in out)


def test_score_single_uses_population_tau2():
    rows = [r for r in synth() if r[0] == "0x" + "0" * 40]
    s = score_single(rows, name="genius", tau2=0.01)
    assert s["n"] == 120 and s["name"] == "genius"
    assert 0 < s["post_edge"] < s["edge"]          # сжато, но не до нуля
    assert s["tier"] in ("S", "A", "B")
    assert score_single(rows[:5], name="", tau2=0.01) is None   # мало ставок
