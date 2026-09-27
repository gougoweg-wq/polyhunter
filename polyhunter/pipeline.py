"""Конвейер рейтинга: позиции из hunter.db → оценки кошельков по категориям."""
import json
import sqlite3
from pathlib import Path

from . import scoring
from .classify import category

CATS = ("all", "news", "sports", "crypto")


def score_positions(rows, names, cat="all", min_n=20, pmin=0.03, min_stake=50, timing=None):
    """rows: (wallet, avg_price, stake $, pnl $, won 0/1, title, slug, event_slug).

    Возвращает (оценки, τ²). Берутся только позиции, удержанные до исхода.
    """
    by = {}
    for w, p, stake, pnl, won, title, slug, ev in rows:
        if not (pmin <= p <= 1 - pmin) or stake < min_stake:
            continue
        if not scoring.held_to_resolution(p, stake, pnl, won):
            continue
        c = category(title, slug)
        if cat != "all" and c != cat:
            continue
        by.setdefault(w, []).append((p, int(won), stake, pnl, ev or title, c))
    stats = []
    for w, pos in by.items():
        if len(pos) >= min_n:
            st = scoring.wallet_stats(pos)
            st["wallet"] = w
            stats.append(st)
    if not stats:
        return [], 0.0
    post, tau2 = scoring.eb_shrink([s["edge"] for s in stats], [s["se"] for s in stats])
    qs = scoring.bh_qvalues([s["p"] for s in stats])
    out = []
    for s, pe, q in zip(stats, post, qs):
        out.append(dict(
            wallet=s["wallet"], name=names.get(s["wallet"], ""),
            tier=scoring.tier(q, pe, s["roi"], s["n"], min_n=min_n), score=scoring.smart_score(pe),
            post_edge=pe, edge=s["edge"], q=q, n=s["n"], events=s["events"], wins=s["wins"], exp=s["exp"],
            roi=s["roi"], pnl=s["pnl"], stake=s["stake"], best_category=s["best_category"],
            timing6h=(timing or {}).get(s["wallet"]),
        ))
    return out, tau2


def score_single(rows, name="", tau2=0.01, min_n=20, pmin=0.03, min_stake=50):
    """Оценка одного кошелька по τ² всей выборки (из последнего пересчёта). q = p: одна проверка."""
    pos = []
    for w, p, stake, pnl, won, title, slug, ev in rows:
        if pmin <= p <= 1 - pmin and stake >= min_stake and scoring.held_to_resolution(p, stake, pnl, won):
            pos.append((p, int(won), stake, pnl, ev or title, category(title, slug)))
    if len(pos) < min_n:
        return None
    st = scoring.wallet_stats(pos)
    pe = st["edge"] * tau2 / (tau2 + st["se"] ** 2) if tau2 + st["se"] ** 2 > 0 else 0.0
    return dict(wallet=rows[0][0], name=name, tier=scoring.tier(st["p"], pe, st["roi"], st["n"], min_n=min_n),
                score=scoring.smart_score(pe), post_edge=pe, edge=st["edge"], q=st["p"], n=st["n"],
                events=st["events"], wins=st["wins"], exp=st["exp"], roi=st["roi"], pnl=st["pnl"],
                stake=st["stake"], best_category=st["best_category"], timing6h=None)


def load_rows(db_path):
    c = sqlite3.connect(db_path, timeout=60)
    rows = c.execute("""select wallet, avg_price, stake, pnl, cast(cur_price as integer), title, slug, event_slug
                        from positions where cur_price in (0, 1)""").fetchall()
    names = {w: n for w, n in c.execute("select wallet, max(name) from trades where name != '' group by wallet")}
    c.close()
    return rows, names


def load_timing(data_dir):
    """Сдвиг цены за 6 ч после входа относительно похожих ставок контроля (из hunter.py timing)."""
    f = Path(data_dir) / "timing_news.json"
    if not f.exists():
        return {}
    d = json.loads(f.read_text())
    ctrl = [t for k, v in d.items() if k.startswith("контроль") for t in v]

    def key(t):
        h = t["hrs_left"]
        hb = 0 if h < 6 else 1 if h < 24 else 2 if h < 72 else 3 if h < 240 else 4
        return (t["final"], min(int(t["price"] * 10), 9), hb)

    cells = {}
    for t in ctrl:
        if t["moves"][2] is not None:
            cells.setdefault(key(t), []).append(t["moves"][2])
    out = {}
    for k, v in d.items():
        if not k.startswith("значимые"):
            continue
        bym = {}
        for t in v:
            cc = cells.get(key(t), [])
            if t["moves"][2] is None or len(cc) < 3:
                continue
            bym.setdefault(t["title"], []).append(t["moves"][2] - sum(cc) / len(cc))
        if len(bym) >= 4:
            out[k.split("|", 1)[1]] = sum(sum(x) / len(x) for x in bym.values()) / len(bym)
    return out


def rescore(db_path, store, data_dir):
    rows, names = load_rows(db_path)
    timing = load_timing(data_dir)
    summary = {}
    for cat in CATS:
        out, tau2 = score_positions(rows, names, cat, timing=timing if cat in ("all", "news") else None)
        store.save_scores(cat, out)
        store.set_meta(f"tau2:{cat}", tau2)
        summary[cat] = dict(wallets=len(out), tau2=tau2)
    return summary


def market_facts(db_path):
    """Сводка для /stats: насколько крупные игроки в сумме отстают от цен."""
    rows, _ = load_rows(db_path)
    held = [(p, won) for _w, p, st, pnl, won, *_ in rows
            if 0.03 <= p <= 0.97 and st >= 50 and scoring.held_to_resolution(p, st, pnl, won)]
    low = [(p, w) for p, w in held if p < 0.2]
    wallets = len({r[0] for r in rows})
    n = len(held) or 1
    return dict(wallets=wallets, bets=len(held),
                wr=sum(w for _, w in held) / n, er=sum(p for p, _ in held) / n,
                lw=sum(w for _, w in low) / (len(low) or 1), le=sum(p for p, _ in low) / (len(low) or 1))
