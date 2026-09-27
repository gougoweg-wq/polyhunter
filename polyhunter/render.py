"""HTML-сообщения для Telegram. Всё, что пришло извне (названия рынков, ники), экранируется."""
import html
import time

from .i18n import TIER_ICON, tr

PM = "https://polymarket.com"


def esc(s):
    return html.escape(str(s or ""), quote=False)


def money(x):
    x = float(x or 0)
    return f"{'−' if x < 0 else ''}${abs(x):,.0f}"


def pp(x):
    return f"{x * 100:+.1f}"


def pct(x):
    return f"{x * 100:+.1f}%"


def short(addr):
    return f"{addr[:6]}…{addr[-4:]}" if addr and len(addr) > 12 else (addr or "")


def who(score_or_trade):
    name = (score_or_trade or {}).get("name") or ""
    if name and not name.startswith("0x") and len(name) < 40:
        return f"<b>{esc(name)}</b>"
    return f"<code>{short(score_or_trade.get('wallet', ''))}</code>"


def profile_url(wallet):
    return f"{PM}/profile/{wallet}"


def market_url(tr_):
    if tr_.get("event_slug"):
        return f"{PM}/event/{tr_['event_slug']}"
    return f"{PM}/market/{tr_.get('slug', '')}"


def price(p):
    return f"{p:.2f}"


def wallet_card(s, lang):
    t = s.get("tier", "?")
    lines = [
        f"{TIER_ICON.get(t, '')} {who(s)} · {tr(lang, 'card.tier')} <b>{t}</b> · "
        f"{tr(lang, 'card.score')} <b>{s.get('score', 50)}</b>/100",
        f"<code>{short(s['wallet'])}</code> · <a href=\"{profile_url(s['wallet'])}\">{tr(lang, 'card.profile')}</a>",
        "",
        f"<i>{tr(lang, 'card.meaning.' + t)}</i>",
        "",
        "📊 " + tr(lang, "card.edge", post=pp(s.get("post_edge", 0)), raw=pp(s.get("edge", 0)),
                   q=f"{s.get('q', 1):.3g}"),
        "🎯 " + tr(lang, "card.bets", n=s.get("n", 0), events=s.get("events", 0)),
        "✅ " + tr(lang, "card.wins", wins=s.get("wins", 0), exp=f"{s.get('exp', 0):.1f}"),
        "💰 " + tr(lang, "card.money", roi=pct(s.get("roi", 0)), pnl=money(s.get("pnl", 0))),
    ]
    if s.get("best_category"):
        lines.append("🏷 " + tr(lang, "card.best", cat=tr(lang, "cat." + s["best_category"])))
    if s.get("timing6h") is not None:
        lines.append("⚡ " + tr(lang, "card.timing", t=pp(s["timing6h"])))
    return "\n".join(lines)


def top_list(rows, cat, lang):
    if not rows:
        return tr(lang, "top.empty")
    out = [tr(lang, "top.title", cat=tr(lang, "cat." + cat)), ""]
    for i, s in enumerate(rows, 1):
        out.append(tr(lang, "top.row", i=i, icon=TIER_ICON.get(s["tier"], ""), tier=s["tier"],
                      score=s["score"], who=who(s), roi=pct(s["roi"]), n=s["n"]))
    out += ["", f"<i>{tr(lang, 'top.foot')}</i>"]
    return "\n".join(out)


def _ts(ts):
    return time.strftime("%H:%M UTC", time.gmtime(ts)) if ts else ""


def alert(kind, trade, score, lang, history_n=None):
    ident = score or trade
    if kind == "smart":
        head = tr(lang, "alert.smart", icon=TIER_ICON.get(score["tier"], ""), tier=score["tier"], who=who(ident))
    elif kind == "fade":
        head = tr(lang, "alert.fade", who=who(ident))
    elif kind == "follow":
        head = tr(lang, "alert.follow", who=who(ident))
    else:
        head = tr(lang, "alert.fresh", who=who(ident), hist=history_n if history_n is not None else "?")
    lines = [
        head,
        tr(lang, "alert.bought", outcome=esc(trade["outcome"]), price=price(trade["price"]), usd=money(trade["usd"])),
        f"📍 <a href=\"{market_url(trade)}\">{esc(trade['title'])}</a>",
    ]
    if kind in ("smart", "follow") and score:
        lines.append(tr(lang, "alert.stats", score=score["score"], post=pp(score["post_edge"]), roi=pct(score["roi"])))
    elif kind == "fade":
        lines.append(tr(lang, "alert.fade_note", pp=f"{abs(score['post_edge']) * 100:.1f}"))
    elif kind == "fresh":
        lines.append(f"<i>{tr(lang, 'alert.fresh_note')}</i>")
    lines.append(f"🕒 {_ts(trade.get('ts'))} · <a href=\"{profile_url(trade['wallet'])}\">{tr(lang, 'card.profile')}</a>")
    return "\n".join(lines)


def plural_ru(n, one, few, many):
    n10, n100 = n % 10, n % 100
    form = one if n10 == 1 and n100 != 11 else few if 2 <= n10 <= 4 and not 12 <= n100 <= 14 else many
    return f"{n} {form}"


def cluster_alert(c, lang):
    minutes = max(1, round((c["last_ts"] - c["first_ts"]) / 60))
    w = plural_ru(c["wallets"], "кошелёк", "кошелька", "кошельков") if lang == "ru" else \
        f"{c['wallets']} wallet{'s' if c['wallets'] != 1 else ''}"
    return "\n".join([
        tr(lang, "cluster.title", w=w, m=minutes, usd=money(c["usd"])),
        tr(lang, "cluster.body", outcome=esc(c["outcome"]), vwap=price(c["vwap"])),
        f"📍 <a href=\"{market_url(c)}\">{esc(c['title'])}</a>",
        f"🕒 {_ts(c['last_ts'])}",
    ])


def market_card(title, url, sm, lang):
    lines = [tr(lang, "market.title", title=f"<a href=\"{url}\">{esc(title)}</a>"), ""]
    for o in sm["outcomes"]:
        lines.append(tr(lang, "market.outcome", outcome=esc(o["outcome"]), price=price(o["price"])))
        if o["smart_usd"]:
            lines.append(tr(lang, "market.smart", usd=money(o["smart_usd"])))
        if o["fade_usd"]:
            lines.append(tr(lang, "market.fade", usd=money(o["fade_usd"])))
        for h in o["top"][:3]:
            lines.append(tr(lang, "market.holder", icon=TIER_ICON.get(h["tier"], ""), tier=h["tier"],
                            who=who(h), usd=money(h["usd"])))
        lines.append("")
    lines.append(tr(lang, "market.verdict_yes", outcome=esc(sm["lean"])) if sm["lean"]
                 else tr(lang, "market.verdict_none"))
    return "\n".join(lines)
