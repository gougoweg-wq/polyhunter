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


# ------------------------------------------------------------------ бумажная торговля
def signed_money(x):
    if abs(x) < 0.5:
        return "$0"
    return f"{'+' if x >= 0 else '−'}${abs(x):,.0f}"


def _mark(pos, marks):
    return marks.get(pos["asset"], pos["cost"] / pos["shares"] if pos["shares"] else 0.0)


def paper_card(acc, positions, marks, lang):
    eq = acc["cash"] + sum(p["shares"] * _mark(p, marks) for p in positions)
    pnl = eq - acc["start"]
    lines = [tr(lang, "paper.title"),
             tr(lang, "paper.equity", eq=money(eq), cash=money(acc["cash"]), pnl=signed_money(pnl),
                pct=pct(pnl / acc["start"] if acc["start"] else 0)), ""]
    if not positions:
        lines.append(tr(lang, "paper.empty"))
    for i, p in enumerate(positions, 1):
        m = _mark(p, marks)
        entry = p["cost"] / p["shares"] if p["shares"] else 0
        val = p["shares"] * m
        lines.append(tr(lang, "paper.pos", i=i, outcome=esc(p["outcome"]), title=f"<a href=\"{market_url(p)}\">{esc(p['title'])}</a>",
                        shares=f"{p['shares']:,.0f}", entry=price(entry), mark=price(m),
                        pnl=f"{signed_money(val - p['cost'])} ({pct((val - p['cost']) / p['cost'] if p['cost'] else 0)})"))
    lines += ["", f"<i>{tr(lang, 'paper.foot')}</i>"]
    return "\n".join(lines)


def ai_card(rep, acc, positions, marks, trades, lang):
    lines = [tr(lang, "ai.title"), "", tr(lang, "ai.what"), ""]
    if rep:
        a, b = rep.get("periods", {}).get("test", ["?", "?"])
        lines.append("📐 " + tr(lang, "ai.backtest", a=a, b=b, bets=f"{rep.get('bets', 0):,}", roi=pct(rep.get("roi", 0)),
                                lo=pct(rep.get("roi_lo", 0)), hi=pct(rep.get("roi_hi", 0)),
                                ll=f"{rep.get('log_loss', 0):.4f}", mll=f"{rep.get('market_log_loss', 0):.4f}"))
        lines.append(f"<i>{tr(lang, 'ai.caveat')}</i>")
        if not rep.get("tradable"):
            lines.append("⛔ " + tr(lang, "ai.off"))
    eq = acc["cash"] + sum(p["shares"] * _mark(p, marks) for p in positions)
    lines += ["", "💼 " + tr(lang, "ai.account", eq=money(eq), pnl=signed_money(eq - acc["start"]), n=len(positions))]
    if trades:
        lines.append(tr(lang, "ai.last"))
        for t in trades[:5]:
            pl = f" · {signed_money(t['pnl'])}" if t.get("pnl") is not None else ""
            lines.append(f"  {t['side']} <b>{esc(t['outcome'])}</b> {price(t['price'])} · {money(t['usd'])}{pl} · {esc(t['title'])[:50]}")
    return "\n".join(lines)


def desk_card(d, lang):
    if not d:
        return tr(lang, "desk.none")
    lines = [tr(lang, "desk.title"), "",
             tr(lang, "desk.body", eq=money(d["equity"]), start=money(d["start"]), pnl=signed_money(d["realized"]),
                m=d["markets"], winp=f"{d['won'] / d['markets']:.0%}" if d["markets"] else "—", f=d["fills_24h"])]
    if d.get("last"):
        lines += ["", tr(lang, "desk.last")]
        for r in d["last"][:5]:
            ts = int(r["slug"].rsplit("-", 1)[-1]) if r["slug"].rsplit("-", 1)[-1].isdigit() else 0
            lines.append(f"  {_ts(ts)} · {signed_money(r['pnl'] or 0)}")
    return "\n".join(lines)


def leaders(rows, names, lang):
    if not rows:
        return tr(lang, "lead.empty")
    out = [tr(lang, "lead.title"), ""]
    for i, (owner, eq, pnl) in enumerate(rows, 1):
        who_ = {"ai": "🤖 AI", "desk": "⚡ polydesk", "news": "📰 News"}.get(owner) or esc(names.get(owner) or owner)
        out.append(f"{i}. {who_} · {money(eq)} · <b>{signed_money(pnl)}</b>")
    return "\n".join(out)


