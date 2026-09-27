"""Модель «выиграет ли ставка»: учится на истории крупных кошельков, проверяется на будущем.

Нет заглядывания в будущее: статистика кошелька считается только по рынкам, закрытым до даты среза,
а обучаются и проверяются на рынках, закрытых после неё. База сравнения — сама цена рынка:
модель полезна, только если на проверочном периоде её вероятности точнее цен.
"""
import math
import pickle
import random
import sqlite3
import time
from pathlib import Path

from . import scoring
from .classify import category

FEATURES = ["logit_p", "p", "known_wallet", "post_edge", "log_n", "roi", "cat_edge", "log_cat_n",
            "log_stake", "cat_news", "cat_sports", "cat_crypto", "longshot", "favourite"]
MODEL_FILE = "model.pkl"


# ------------------------------------------------------------------ данные
def load_rows(db_path, today="2026-09-27"):
    """(wallet, price, stake $, pnl $, won, title, slug, event, дата исхода YYYY-MM-DD).
    Дата исхода: время закрытия позиции, если есть, иначе срок рынка, но не позже сегодня."""
    c = sqlite3.connect(db_path, timeout=60)
    rows = c.execute(f"""
        select wallet, avg_price, stake, pnl, cast(cur_price as integer), title, slug, event_slug,
               case when ts is not null and ts > 0 then strftime('%Y-%m-%d', ts, 'unixepoch')
                    else min(substr(end_date, 1, 10), '{today}') end
        from positions where cur_price in (0, 1) and end_date > '2000'""").fetchall()
    c.close()
    return rows


def _held(r, pmin=0.03, min_stake=10):
    _w, p, stake, pnl, won = r[:5]
    return pmin <= p <= 1 - pmin and stake >= min_stake and scoring.held_to_resolution(p, stake, pnl, won)


def wallet_features(rows, cutoff):
    """Статистика кошельков только по ставкам, закрытым строго до среза."""
    by = {}
    for r in rows:
        if r[8] < cutoff and _held(r):
            w, p, stake, pnl, won, title, slug, ev, _d = r
            by.setdefault(w, []).append((p, int(won), stake, pnl, ev or title, category(title, slug)))
    wallets = sorted(by)
    stats = [scoring.wallet_stats(by[w]) for w in wallets]
    post, _tau2 = scoring.eb_shrink([s["edge"] for s in stats], [s["se"] for s in stats])
    out = {}
    for w, s, pe in zip(wallets, stats, post):
        cats = {c: ((v["wins"] - v["exp"]) / v["n"], v["n"]) for c, v in s["cats"].items()}
        out[w] = dict(post_edge=pe, n=s["n"], roi=s["roi"], cats=cats)
    return out


def features(p, stake, cat, wf):
    known = wf is not None
    wf = wf or {}
    cat_edge, cat_n = (wf.get("cats") or {}).get(cat, (0.0, 0))
    shrink = cat_n / (cat_n + 50.0)          # край в категории по малой выборке сильно сжимаем
    return [
        math.log(p / (1 - p)), p, 1.0 if known else 0.0,
        wf.get("post_edge", 0.0), math.log1p(wf.get("n", 0)), max(-1.0, min(1.0, wf.get("roi", 0.0))),
        cat_edge * shrink, math.log1p(cat_n), math.log(max(stake, 1.0)),
        1.0 if cat == "news" else 0.0, 1.0 if cat == "sports" else 0.0, 1.0 if cat == "crypto" else 0.0,
        1.0 if p < 0.2 else 0.0, 1.0 if p > 0.8 else 0.0,
    ]


def dataset(rows, wf, start, end):
    X, y, P, ev = [], [], [], []
    for r in rows:
        if start <= r[8] < end and _held(r):
            w, p, stake, pnl, won, title, slug, e, _d = r
            X.append(features(p, stake, category(title, slug), wf.get(w)))
            y.append(int(won)); P.append(p); ev.append(e or title)
    return X, y, P, ev


# ------------------------------------------------------------------ метрики
def log_loss(y, q):
    eps = 1e-6
    return -sum(yi * math.log(max(eps, qi)) + (1 - yi) * math.log(max(eps, 1 - qi)) for yi, qi in zip(y, q)) / len(y)


def brier(y, q):
    return sum((qi - yi) ** 2 for yi, qi in zip(y, q)) / len(y)


def strategy_roi(y, q, P, ev, margin, n_boot=1000, seed=7):
    """Ставим $1 везде, где модель выше цены на `margin`. ROI с бутстрепом по событиям."""
    picks = [(yi, pi, ei) for yi, qi, pi, ei in zip(y, q, P, ev) if qi - pi >= margin]
    if not picks:
        return dict(n=0, roi=0.0, lo=0.0, hi=0.0, win=0.0, avg_p=0.0)
    ret = lambda xs: sum(yi / pi - 1 for yi, pi, _ in xs) / len(xs)
    by_ev = {}
    for x in picks:
        by_ev.setdefault(x[2], []).append(x)
    groups = list(by_ev.values())
    rnd = random.Random(seed)
    boots = []
    for _ in range(n_boot):
        sample = [x for _ in groups for x in rnd.choice(groups)]
        boots.append(ret(sample))
    boots.sort()
    return dict(n=len(picks), events=len(groups), roi=ret(picks), lo=boots[int(0.025 * n_boot)],
                hi=boots[int(0.975 * n_boot)], win=sum(x[0] for x in picks) / len(picks),
                avg_p=sum(x[1] for x in picks) / len(picks))


