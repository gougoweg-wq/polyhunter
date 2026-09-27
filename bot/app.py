"""Polyhunter — Telegram-бот: рейтинг умных денег Polymarket и радар крупных ставок.

Запуск: .venv/bin/python -m bot.app  (токен в .env: BOT_TOKEN=...)
"""
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import (BotCommand, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,
                           LinkPreviewOptions, Message)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import hunter  # noqa: E402  сбор позиций кошелька (синхронный)
from polyhunter import api, pipeline, render  # noqa: E402
from polyhunter.engine import RadarEngine  # noqa: E402
from polyhunter.radar import trade_key  # noqa: E402
from polyhunter.model import FADE_FILE, Predictor  # noqa: E402
from polyhunter.paper import Paper  # noqa: E402
from polyhunter.trader import Trader  # noqa: E402
from bot import trading  # noqa: E402
from polyhunter.i18n import lang_of, tr  # noqa: E402
from polyhunter.store import ALERT_TYPES, Store  # noqa: E402

DATA = ROOT / "data"
HUNTER_DB = DATA / "hunter.db"
RADAR_EVERY = 30
RESCORE_EVERY = 3 * 3600
log = logging.getLogger("polyhunter")


def load_env():
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


load_env()
store = Store(DATA / "bot.db")
client = api.Client()
paper = Paper(store)
predictor = Predictor(DATA / FADE_FILE) if (DATA / FADE_FILE).exists() else None
trader = Trader(store, paper, client, predictor, min_signal_usd=2000)
POLYDESK_DB = Path.home() / "polydesk" / "data" / "polydesk.db"
dp = Dispatcher()
NOPREVIEW = LinkPreviewOptions(is_disabled=True)
_facts = {"at": 0, "v": None}


# ------------------------------------------------------------------ помощники
def ulang(obj):
    u = obj.from_user
    return store.user(obj.chat.id if isinstance(obj, Message) else obj.message.chat.id,
                      lang_of(u.language_code if u else None))["lang"]


def kb(rows):
    return InlineKeyboardMarkup(inline_keyboard=rows)


def top_kb(lang):
    return kb([[InlineKeyboardButton(text=tr(lang, "btn.top_news"), callback_data="top:news"),
                InlineKeyboardButton(text=tr(lang, "btn.top_sports"), callback_data="top:sports")],
               [InlineKeyboardButton(text=tr(lang, "btn.top_crypto"), callback_data="top:crypto"),
                InlineKeyboardButton(text=tr(lang, "btn.top_all"), callback_data="top:all")]])


def start_kb(lang):
    k = top_kb(lang)
    k.inline_keyboard.append([InlineKeyboardButton(text="💼 " + ("Счёт" if lang == "ru" else "Account"), callback_data="paper"),
                              InlineKeyboardButton(text="🤖 " + ("Модель" if lang == "ru" else "Model"), callback_data="ai")])
    k.inline_keyboard.append([InlineKeyboardButton(text=tr(lang, "btn.radar"), callback_data="radar"),
                              InlineKeyboardButton(text=tr(lang, "btn.alerts"), callback_data="alerts")])
    return k


def wallet_kb(lang, chat_id, wallet):
    followed = wallet in store.following(chat_id)
    return kb([[InlineKeyboardButton(text=tr(lang, "btn.unfollow" if followed else "btn.follow"),
                                     callback_data=("uf:" if followed else "fw:") + wallet),
                InlineKeyboardButton(text=tr(lang, "btn.profile"), url=render.profile_url(wallet))]])


def alerts_kb(lang, chat_id):
    u = store.user(chat_id)
    rows = [[InlineKeyboardButton(text=("✅ " if u["alerts"].get(k) else "⬜ ") + tr(lang, "alerts." + k),
                                  callback_data="al:" + k)] for k in ALERT_TYPES]
    return kb(rows)


def signal_kb(lang, sig):
    t = sig.get("trade") or sig.get("cluster")
    row = [InlineKeyboardButton(text=tr(lang, "btn.market"), url=render.market_url(t))]
    if sig.get("trade"):
        row.append(InlineKeyboardButton(text=tr(lang, "btn.follow"), callback_data="fw:" + sig["trade"]["wallet"]))
    return kb([row])


def render_signal(sig, lang):
    if sig["kind"] == "cluster":
        return render.cluster_alert(sig["cluster"], lang)
    return render.alert(sig["kind"], sig["trade"], sig.get("score"), lang, history_n=sig.get("history_n"))


