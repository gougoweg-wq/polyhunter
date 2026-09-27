"""Сквозной прогон бумажной торговли через диспетчер aiogram с поддельными сессией и API."""
import asyncio
from datetime import datetime

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.types import CallbackQuery, Chat, Message, Update, User

import bot.app as app
from polyhunter.paper import Paper
from polyhunter.store import Store
from tests.test_bot_smoke import FakeSession

MARKET = {"markets": [{"slug": "m", "question": "Germany vs. Greece", "conditionId": "C", "volume": "10", "closed": False,
                       "outcomes": '["Germany", "Greece"]', "outcomePrices": '["0.8", "0.2"]',
                       "clobTokenIds": '["t1", "t2"]', "feeSchedule": {}}]}


class FakeClient:
    async def event(self, slug):
        return MARKET

    async def holders(self, cond):
        return []

    async def book(self, token):
        return [(0.79, 5000)], [(0.80, 5000)]

    async def midpoints(self, tokens):
        return {t: 0.85 for t in tokens}


def test_paper_trading_flow(tmp_path, monkeypatch):
    st = Store(tmp_path / "s.db")
    paper = Paper(st)
    for mod, attr, val in ((app, "store", st), (app.trading.ctx, "store", st), (app.trading.ctx, "paper", paper),
                           (app.trading.ctx, "client", FakeClient()), (app, "client", FakeClient())):
        monkeypatch.setattr(mod, attr, val)
    monkeypatch.setattr(app.trading.ctx, "desk_db", tmp_path / "none.db")
    session = FakeSession()
    bot = Bot("123456:TEST", session=session, default=DefaultBotProperties(parse_mode="HTML"))
    user = User(id=5, is_bot=False, first_name="T", language_code="ru")
    chat = Chat(id=5, type="private")
    n = [0]

    async def say(text):
        n[0] += 1
        k = len(session.sent)
        await app.dp.feed_update(bot, Update(update_id=n[0], message=Message(
            message_id=n[0], date=datetime.now(), chat=chat, from_user=user, text=text)))
        return session.sent[k:]

    async def press(data):
        n[0] += 1
        k = len(session.sent)
        msg = Message(message_id=n[0], date=datetime.now(), chat=chat, from_user=user, text="x")
        await app.dp.feed_update(bot, Update(update_id=n[0], callback_query=CallbackQuery(
            id=str(n[0]), from_user=user, chat_instance="c", message=msg, data=data)))
        return session.sent[k:]

    def btn(msg, needle):
        return next(b.callback_data for row in msg.reply_markup.inline_keyboard for b in row if needle in b.text)

    async def flow():
        card = (await say("https://polymarket.com/event/ger-grc"))[-1]
        out = await press(btn(card, "$50"))                                  # купить Germany на $50
        assert "Куплено" in out[-1].text and "0.80" in out[-1].text
        assert paper.account("u:5")["cash"] == 950
        acc = (await say("/paper"))[-1]
        assert "Germany vs. Greece" in acc.text and "0.85" in acc.text and "+$3" in acc.text   # 62.5 акц × 0.85 − 50
        out = await press(btn(acc, "½"))
        assert "Продано" in out[-1].text and paper.positions("u:5")[0]["shares"] == 31.25
        assert "Копирую модель" in (await say("/copy ai 15"))[-1].text and st.copies_of(5) == [("ai", 15.0)]
        ai = (await say("/ai"))[-1]
        assert "Модель" in ai.text and "Живой счёт" in ai.text
        assert "Лидеры" in (await say("/leaders"))[-1].text
        assert "polydesk" in (await say("/desk"))[-1].text
        ask = (await say("/reset"))[-1]
        await press(btn(ask, "Да"))
        assert paper.account("u:5")["cash"] == 1000 and paper.positions("u:5") == []

    asyncio.run(flow())
