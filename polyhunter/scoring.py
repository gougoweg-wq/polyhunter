"""Чистая статистика оценки кошельков.

Ставка по цене p при честном рынке выигрывает с вероятностью p. Край (edge) кошелька —
на сколько пунктов он выигрывает чаще, чем обещали цены. Сырой край шумный, поэтому
эмпирический Байес (DerSimonian–Laird) сжимает его к нулю пропорционально шуму.
"""
import math


def poisson_binomial_tail(ps, k):
    """P(X >= k), X — сумма независимых Бернулли(p_i). Точная ДП до 3000, дальше нормаль."""
    if k <= 0:
        return 1.0
    if len(ps) > 3000:
        mu = sum(ps)
        sd = math.sqrt(sum(p * (1 - p) for p in ps))
        return 0.5 * math.erfc((k - 0.5 - mu) / (sd * math.sqrt(2))) if sd else float(k <= mu)
    dist = [1.0]
    for p in ps:
        new = [0.0] * (len(dist) + 1)
        for j, v in enumerate(dist):
            new[j] += v * (1 - p)
            new[j + 1] += v * p
        dist = new
    return min(1.0, sum(dist[k:]))


def normal_sf(z):
    return 0.5 * math.erfc(z / math.sqrt(2))


def bh_qvalues(pvals):
    """q-values Бенджамини–Хохберга в исходном порядке."""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    q = [0.0] * m
    running = 1.0
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        running = min(running, pvals[i] * m / rank)
        q[i] = running
    return q


def eb_shrink(edges, ses):
    """Эмпирический Байес с априорным средним 0 и τ² по DerSimonian–Laird.

    Возвращает (апостериорные края, τ²). Кошелёк с шумной оценкой сжимается к нулю,
    с точной почти не меняется.
    """
    w = [1 / (s * s) if s > 0 else 0.0 for s in ses]
    sw = sum(w)
    if sw == 0 or len(edges) < 2:
        return [0.0] * len(edges), 0.0
    mean = sum(wi * e for wi, e in zip(w, edges)) / sw
    q = sum(wi * (e - mean) ** 2 for wi, e in zip(w, edges))
    denom = sw - sum(wi * wi for wi in w) / sw
    tau2 = max(0.0, (q - (len(edges) - 1)) / denom) if denom > 0 else 0.0
    post = [e * tau2 / (tau2 + s * s) if (tau2 + s * s) > 0 else 0.0 for e, s in zip(edges, ses)]
    return post, tau2


def smart_score(post_edge):
    """0–100: 50 — как рынок, +4 п.п. ≈ 69, +10 п.п. ≈ 88, −10 п.п. ≈ 12."""
    return round(50 + 50 * math.tanh(post_edge / 0.10))


def tier(q, post_edge, roi, n, min_n=20):
    """S и A требуют длинной истории: 50 и 30 ставок до исхода."""
    if n < min_n:
        return "?"
    if q < 0.05 and post_edge >= 0.03 and roi > 0 and n >= 50:
        return "S"
    if q < 0.2 and post_edge >= 0.02 and roi > 0 and n >= 30:
        return "A"
    if post_edge >= 0.01 and roi > 0:
        return "B"
    if post_edge <= -0.03:
        return "F"
    if post_edge <= -0.01:
        return "D"
    return "C"


def held_to_resolution(p, stake, pnl, won, tol=0.03):
    """Держал до исхода: выигрыш = акции×(1−p), проигрыш = −ставка."""
    if p <= 0:
        return False
    exp = stake / p * (1 - p) if won else -stake
    return abs(pnl - exp) <= tol * max(abs(exp), 1)


def wallet_stats(positions):
    """positions: [(price, won 0/1, stake $, pnl $, event, category)] — только удержанные до исхода."""
    n = len(positions)
    ps = [x[0] for x in positions]
    wins = sum(x[1] for x in positions)
    exp = sum(ps)
    var = sum(p * (1 - p) for p in ps)
    z = (wins - exp) / math.sqrt(var) if var else 0.0
    ev = {}
    for p, won, *_rest, event, _cat in positions:
        d = ev.setdefault(event, [0.0, 0.0])
        d[0] += won
        d[1] += p
    num = sum(a - b for a, b in ev.values())
    den = math.sqrt(sum((a - b) ** 2 for a, b in ev.values()))
    z_cl = num / den if den else 0.0
    p_ind = poisson_binomial_tail(ps, wins)
    stake = sum(x[2] for x in positions)
    pnl = sum(x[3] for x in positions)
    cats = {}
    for p, won, st, pl, _e, cat in positions:
        c = cats.setdefault(cat, dict(n=0, wins=0, exp=0.0, stake=0.0, pnl=0.0))
        c["n"] += 1; c["wins"] += won; c["exp"] += p; c["stake"] += st; c["pnl"] += pl
    best = max(cats, key=lambda k: cats[k]["wins"] - cats[k]["exp"]) if cats else None
    low = [x for x in positions if x[0] < 0.35]
    return dict(
        n=n, events=len(ev), wins=wins, exp=exp,
        edge=(wins - exp) / n if n else 0.0,
        se=math.sqrt(var) / n if n else 1.0,
        z=z, z_cl=z_cl,
        p=max(p_ind, normal_sf(z_cl)) if n else 1.0,
        stake=stake, pnl=pnl, roi=pnl / stake if stake else 0.0,
        low_n=len(low), low_wins=sum(x[1] for x in low), low_exp=sum(x[0] for x in low),
        cats=cats, best_category=best,
    )