async def wallet_score(query):
    """Кошелёк из базы или посчитанный с нуля по открытому API."""
    w = store.find_wallet(query)
    if w and store.score(w):
        return store.score(w)
    if not (query or "").lower().startswith("0x") or len(query) != 42:
        return None
    w = query.lower()
    _, rows = await asyncio.to_thread(hunter.fetch_wallet, w, 40)
    prow = [(w, r[3], r[4], r[5], int(r[6]), r[7], r[8], r[9]) for r in rows if r[6] in (0, 1)]
    names = {}
    s = pipeline.score_single(prow, name=names.get(w, ""), tau2=store.meta("tau2:all", 0.01))
    if s:
        store.upsert_score("all", s)
    return s if s else {"wallet": w, "nodata": True}


# ------------------------------------------------------------------ команды
@dp.message(CommandStart())
async def cmd_start(m: Message):
    lang = ulang(m)
    await m.answer(tr(lang, "start"), reply_markup=start_kb(lang), link_preview_options=NOPREVIEW)


@dp.message(Command("help"))
async def cmd_help(m: Message):
    await m.answer(tr(ulang(m), "help"))


@dp.message(Command("about"))
async def cmd_about(m: Message):
    await m.answer(tr(ulang(m), "about"), link_preview_options=NOPREVIEW)


@dp.message(Command("top"))
async def cmd_top(m: Message, command: CommandObject):
    lang = ulang(m)
    cat = (command.args or "news").strip().lower()
    cat = cat if cat in pipeline.CATS else "news"
    await m.answer(render.top_list(store.top(cat, 10), cat, lang), reply_markup=top_kb(lang),
                   link_preview_options=NOPREVIEW)


@dp.callback_query(F.data.startswith("top:"))
async def cb_top(c: CallbackQuery):
    lang = ulang(c)
    cat = c.data.split(":", 1)[1]
    text = render.top_list(store.top(cat, 10), cat, lang)
    await c.answer()
    if (c.message.text or "").startswith("🏆"):     # переключаем категорию в том же сообщении
        try:
            await c.message.edit_text(text, reply_markup=top_kb(lang), link_preview_options=NOPREVIEW)
        except TelegramAPIError:
            pass
    else:                                            # из стартового меню — новым сообщением, меню остаётся
        await c.message.answer(text, reply_markup=top_kb(lang), link_preview_options=NOPREVIEW)


@dp.message(Command("wallet"))
async def cmd_wallet(m: Message, command: CommandObject):
    lang = ulang(m)
    q = (command.args or "").strip()
    if not q:
        await m.answer(tr(lang, "follow.bad"))
        return
    wait = None
    if q.lower().startswith("0x") and len(q) == 42 and not store.score(q.lower()):
        wait = await m.answer(tr(lang, "wallet.computing"))
    try:
        s = await wallet_score(q)
    except Exception:
        log.exception("wallet")
        s = None
    if wait:
        await wait.delete()
    if not s:
        await m.answer(tr(lang, "wallet.notfound"))
    elif s.get("nodata"):
        await m.answer(tr(lang, "wallet.nodata"), reply_markup=wallet_kb(lang, m.chat.id, s["wallet"]))
    else:
        await m.answer(render.wallet_card(s, lang), reply_markup=wallet_kb(lang, m.chat.id, s["wallet"]),
                       link_preview_options=NOPREVIEW)


@dp.message(Command("follow"))
async def cmd_follow(m: Message, command: CommandObject):
    lang = ulang(m)
    w = store.find_wallet((command.args or "").strip())
    if not w:
        await m.answer(tr(lang, "follow.bad"))
        return
    store.follow(m.chat.id, w)
    s = store.score(w) or {"wallet": w}
    await m.answer(tr(lang, "follow.ok", who=render.who(s), usd=render.money(store.user(m.chat.id)["threshold"])))


@dp.message(Command("unfollow"))
async def cmd_unfollow(m: Message, command: CommandObject):
    lang = ulang(m)
    w = store.find_wallet((command.args or "").strip())
    if not w:
        await m.answer(tr(lang, "follow.bad"))
        return
    store.unfollow(m.chat.id, w)
    await m.answer(tr(lang, "unfollow.ok", who=render.who(store.score(w) or {"wallet": w})))


