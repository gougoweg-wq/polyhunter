"""Команды бумажной торговли: счёт, покупка и продажа по кнопкам, копирование, модель, polydesk, лидеры."""
from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions, Message

from polyhunter import api, brain, render, stats
from polyhunter.desk import desk_stats
from polyhunter.i18n import tr
from polyhunter.paper import PaperError

router = Router()
NOPREVIEW = LinkPreviewOptions(is_disabled=True)
BUY_SIZES = (10, 50, 100)


class Ctx:
    store = paper = trader = client = newstrader = None
    ulang = None
    desk_db = None


ctx = Ctx()


def kb(rows):
    return InlineKeyboardMarkup(inline_keyboard=rows)


def owner(chat_id):
    return f"u:{chat_id}"


def q(payload):
    return f"q:{ctx.store.put_quick(payload)}"


def buy_rows(market, lang):
    """Кнопки «Купить <исход> $10/$50/$100» для каждого исхода рынка."""
    outcomes = api._jl(market.get("outcomes"))
    tokens = api._jl(market.get("clobTokenIds"))
    rows = []
    for name, tok in list(zip(outcomes, tokens))[:3]:
        mk = dict(asset=tok, condition_id=market.get("conditionId", ""), outcome=name,
                  title=market.get("question", ""), slug=market.get("slug", ""),
                  event_slug=((market.get("events") or [{}])[0] or {}).get("slug", ""))
        rows.append([InlineKeyboardButton(text=tr(lang, "btn.buy", outcome=name[:14], usd=f"${u}"),
                                          callback_data=q(dict(a="buy", mk=mk, usd=u, fee=api.fee_rate(market))))
                     for u in BUY_SIZES])
    return rows


async def marks_for(positions):
    assets = [p["asset"] for p in positions]
    return await ctx.client.midpoints(assets) if assets else {}


# ------------------------------------------------------------------ счёт
@router.message(Command("paper", "portfolio"))
async def cmd_paper(m: Message):
    await send_paper(m.chat.id, ctx.ulang(m), m.bot)


async def send_paper(chat_id, lang, bot):
    acc = ctx.paper.account(owner(chat_id))
    pos = ctx.paper.positions(owner(chat_id))
    marks = await marks_for(pos)
    rows = []
    for i, p in enumerate(pos[:8], 1):
        rows.append([InlineKeyboardButton(text=tr(lang, "btn.sell_half", i=i), callback_data=q(dict(a="sell", asset=p["asset"], frac=0.5))),
                     InlineKeyboardButton(text=tr(lang, "btn.sell_all", i=i), callback_data=q(dict(a="sell", asset=p["asset"], frac=1.0)))])
    await bot.send_message(chat_id, render.paper_card(acc, pos, marks, lang), reply_markup=kb(rows) if rows else None,
                           link_preview_options=NOPREVIEW)


@router.callback_query(F.data == "paper")
async def cb_paper(c: CallbackQuery):
    await c.answer()
    await send_paper(c.message.chat.id, ctx.ulang(c), c.bot)


