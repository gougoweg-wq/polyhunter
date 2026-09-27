"""Новостная модель: читает свежие заголовки по рынкам политики и войн, спрашивает «мозг»
о вероятности, записывает прогноз вместе с ценой рынка и ставит тестовыми деньгами со счёта «news».

Каждый прогноз проверяется потом по исходу: Brier модели против Brier цены рынка в момент прогноза.
"""
import json
import time

from . import api, brain, news
from .paper import PaperError

OWNER = "news"
GAMMA_EVENTS = f"{api.GAMMA}/events"


class NewsTrader:
    def __init__(self, store, paper, client, http, ask_fn=None, per_cycle=10, refresh_hours=12, min_headlines=3):
        self.store, self.paper, self.client, self.http = store, paper, client, http
        self.ask = ask_fn or brain.ask
        self.per_cycle = per_cycle
        self.refresh = refresh_hours * 3600
        self.min_headlines = min_headlines
        with store.lock, store.c:
            store.c.execute("""create table if not exists forecasts(id integer primary key autoincrement, ts integer,
                condition_id text, question text, slug text, event_slug text, yes_token text, no_token text,
                end_date text, price real, p_yes real, confidence text, reasoning text, headlines text,
                model text, outcome integer)""")

    # ------------------------------------------------------------ чтение
    def forecasts(self, limit=20):
        with self.store.lock:
            return [dict(r) for r in self.store.c.execute("select * from forecasts order by id desc limit ?", (limit,))]

    def track_record(self):
        with self.store.lock:
            rows = [dict(p_yes=r[0], price=r[1], outcome=r[2]) for r in self.store.c.execute(
                "select p_yes, price, outcome from forecasts where outcome is not null")]
        return news.score_forecasts(rows)

    def _recent(self, condition_id):
        with self.store.lock:
            r = self.store.c.execute("select max(ts) from forecasts where condition_id=?", (condition_id,)).fetchone()
        return r[0] and time.time() - r[0] < self.refresh

    # ------------------------------------------------------------ цикл
    async def cycle(self):
        evs = []
        for tag in news.NEWS_TAGS:
            try:
                evs += await self.client.get(GAMMA_EVENTS, tag_slug=tag, closed="false", limit=100,
                                             order="volume24hr", ascending="false")
            except Exception:
                continue
        markets = [m for m in news.select_markets(evs, limit=100) if not self._recent(m["condition_id"])]
        events = []
        for m in markets[: self.per_cycle]:
            items = await news.fetch_news(self.http, news.query_for(m["question"]))
            if len(items) < self.min_headlines:
                continue
            prompt = brain.forecast_prompt(m, items)
            try:
                f = brain.parse_forecast(await self.ask(self.http, prompt))
            except Exception:
                continue
            if not f:
                continue
            with self.store.lock, self.store.c:
                self.store.c.execute(
                    "insert into forecasts(ts, condition_id, question, slug, event_slug, yes_token, no_token, end_date,"
                    " price, p_yes, confidence, reasoning, headlines, model, outcome) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,null)",
                    (int(time.time()), m["condition_id"], m["question"], m["slug"], m["event_slug"], m["yes_token"],
                     m["no_token"], m["end_date"], m["yes_price"], f["p_yes"], f["confidence"], f["reasoning"],
                     json.dumps([it["title"] for it in items[:10]], ensure_ascii=False), brain.config()["model"]))
            events += await self._trade(m, f)
        return events

    async def _trade(self, m, f):
        if any(p["condition_id"] == m["condition_id"] for p in self.paper.positions(OWNER)):
            return []
        _b, yes_asks = await self.client.book(m["yes_token"])
        _b, no_asks = await self.client.book(m["no_token"])
        if not yes_asks or not no_asks:
            return []
        d = news.decide(f["p_yes"], yes_asks[0][0], no_asks[0][0], f["confidence"], self.paper.account(OWNER)["cash"])
        if not d["side"]:
            return []
        yes = d["side"] == "YES"
        mk = dict(asset=m["yes_token"] if yes else m["no_token"], condition_id=m["condition_id"],
                  outcome="Yes" if yes else "No", title=m["question"], slug=m["slug"], event_slug=m["event_slug"])
        asks = yes_asks if yes else no_asks
        try:
            r = self.paper.buy(OWNER, mk, asks, d["usd"], source="news")
        except PaperError:
            return []
        out = [dict(kind="news_buy", owner=OWNER, mk=mk, price=r["price"], usd=r["usd"], p_yes=f["p_yes"],
                    confidence=f["confidence"], reasoning=f["reasoning"], market_price=m["yes_price"])]
        for chat, usd in self.store.copiers(OWNER):
            try:
                rr = self.paper.buy(f"u:{chat}", mk, asks, usd, source="copy:news")
                out.append(dict(kind="copy_buy", chat=chat, leader=OWNER, mk=mk, price=rr["price"], usd=rr["usd"]))
            except PaperError as e:
                out.append(dict(kind="copy_fail", chat=chat, leader=OWNER, mk=mk, reason=str(e)))
        return out

    async def resolve(self):
        """Проставить исходы прогнозам по закрытым рынкам."""
        with self.store.lock:
            pending = [dict(r) for r in self.store.c.execute(
                "select id, condition_id, yes_token from forecasts where outcome is null")]
        done = {}
        for f in pending:
            if f["condition_id"] not in done:
                m = await self.client.market_by_condition(f["condition_id"])
                done[f["condition_id"]] = api.winner_token(m or {})
            win = done[f["condition_id"]]
            if win:
                with self.store.lock, self.store.c:
                    self.store.c.execute("update forecasts set outcome=? where id=?", (int(win == f["yes_token"]), f["id"]))
        return []