# ------------------------------------------------------------------ обучение
def train(db_path, out_dir, cut_train="2026-07-01", cut_cal="2026-08-01", cut_test="2026-08-15",
          end="2026-09-28", log=print):
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.isotonic import IsotonicRegression
    from sklearn.linear_model import LogisticRegression

    t0 = time.time()
    rows = load_rows(db_path)
    log(f"строк {len(rows):,}")
    wf_train = wallet_features(rows, cut_train)
    Xtr, ytr, Ptr, _ = dataset(rows, wf_train, cut_train, cut_cal)
    Xca, yca, Pca, _ = dataset(rows, wf_train, cut_cal, cut_test)
    wf_test = wallet_features(rows, cut_test)
    Xte, yte, Pte, Ete = dataset(rows, wf_test, cut_test, end)
    log(f"обучение {len(ytr):,} · калибровка {len(yca):,} · проверка {len(yte):,} · {time.time() - t0:.0f} с")

    models = {
        "gbm": HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=31,
                                              min_samples_leaf=200, l2_regularization=1.0, random_state=0),
        "logreg": LogisticRegression(max_iter=2000, C=1.0),
    }
    report = {"baseline_market": dict(log_loss=log_loss(yte, Pte), brier=brier(yte, Pte))}
    best = None
    for name, mdl in models.items():
        mdl.fit(Xtr, ytr)
        iso = IsotonicRegression(out_of_bounds="clip", y_min=0.001, y_max=0.999)
        iso.fit(mdl.predict_proba(Xca)[:, 1], yca)
        q_tr = iso.predict(mdl.predict_proba(Xtr)[:, 1])
        q_te = iso.predict(mdl.predict_proba(Xte)[:, 1])
        rep = dict(log_loss=log_loss(yte, q_te), brier=brier(yte, q_te), train_log_loss=log_loss(ytr, q_tr),
                   strategies={f"{m:.2f}": strategy_roi(yte, q_te, Pte, Ete, m) for m in (0.03, 0.05, 0.08)})
        report[name] = rep
        log(f"{name}: log-loss {rep['log_loss']:.4f} (рынок {report['baseline_market']['log_loss']:.4f}), "
            f"Brier {rep['brier']:.4f} (рынок {report['baseline_market']['brier']:.4f})")
        if best is None or rep["log_loss"] < report[best[0]]["log_loss"]:
            best = (name, mdl, iso)
    name, mdl, iso = best
    beats = report[name]["log_loss"] < report["baseline_market"]["log_loss"]
    s5 = report[name]["strategies"]["0.05"]
    report["chosen"] = name
    report["beats_market"] = beats
    report["tradable"] = bool(beats and s5["n"] >= 200 and s5["lo"] > 0)
    report["periods"] = dict(train=[cut_train, cut_cal], calibrate=[cut_cal, cut_test], test=[cut_test, end])
    report["sizes"] = dict(train=len(ytr), calibrate=len(yca), test=len(yte))
    report["trained_at"] = int(time.time())
    Path(out_dir).mkdir(exist_ok=True)
    with open(Path(out_dir) / MODEL_FILE, "wb") as f:
        pickle.dump(dict(model=mdl, calibrator=iso, features=FEATURES, report=report), f)
    return report


# ------------------------------------------------------------------ модель «против китов»
FADE_FEATURES = ["logit_p", "cat_news", "cat_sports", "cat_crypto", "longshot", "favourite"]
FADE_FILE = "fade_model.pkl"


def fade_features(p, cat):
    return [math.log(p / (1 - p)), 1.0 if cat == "news" else 0.0, 1.0 if cat == "sports" else 0.0,
            1.0 if cat == "crypto" else 0.0, 1.0 if p < 0.2 else 0.0, 1.0 if p > 0.8 else 0.0]


def fade_return(price, won, spread=0.01, fee=0.0):
    """Доход $1, поставленного на противоположный исход: он стоит 1 − цена кита + спред,
    плюс комиссия покупателя по рынку fee × c × (1 − c) за акцию."""
    c = min(0.99, 1 - price + spread)
    return (0 if won else 1) / (c + fee * c * (1 - c)) - 1