@router.callback_query(F.data.startswith("q:"))
async def cb_quick(c: CallbackQuery):
    lang = ctx.ulang(c)
    chat_id = c.message.chat.id
    p = ctx.store.get_quick(c.data[2:])
    if not p:
        await c.answer()
        return
    a = p.get("a")
    try:
        if a == "buy":
            _bids, asks = await ctx.client.book(p["mk"]["asset"])
            r = ctx.paper.buy(owner(chat_id), p["mk"], asks, p["usd"], source="manual", fee_rate=p.get("fee", 0))
            text = tr(lang, "buy.ok", outcome=render.esc(p["mk"]["outcome"]), shares=f"{r['shares']:,.1f}",
                      price=render.price(r["price"]), usd=render.money(r["usd"]))
            text += tr(lang, "buy.partial") if r["partial"] else ""
            await c.answer()
            await c.message.answer(text, reply_markup=kb([[InlineKeyboardButton(text="💼", callback_data="paper")]]))
        elif a == "sell":
            bids, _asks = await ctx.client.book(p["asset"])
            r = ctx.paper.sell(owner(chat_id), p["asset"], bids, p["frac"])
            await c.answer()
            await c.message.answer(tr(lang, "sell.ok", shares=f"{r['shares']:,.1f}", price=render.price(r["price"]),
                                      pnl=render.signed_money(r["pnl"])))
        elif a == "reset":
            ctx.paper.reset(owner(chat_id))
            await c.answer()
            await c.message.edit_text(tr(lang, "reset.ok"))
        elif a == "copy":
            ctx.store.set_copy(chat_id, p["leader"], p["usd"])
            await c.answer(tr(lang, "copy.ai", usd=render.money(p["usd"])).replace("<b>", "").replace("</b>", "")[:190])
        elif a == "uncopy":
            ctx.store.remove_copy(chat_id, p["leader"])
            await c.answer(tr(lang, "copy.off", who=p["leader"]))
        else:
            await c.answer()
    except PaperError as e:
        await c.answer(tr(lang, "err." + str(e)).replace("<b>", "").replace("</b>", "")[:190], show_alert=True)
    except TelegramAPIError:
        pass


@router.message(Command("reset"))
async def cmd_reset(m: Message):
    lang = ctx.ulang(m)
    await m.answer(tr(lang, "reset.ask"), reply_markup=kb([[
        InlineKeyboardButton(text=tr(lang, "btn.reset_yes"), callback_data=q(dict(a="reset"))),
        InlineKeyboardButton(text=tr(lang, "btn.cancel"), callback_data=q(dict(a="noop")))]]))


# ------------------------------------------------------------------ копирование
@router.message(Command("copy"))
async def cmd_copy(m: Message, command: CommandObject):
    lang = ctx.ulang(m)
    args = (command.args or "").split()
    if not args:
        await m.answer(tr(lang, "copy.bad"))
        return
    try:
        usd = float(args[1].replace("$", "")) if len(args) > 1 else 20.0
        assert 1 <= usd <= 500
    except (ValueError, AssertionError):
        await m.answer(tr(lang, "copy.bad"))
        return
    if args[0].lower() in ("ai", "news"):
        ctx.store.set_copy(m.chat.id, args[0].lower(), usd)
        await m.answer(tr(lang, "copy." + args[0].lower(), usd=render.money(usd)))
        return
    w = ctx.store.find_wallet(args[0])
    if not w:
        await m.answer(tr(lang, "copy.bad"))
        return
    ctx.store.set_copy(m.chat.id, w, usd)
    await m.answer(tr(lang, "copy.ok", who=render.who(ctx.store.score(w) or {"wallet": w}), usd=render.money(usd)))


@router.message(Command("copies"))
async def cmd_copies(m: Message):
    lang = ctx.ulang(m)
    cs = ctx.store.copies_of(m.chat.id)
    if not cs:
        await m.answer(tr(lang, "copy.none"))
        return
    lines, rows = [tr(lang, "copy.list"), ""], []
    for leader, usd in cs:
        who = {"ai": "🤖 AI", "news": "📰 News"}.get(leader) or render.who(ctx.store.score(leader) or {"wallet": leader})
        lines.append(f"• {who} · {render.money(usd)}")
        rows.append([InlineKeyboardButton(text=tr(lang, "btn.uncopy", who="AI" if leader == "ai" else render.short(leader)),
                                          callback_data=q(dict(a="uncopy", leader=leader)))])
    await m.answer("\n".join(lines), reply_markup=kb(rows))


@router.message(Command("uncopy"))
async def cmd_uncopy(m: Message, command: CommandObject):
    lang = ctx.ulang(m)
    arg = (command.args or "").strip()
    leader = arg.lower() if arg.lower() in ("ai", "news") else ctx.store.find_wallet(arg)
    if not leader:
        await m.answer(tr(lang, "copy.bad"))
        return
    ctx.store.remove_copy(m.chat.id, leader)
    await m.answer(tr(lang, "copy.off", who="AI" if leader == "ai" else render.short(leader)))