@dp.callback_query(F.data.startswith(("fw:", "uf:")))
async def cb_follow(c: CallbackQuery):
    lang = ulang(c)
    chat_id = c.message.chat.id
    action, w = c.data.split(":", 1)
    if action == "fw":
        store.follow(chat_id, w)
        note = tr(lang, "follow.ok", who=render.short(w), usd=render.money(store.user(chat_id)["threshold"]))
    else:
        store.unfollow(chat_id, w)
        note = tr(lang, "unfollow.ok", who=render.short(w))
    await c.answer(note.replace("<b>", "").replace("</b>", ""))
    # на карточке кошелька кнопка переключается между «Следить» и «Не следить»
    rows = c.message.reply_markup.inline_keyboard if c.message.reply_markup else []
    is_card = any(b.url and "/profile/" in b.url for row in rows for b in row)
    if is_card:
        try:
            await c.message.edit_reply_markup(reply_markup=wallet_kb(lang, chat_id, w))
        except TelegramAPIError:
            pass


@dp.message(Command("following"))
async def cmd_following(m: Message):
    lang = ulang(m)
    ws = store.following(m.chat.id)
    if not ws:
        await m.answer(tr(lang, "following.empty"))
        return
    lines = [tr(lang, "following.title"), ""]
    for w in ws:
        s = store.score(w)
        if s:
            lines.append(f"{render.TIER_ICON.get(s['tier'], '')}<b>{s['tier']}</b> {s['score']} · {render.who(s)} · "
                         f"ROI {render.pct(s['roi'])} · <code>{w}</code>")
        else:
            lines.append(f"❔ <code>{w}</code>")
    await m.answer("\n".join(lines), link_preview_options=NOPREVIEW)


@dp.message(Command("radar"))
async def cmd_radar(m: Message):
    await send_radar(m.chat.id, ulang(m), m.bot)


@dp.callback_query(F.data == "radar")
async def cb_radar(c: CallbackQuery):
    await c.answer()
    await send_radar(c.message.chat.id, ulang(c), c.bot)


async def send_radar(chat_id, lang, bot):
    sigs = store.recent_signals(6)
    if not sigs:
        await bot.send_message(chat_id, tr(lang, "radar.empty"))
        return
    await bot.send_message(chat_id, tr(lang, "radar.title"))
    for s in reversed(sigs):
        try:
            sig = json.loads(s["text"])
            await bot.send_message(chat_id, render_signal(sig, lang), link_preview_options=NOPREVIEW,
                                   reply_markup=signal_kb(lang, sig))
        except (ValueError, KeyError, TelegramAPIError):
            continue


@dp.message(Command("alerts"))
async def cmd_alerts(m: Message):
    lang = ulang(m)
    await m.answer(tr(lang, "alerts.title"), reply_markup=alerts_kb(lang, m.chat.id))


@dp.callback_query(F.data == "alerts")
async def cb_alerts_open(c: CallbackQuery):
    lang = ulang(c)
    await c.answer()
    await c.message.answer(tr(lang, "alerts.title"), reply_markup=alerts_kb(lang, c.message.chat.id))


@dp.callback_query(F.data.startswith("al:"))
async def cb_alert_toggle(c: CallbackQuery):
    lang = ulang(c)
    kind = c.data.split(":", 1)[1]
    if kind in ALERT_TYPES:
        store.toggle_alert(c.message.chat.id, kind)
    try:
        await c.message.edit_reply_markup(reply_markup=alerts_kb(lang, c.message.chat.id))
    except TelegramAPIError:
        pass
    await c.answer()


@dp.message(Command("threshold"))
async def cmd_threshold(m: Message, command: CommandObject):
    lang = ulang(m)
    try:
        usd = float((command.args or "").replace("$", "").replace(",", "").replace(" ", ""))
        assert 100 <= usd <= 10_000_000
    except (ValueError, AssertionError):
        await m.answer(tr(lang, "threshold.bad"))
        return
    store.set_threshold(m.chat.id, usd)
    await m.answer(tr(lang, "threshold.ok", usd=render.money(usd)))


@dp.message(Command("market"))
async def cmd_market(m: Message, command: CommandObject):
    lang = ulang(m)
    ev_slug, mk_slug = api.parse_link(command.args or "")
    if not ev_slug and not mk_slug:
        await m.answer(tr(lang, "market.bad"))
        return
    try:
        market, url = None, None
        if ev_slug:
            ev = await client.event(ev_slug)
            market = api.pick_market(ev, mk_slug) if ev else None
            url = f"{render.PM}/event/{ev_slug}"
        if not market and mk_slug:
            market = await client.market_by_slug(mk_slug)
            url = f"{render.PM}/market/{mk_slug}"
        if not market:
            await m.answer(tr(lang, "market.notfound"))
            return
        holders = await client.holders(market["conditionId"])
        sm = api.smart_money(market, holders, store.scores_map("all"))
        await m.answer(render.market_card(market.get("question") or "", url, sm, lang)
                       + "\n\n<i>" + tr(lang, "market.buy_hint") + "</i>",
                       link_preview_options=NOPREVIEW,
                       reply_markup=kb([[InlineKeyboardButton(text=tr(lang, "btn.market"), url=url)]]
                                       + trading.buy_rows(market, lang)))
    except Exception:
        log.exception("market")
        await m.answer(tr(lang, "err"))