def paper_event(e, lang):
    k = e["kind"]
    mk = e.get("mk") or {}
    if k == "ai_buy":
        key = "ev.ai_fade" if e.get("side") == "fade" else "ev.ai_follow"
        head = tr(lang, key, tier=e.get("leader_tier", "?"), lo=esc(e.get("leader_outcome", "")),
                  lp=price(e.get("leader_price", 0)), outcome=esc(mk.get("outcome", "")), price=price(e["price"]),
                  usd=money(e["usd"]), pm=price(1 - e["p_model"] if e.get("side") == "fade" else e["p_model"]))
        return head + f"\n📍 <a href=\"{market_url(mk)}\">{esc(mk.get('title', ''))}</a>"
    leader = {"ai": "AI", "news": "News"}.get(e.get("leader")) or short(e.get("leader", ""))
    if k == "news_buy":
        return tr(lang, "ev.news_buy", outcome=esc(mk.get("outcome", "")), price=price(e["price"]), usd=money(e["usd"]),
                  p=f"{e['p_yes']:.0%}", m=f"{e['market_price']:.0%}", conf=e.get("confidence", ""),
                  r=esc(e.get("reasoning", ""))[:300]) + f"\n📍 <a href=\"{market_url(mk)}\">{esc(mk.get('title', ''))}</a>"
    if k == "copy_buy":
        return tr(lang, "ev.copy_buy", leader=leader, outcome=esc(mk.get("outcome", "")), price=price(e["price"]),
                  usd=money(e["usd"])) + f"\n📍 <a href=\"{market_url(mk)}\">{esc(mk.get('title', ''))}</a>"
    if k == "copy_sell":
        return tr(lang, "ev.copy_sell", leader=leader, frac=f"{e['fraction']:.0%}", outcome=esc(mk.get("outcome", "")),
                  price=price(e["price"]), pnl=signed_money(e["pnl"]))
    if k == "copy_fail":
        return tr(lang, "ev.copy_fail", leader=leader, reason=tr(lang, "err." + e.get("reason", "cash")))
    if k == "settle":
        key = "ev.settle_win" if e["won"] else "ev.settle_loss"
        return tr(lang, key, outcome=esc(e.get("outcome", "")), pnl=signed_money(e["pnl"])) + f"\n{esc(e.get('title', ''))}"
    return ""


def news_card(cfg, forecasts, acc, positions, marks, track, lang):
    lines = [tr(lang, "news.title"), "", tr(lang, "news.what"), ""]
    lines.append("🧠 " + (tr(lang, "news.brain", provider=esc(cfg["provider"]), model=esc(cfg["model"])) if cfg.get("ready")
                         else tr(lang, "news.nokey")))
    if forecasts:
        lines.append("")
        for f in forecasts[:6]:
            lines.append(tr(lang, "news.fc", q=f"<a href=\"{market_url(f)}\">{esc(f['question'])}</a>", p=f"{f['p_yes']:.0%}",
                            m=f"{f['price']:.0%}", conf=esc(f["confidence"]), r=esc(f.get("reasoning") or "")[:220]))
    lines.append("")
    if track.get("n"):
        lines.append("🎯 " + tr(lang, "news.track", n=track["n"], bm=f"{track['brier_model']:.3f}", bk=f"{track['brier_market']:.3f}"))
    else:
        lines.append("🎯 " + tr(lang, "news.track_none"))
    eq = acc["cash"] + sum(p["shares"] * _mark(p, marks) for p in positions)
    lines.append("💼 " + tr(lang, "news.account", eq=money(eq), pnl=signed_money(eq - acc["start"]), n=len(positions)))
    return "\n".join(lines)


def live_line(rec, lang):
    if not rec.get("n"):
        return tr(lang, "live.none")
    return tr(lang, "live.line", n=rec["n"], m=pct(rec["mean"]), lo=pct(rec["lo"]), hi=pct(rec["hi"]),
              need=rec["needed"] if rec.get("needed") else "—")
