"""Детекторы сигналов по ленте сделок. Чистые функции — без сети и базы."""
from .classify import category

SMART_TIERS = {"S", "A"}
FADE_TIERS = {"F"}


def trade_key(tr):
    return (tr["tx"], tr["asset"], tr["wallet"], tr["side"])


def signal_kind(tr, score, min_usd=2000, pmin=0.03, pmax=0.95):
    """'smart' — крупная покупка кошелька тира S/A, 'fade' — тира F (сигнал «против»).
    Почти решённые исходы (цена > 0.95 или < 0.03) не сигнал: там нечего узнавать."""
    if not score or tr["side"] != "BUY" or tr["usd"] < min_usd or not (pmin <= tr["price"] <= pmax):
        return None
    if score.get("tier") in SMART_TIERS:
        return "smart"
    if score.get("tier") in FADE_TIERS:
        return "fade"
    return None


def is_fresh_whale(tr, history_n, min_usd=5000, max_price=0.35, max_history=3):
    """Новый кошелёк сразу ставит крупно на аутсайдера в новостном рынке —
    типичный рисунок ставок «со знанием»: деньги заводят на чистый адрес перед событием."""
    return (tr["side"] == "BUY" and tr["usd"] >= min_usd and tr["price"] <= max_price
            and history_n <= max_history and category(tr["title"], tr["slug"]) == "news")


def clusters(trades, window=600, min_wallets=3, min_usd=20000):
    """Несколько разных кошельков покупают один исход в пределах окна."""
    by_asset = {}
    for tr in trades:
        if tr["side"] == "BUY":
            by_asset.setdefault(tr["asset"], []).append(tr)
    out = []
    for asset, trs in by_asset.items():
        trs.sort(key=lambda x: x["ts"])
        best = None
        j = 0
        for i in range(len(trs)):
            while trs[i]["ts"] - trs[j]["ts"] > window:
                j += 1
            win = trs[j:i + 1]
            wallets = {x["wallet"] for x in win}
            usd = sum(x["usd"] for x in win)
            if len(wallets) >= min_wallets and usd >= min_usd and (best is None or usd > best["usd"]):
                best = dict(asset=asset, title=win[-1]["title"], slug=win[-1]["slug"],
                            outcome=win[-1]["outcome"], wallets=len(wallets), usd=usd,
                            vwap=sum(x["usd"] * x["price"] for x in win) / usd,
                            first_ts=win[0]["ts"], last_ts=win[-1]["ts"])
        if best:
            out.append(best)
    return sorted(out, key=lambda c: -c["usd"])
