"""Прогон команд через настоящий диспетчер aiogram с поддельной сессией: без сети и без Telegram."""
import asyncio
from datetime import datetime

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.base import BaseSession
from aiogram.methods import SendMessage
from aiogram.types import Chat, Message, Update, User

import bot.app as app
from polyhunter.store import Store

W = "0x23d81ba9371e576015c1e562db09c689f56b0288"


class FakeSession(BaseSession):
    def __init__(self):
        super().__init__()
        self.sent = []

    async def make_request(self, bot, method, timeout=None):
        if isinstance(method, SendMessage):
            self.sent.append(method)
            return Message(message_id=len(self.sent), date=datetime.now(),
                           chat=Chat(id=method.chat_id, type="private"), text=method.text)
        return True

    async def stream_content(self, url, headers=None, timeout=30, chunk_size=65536, raise_for_status=True):
        yield b""

    async def close(self):
        pass


def test_commands_end_to_end(tmp_path, monkeypatch):
    st = Store(tmp_path / "b.db")
    st.save_scores("news", [dict(wallet=W, name="flawfence", tier="S", score=85, post_edge=.09, edge=.1, q=.01,
                                 n=163, events=107, wins=92, exp=74.4, roi=.26, pnl=154178, stake=590000,
                                 best_category="news", timing6h=.054)])
    st.save_scores("all", [dict(wallet=W, name="flawfence", tier="S", score=85, post_edge=.09, edge=.1, q=.01,
                                n=163, events=107, wins=92, exp=74.4, roi=.26, pnl=154178, stake=590000,
                                best_category="news", timing6h=.054)])
    monkeypatch.setattr(app, "store", st)
    monkeypatch.setattr(app, "_facts", {"at": 9e18, "v": dict(wallets=10, bets=100, wr=.48, er=.53, lw=.06, le=.11)})
    session = FakeSession()
    bot = Bot("123456:TEST", session=session, default=DefaultBotProperties(parse_mode="HTML"))
    user = User(id=77, is_bot=False, first_name="T", language_code="ru")

    async def say(i, text):
        n = len(session.sent)
        upd = Update(update_id=i, message=Message(message_id=i, date=datetime.now(), text=text, from_user=user,
                                                  chat=Chat(id=77, type="private")))
        await app.dp.feed_update(bot, upd)
        return [m.text for m in session.sent[n:]]

    async def run():
        out = {}
        for i, cmd in enumerate(["/start", "/help", "/about", "/top news", "/wallet flawfence", "/follow flawfence",
                                 "/following", "/threshold 2500", "/threshold abc", "/alerts", "/radar", "/stats",
                                 "/market hello", W], 1):
            out[cmd] = await say(i, cmd)
        return out

    out = asyncio.run(run())
    assert "Polyhunter" in out["/start"][0]
    assert "/top" in out["/help"][0] and "Бенджамини" in out["/about"][0]
    assert "🏆" in out["/top news"][0] and "flawfence" in out["/top news"][0]
    assert "flawfence" in out["/wallet flawfence"][0] and "+26.0%" in out["/wallet flawfence"][0]
    assert "⭐" in out["/follow flawfence"][0] and W in out["/following"][0]
    assert "$2,500" in out["/threshold 2500"][0] and "/threshold 5000" in out["/threshold abc"][0]
    assert "сигналы" in out["/alerts"][0].lower()
    assert "Сигналов пока нет" in out["/radar"][0]
    assert "48.0%" in out["/stats"][0]
    assert "ссылку" in out["/market hello"][0]
    assert "flawfence" in out[W][0]                     # адрес без команды → карточка кошелька
    assert st.user(77)["threshold"] == 2500 and st.following(77) == [W]


def test_bare_link_shows_market(tmp_path, monkeypatch):
    st = Store(tmp_path / "b2.db")
    monkeypatch.setattr(app, "store", st)

    class FakeClient:
        async def event(self, slug):
            return {"markets": [{"slug": "m", "question": "Germany vs. Greece", "conditionId": "C", "volume": "10",
                                 "closed": False, "outcomes": '["Germany", "Greece"]',
                                 "outcomePrices": '["0.8", "0.2"]', "clobTokenIds": '["t1", "t2"]'}]}

        async def holders(self, cond):
            return [{"token": "t1", "holders": [{"proxyWallet": W, "amount": 1000, "outcomeIndex": 0, "name": "x"}]}]
    monkeypatch.setattr(app, "client", FakeClient())
    session = FakeSession()
    bot = Bot("123456:TEST", session=session, default=DefaultBotProperties(parse_mode="HTML"))
    user = User(id=78, is_bot=False, first_name="T", language_code="ru")
    upd = Update(update_id=1, message=Message(message_id=1, date=datetime.now(), from_user=user,
                                              chat=Chat(id=78, type="private"),
                                              text="https://polymarket.com/event/unl-ger-grc-2026-09-27-more-markets"))
    asyncio.run(app.dp.feed_update(bot, upd))
    assert session.sent and "Germany vs. Greece" in session.sent[-1].text and "0.80" in session.sent[-1].text