@dp.message(Command("stats"))
async def cmd_stats(m: Message):
    lang = ulang(m)
    if time.time() - _facts["at"] > 3600 or not _facts["v"]:
        _facts["v"] = await asyncio.to_thread(pipeline.market_facts, HUNTER_DB)
        _facts["at"] = time.time()
    f = _facts["v"]
    tc = store.tier_counts("all")
    await m.answer(tr(lang, "stats", wallets=f["wallets"], bets=f"{f['bets']:,}", wr=f"{f['wr']:.1%}",
                      er=f"{f['er']:.1%}", lw=f"{f['lw']:.1%}", le=f"{f['le']:.1%}",
                      s=tc.get("S", 0), a=tc.get("A", 0), f=tc.get("F", 0)))


@dp.message(F.text.regexp(r"polymarket\.com/(event|market)/", mode="search"))
async def link_shortcut(m: Message):
    """Просто прислали ссылку — показываем умные деньги в рынке."""
    await cmd_market(m, CommandObject(prefix="/", command="market", args=m.text))


@dp.message(F.text.regexp(r"^0x[0-9a-fA-F]{40}$"))
async def addr_shortcut(m: Message):
    await cmd_wallet(m, CommandObject(prefix="/", command="wallet", args=m.text.strip()))


# ------------------------------------------------------------------ фоновые циклы
async def radar_loop(bot: Bot):
    async def hist(wallet, cond):
        try:
            return await client.history_markets(wallet, exclude_condition=cond)
        except Exception:
            return 99   # не знаем — не считаем новым
    eng = RadarEngine(store, hist)
    first = True
    while True:
        try:
            trades = await client.trades(min_usd=1000, limit=500)
            if first:  # на старте не засыпаем пользователей старыми сделками
                for t in trades:
                    store.mark_seen(trade_key(t))
                first = False
            else:
                eng.refresh()
                for sig in await eng.step(trades):
                    await broadcast(bot, sig)
                await notify_events(bot, await trader.on_trades(trades))
            store.prune_seen()
        except Exception:
            log.exception("radar")
        await asyncio.sleep(RADAR_EVERY)


async def notify_events(bot, events):
    """Сделки модели, копирования и расчёты — тем, кого они касаются."""
    for e in events:
        if e["kind"] == "ai_buy":
            to = [u["chat_id"] for u in store.users() if u["alerts"].get("ai")]
        elif e["kind"] in ("copy_buy", "copy_sell", "copy_fail"):
            to = [e["chat"]]
        elif e["kind"] == "settle" and str(e["owner"]).startswith("u:"):
            to = [int(e["owner"][2:])]
        else:
            to = []
        for chat_id in to:
            lang = store.user(chat_id)["lang"]
            try:
                await bot.send_message(chat_id, render.paper_event(e, lang), link_preview_options=NOPREVIEW)
            except TelegramAPIError as err:
                log.warning("notify %s: %s", chat_id, err)
            await asyncio.sleep(0.05)


async def loop_every(seconds, fn, bot, name):
    while True:
        try:
            await notify_events(bot, await fn())
        except Exception:
            log.exception(name)
        await asyncio.sleep(seconds)


async def broadcast(bot, sig):
    for chat_id in sig["to"]:
        lang = store.user(chat_id)["lang"]
        try:
            await bot.send_message(chat_id, render_signal(sig, lang), link_preview_options=NOPREVIEW,
                                   reply_markup=signal_kb(lang, sig))
        except TelegramAPIError as e:
            log.warning("send %s: %s", chat_id, e)
        await asyncio.sleep(0.05)


async def rescore_loop():
    py = sys.executable
    while True:
        try:
            if not store.meta("tau2:all"):
                await asyncio.to_thread(pipeline.rescore, HUNTER_DB, store, DATA)
            await asyncio.sleep(RESCORE_EVERY)
            for args in (["trades", "--min-usd", "2000"], ["positions", "--min-usd", "2000", "--max-wallets", "150"]):
                p = await asyncio.create_subprocess_exec(py, str(ROOT / "hunter.py"), *args, cwd=str(ROOT),
                                                         stdout=asyncio.subprocess.DEVNULL,
                                                         stderr=asyncio.subprocess.DEVNULL)
                await p.wait()
            summary = await asyncio.to_thread(pipeline.rescore, HUNTER_DB, store, DATA)
            log.info("rescore %s", summary)
        except Exception:
            log.exception("rescore")
            await asyncio.sleep(600)