def train_fade(db_path, out_dir, cut="2026-07-01", cut_test="2026-08-15", end="2026-09-28",
               margin=0.02, spread=0.01, fee=0.05, log=print):
    """Цена + категория → вероятность, что сторона кита выиграет. Проверка — на всех позициях
    (и проданных раньше), выигрыш по исходу рынка, спред 1 цент на входе."""
    from sklearn.linear_model import LogisticRegression

    rows = load_rows(db_path)
    ok = lambda r: 0.03 <= r[1] <= 0.97 and r[2] >= 10
    tr = [r for r in rows if cut <= r[8] < cut_test and ok(r)]
    te = [r for r in rows if cut_test <= r[8] < end and ok(r)]
    Xtr = [fade_features(r[1], category(r[5], r[6])) for r in tr]
    Xte = [fade_features(r[1], category(r[5], r[6])) for r in te]
    ytr, yte = [r[4] for r in tr], [r[4] for r in te]
    lr = LogisticRegression(max_iter=1000).fit(Xtr, ytr)
    q = lr.predict_proba(Xte)[:, 1]
    # комиссия берётся по верхней оценке (0.05) на всех рынках: историю ставок комиссий мы не храним
    picks = [(fade_return(r[1], r[4], spread, fee), r[7] or r[5]) for r, qi in zip(te, q)
             if (1 - qi) - min(0.99, 1 - r[1] + spread) >= margin and 0.05 <= 1 - r[1] + spread <= 0.95]
    by = {}
    for v, e in picks:
        by.setdefault(e, []).append(v)
    groups = list(by.values())
    rnd = random.Random(7)
    # бутстреп по событиям: пересобираем события с возвращением
    boots = []
    for _ in range(500):
        sample = [v for _ in groups for v in rnd.choice(groups)]
        boots.append(sum(sample) / len(sample))
    boots.sort()
    roi = sum(v for v, _ in picks) / len(picks) if picks else 0.0
    report = dict(kind="fade", log_loss=log_loss(yte, q), market_log_loss=log_loss(yte, [r[1] for r in te]),
                  whale_win=sum(yte) / len(yte), whale_price=sum(r[1] for r in te) / len(te),
                  bets=len(picks), events=len(groups), roi=roi,
                  roi_lo=boots[int(0.025 * len(boots))] if boots else 0.0,
                  roi_hi=boots[int(0.975 * len(boots))] if boots else 0.0,
                  margin=margin, spread=spread, fee=fee, periods=dict(train=[cut, cut_test], test=[cut_test, end]),
                  sizes=dict(train=len(tr), test=len(te)), trained_at=int(time.time()))
    report["tradable"] = bool(report["log_loss"] < report["market_log_loss"] and report["roi_lo"] > 0)
    log(f"fade: log-loss {report['log_loss']:.4f} vs рынок {report['market_log_loss']:.4f}; "
        f"ставок {len(picks):,}, ROI {roi:+.2%} [{report['roi_lo']:+.2%}, {report['roi_hi']:+.2%}]")
    Path(out_dir).mkdir(exist_ok=True)
    with open(Path(out_dir) / FADE_FILE, "wb") as f:
        pickle.dump(dict(kind="fade", model=lr, report=report), f)
    save_fade_json(lr, report, Path(out_dir) / FADE_JSON)
    return report


FADE_JSON = "fade_model.json"


def save_fade_json(lr, report, path):
    """Логистическая регрессия → JSON: не зависит от версий Python и scikit-learn в облаке."""
    import json as _json
    Path(path).write_text(_json.dumps(dict(kind="fade", features=FADE_FEATURES, intercept=float(lr.intercept_[0]),
                                           coef=[float(c) for c in lr.coef_[0]], report=report), indent=1, default=str))


class Predictor:
    """Модель для бота: prob(цена, ставка, категория, признаки кошелька) → P(сторона кита выиграет).
    .json — коэффициенты модели «против китов» (чистый Python); .pkl — прежний формат scikit-learn."""

    def __init__(self, path):
        path = Path(path)
        self.cal = None
        if path.suffix == ".json":
            import json as _json
            d = _json.loads(path.read_text())
            self.kind, self.model, self.report = "fade", None, d["report"]
            self.intercept, self.coef = d["intercept"], d["coef"]
            return
        with open(path, "rb") as f:
            d = pickle.load(f)
        self.kind = d.get("kind", "wallet")
        self.model, self.report = d["model"], d["report"]
        self.cal = d.get("calibrator")

    def prob(self, p, stake, cat, wf):
        if self.kind == "fade":
            if self.model is None:
                z = self.intercept + sum(c * x for c, x in zip(self.coef, fade_features(p, cat)))
                return 1 / (1 + math.exp(-z))
            return float(self.model.predict_proba([fade_features(p, cat)])[:, 1][0])
        raw = self.model.predict_proba([features(p, stake, cat, wf)])[:, 1]
        return float(self.cal.predict(raw)[0])


# ------------------------------------------------------------------ решение о ставке
def decide(p_model, ask, bankroll, margin=0.05, kelly_frac=0.25, cap=0.03, min_usd=10, max_ask=0.95, min_ask=0.03):
    """Ставим, если модель выше цены на margin. Размер: доля Келли f* = (p − a)/(1 − a), ¼ от неё, потолок cap."""
    if not (min_ask <= ask <= max_ask) or p_model - ask < margin:
        return dict(bet=False, usd=0.0, edge=p_model - ask)
    kelly = (p_model - ask) / (1 - ask)
    usd = bankroll * min(cap, kelly_frac * kelly)
    if usd < min_usd:
        return dict(bet=False, usd=0.0, edge=p_model - ask)
    return dict(bet=True, usd=usd, edge=p_model - ask, kelly=kelly)