# ------------------------------------------------------------------ модель, polydesk, лидеры
@router.message(Command("ai"))
async def cmd_ai(m: Message):
    await send_ai(m.chat.id, ctx.ulang(m), m.bot)


@router.callback_query(F.data == "ai")
async def cb_ai(c: CallbackQuery):
    await c.answer()
    await send_ai(c.message.chat.id, ctx.ulang(c), c.bot)


async def send_ai(chat_id, lang, bot):
    rep = (ctx.trader.predictor.report if ctx.trader and ctx.trader.predictor else None)
    pos = ctx.paper.positions("ai")
    marks = await marks_for(pos)
    text = render.ai_card(rep, ctx.paper.account("ai"), pos, marks, ctx.paper.trades("ai", 5), lang)
    text += "\n" + render.live_line(stats.live_record(stats.settled_returns(ctx.paper.trades("ai", 100000)), 0.075), lang)
    on = ctx.store.user(chat_id)["alerts"].get("ai")
    rows = [[InlineKeyboardButton(text=tr(lang, "btn.copy_ai"), callback_data=q(dict(a="copy", leader="ai", usd=20))),
             InlineKeyboardButton(text=("✅ " if on else "⬜ ") + tr(lang, "btn.ai_alerts"), callback_data="al:ai")]]
    await bot.send_message(chat_id, text, reply_markup=kb(rows), link_preview_options=NOPREVIEW)


@router.message(Command("desk"))
async def cmd_desk(m: Message):
    d = desk_stats(ctx.desk_db)
    text = render.desk_card(d, ctx.ulang(m))
    if d:
        text += "\n" + render.live_line(stats.live_record(d.get("returns", []), 0.10), ctx.ulang(m))
    await m.answer(text)


@router.message(Command("leaders"))
async def cmd_leaders(m: Message):
    lang = ctx.ulang(m)
    rows = ctx.paper.leaderboard({}, limit=10, prefix="u:")
    ai_acc = ctx.paper.account("ai")
    ai_eq = ctx.paper.equity("ai", {})
    rows.append(("ai", ai_eq, ai_eq - ai_acc["start"]))
    n_eq = ctx.paper.equity("news", {})
    rows.append(("news", n_eq, n_eq - ctx.paper.account("news")["start"]))
    d = desk_stats(ctx.desk_db)
    if d:
        rows.append(("desk", d["equity"], d["equity"] - d["start"]))
    rows.sort(key=lambda r: -r[2])
    names = {owner(m.chat.id): "⭐ " + ("Вы" if lang == "ru" else "You")}
    await m.answer(render.leaders(rows, names, lang))


@router.message(Command("news"))
async def cmd_news(m: Message):
    await send_news(m.chat.id, ctx.ulang(m), m.bot)


@router.callback_query(F.data == "news")
async def cb_news(c: CallbackQuery):
    await c.answer()
    await send_news(c.message.chat.id, ctx.ulang(c), c.bot)


async def send_news(chat_id, lang, bot):
    nt = ctx.newstrader
    cfg = dict(brain.config(), ready=brain.ready())
    pos = ctx.paper.positions("news")
    marks = await marks_for(pos)
    text = render.news_card(cfg, nt.forecasts(6) if nt else [], ctx.paper.account("news"), pos, marks,
                            nt.track_record() if nt else dict(n=0), lang)
    text += "\n" + render.live_line(stats.live_record(stats.settled_returns(ctx.paper.trades("news", 100000)), 0.08), lang)
    on = ctx.store.user(chat_id)["alerts"].get("news")
    rows = [[InlineKeyboardButton(text=tr(lang, "btn.copy_news"), callback_data=q(dict(a="copy", leader="news", usd=20))),
             InlineKeyboardButton(text=("✅ " if on else "⬜ ") + tr(lang, "alerts.news"), callback_data="al:news")]]
    await bot.send_message(chat_id, text, reply_markup=kb(rows), link_preview_options=NOPREVIEW)