async def setup_profile(bot: Bot):
    """Команды и описания для RU и EN — Telegram показывает их по языку пользователя."""
    cmds = {
        "ru": [("top", "Рейтинг умных денег"), ("wallet", "Разбор кошелька"), ("market", "Умные деньги в рынке"),
               ("radar", "Последние сигналы"), ("follow", "Следить за кошельком"), ("following", "Мой список"),
               ("alerts", "Какие сигналы присылать"), ("threshold", "Минимальная ставка для сигнала"),
               ("paper", "Мой тестовый счёт"), ("ai", "Модель «против китов»"), ("copy", "Копировать модель или кошелёк"),
               ("copies", "Кого я копирую"), ("leaders", "Лидеры бумажной торговли"), ("desk", "Бот polydesk"),
               ("reset", "Сбросить тестовый счёт"),
               ("stats", "Что показывают данные"), ("about", "Как считается рейтинг"), ("help", "Все команды")],
        "en": [("top", "Smart money leaderboard"), ("wallet", "Wallet breakdown"), ("market", "Smart money in a market"),
               ("radar", "Latest signals"), ("follow", "Track a wallet"), ("following", "My list"),
               ("alerts", "Choose signals"), ("threshold", "Minimum bet size"),
               ("paper", "My test account"), ("ai", "Fade-the-whales model"), ("copy", "Copy the model or a wallet"),
               ("copies", "Who I copy"), ("leaders", "Paper trading leaders"), ("desk", "polydesk bot"),
               ("reset", "Reset test account"),
               ("stats", "What the data shows"), ("about", "How the score works"), ("help", "All commands")],
    }
    desc = {
        "ru": ("Polyhunter находит на Polymarket кошельки, которые выигрывают чаще, чем обещают цены, "
               "и присылает их крупные ставки в реальном времени.\n\n"
               "🏆 Рейтинг умных денег по новостям, спорту и крипте\n"
               "🐋 Свежие киты: новый кошелёк сразу ставит крупно на аутсайдера\n"
               "🌊 Потоки денег: несколько кошельков в одну сторону за минуты\n"
               "📍 Кто крупно ставит на любой рынок — пришлите ссылку\n\n"
               "Статистика на открытых данных, не финансовый совет."),
        "en": ("Polyhunter finds Polymarket wallets that win more often than the prices imply "
               "and sends their big bets in real time.\n\n"
               "🏆 Smart money leaderboard for news, sports and crypto\n"
               "🐋 Fresh whales: new wallets going big on underdogs\n"
               "🌊 Money flows: several wallets piling in within minutes\n"
               "📍 Who bets big on any market — just send a link\n\n"
               "Open-data statistics, not financial advice."),
    }
    short = {"ru": "Умные деньги Polymarket: рейтинг кошельков и радар крупных ставок в реальном времени.",
             "en": "Polymarket smart money: wallet leaderboard and a real-time radar of big bets."}
    for lang in ("ru", "en"):
        await bot.set_my_commands([BotCommand(command=c, description=d) for c, d in cmds[lang]], language_code=lang)
        await bot.set_my_description(desc[lang], language_code=lang)
        await bot.set_my_short_description(short[lang], language_code=lang)
    await bot.set_my_commands([BotCommand(command=c, description=d) for c, d in cmds["en"]])
    await bot.set_my_description(desc["en"])
    await bot.set_my_short_description(short["en"])


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    token = os.environ.get("BOT_TOKEN")
    if not token:
        sys.exit("BOT_TOKEN не задан: добавьте его в .env")
    bot = Bot(token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    try:
        await setup_profile(bot)
    except TelegramAPIError as e:
        log.warning("profile: %s", e)
    asyncio.create_task(radar_loop(bot))
    asyncio.create_task(loop_every(60, trader.copy_step, bot, "copy"))
    asyncio.create_task(loop_every(300, trader.settle_step, bot, "settle"))
    asyncio.create_task(rescore_loop())
    await dp.start_polling(bot)


trading.ctx.store, trading.ctx.paper, trading.ctx.trader, trading.ctx.client = store, paper, trader, client
trading.ctx.ulang, trading.ctx.desk_db = ulang, POLYDESK_DB
dp.include_router(trading.router)


if __name__ == "__main__":
    asyncio.run(main())
