"""Бумажный трейдер: модель торгует счётом «ai», копировщики повторяют её и выбранные кошельки,
рынки рассчитываются по исходу. Сеть и модель подаются снаружи — в тестах их подменяют."""
from . import api, copytrade, model as mdl
from .classify import category
from .paper import PaperError

AI = "ai"
AI_VERSION = 2

# v2: против китов ставим только там, где это работало и на отборе (июль–15.08), и на проверке (15.08–28.09):
# кит покупает аутсайдера или «50 на 50». Когда кит берёт фаворита, он прав — ставить против него убыточно.
FADE_MAX_WHALE_PRICE = {"sports": 0.60, "crypto": 0.60, "news": 0.40}


def fade_allowed(cat, whale_price):
    return whale_price < FADE_MAX_WHALE_PRICE.get(cat, 0.0)


def _mk(src):
    """Описание исхода из сделки радара (наш формат) или из activity data-api."""
    return dict(asset=src["asset"], condition_id=src.get("condition_id") or src.get("conditionId", ""),
                outcome=src.get("outcome", ""), title=src.get("title", ""), slug=src.get("slug", ""),
                event_slug=src.get("event_slug") or src.get("eventSlug", ""))


class Trader:
    def __init__(self, store, paper, client, predictor, min_signal_usd=1000, max_ai_positions=40,
                 max_new_per_hour=6):
        self.store = store
        self.paper = paper
        self.client = client
        self.predictor = predictor
        self.min_signal_usd = min_signal_usd
        self.max_ai_positions = max_ai_positions
        self.max_new_per_hour = max_new_per_hour   # не набирать весь портфель за минуту

    # ------------------------------------------------------------ признаки кошелька из рейтинга
    def wallet_features(self, wallet, cat):
        s = self.store.score(wallet, "all")
        if not s:
            return None
        c = self.store.score(wallet, cat)
        cats = {cat: (c["edge"], c["n"])} if c else {}
        return dict(post_edge=s["post_edge"], n=s["n"], roi=s["roi"], cats=cats)

    def ai_enabled(self):
        return bool(self.predictor and (self.predictor.report or {}).get("tradable"))

    # ------------------------------------------------------------ модель
    async def on_trades(self, trades, margin=0.02, cap=0.02):
        """Для каждой крупной покупки известного кошелька модель даёт P(сторона кита выиграет).
        follow — купить ту же сторону, если P выше её цены; fade — купить противоположную, если
        1 − P выше цены противоположной. Против тиров S и A не ставим: они обыгрывают цены."""
        events = []
        if not self.ai_enabled():
            return events
        for t in trades:
            if t["side"] != "BUY" or t["usd"] < self.min_signal_usd:
                continue
            if not self.store.mark_seen(("ai_eval", t["tx"], t["asset"])):
                continue                      # эту сделку уже оценивали в прошлом проходе радара
            score = self.store.score(t["wallet"], "all")
            if not score:
                continue
            cat = category(t["title"], t["slug"])
            wf = self.wallet_features(t["wallet"], cat)
            open_pos = self.paper.positions(AI)
            held = {p["condition_id"] for p in open_pos}
            events_held = {p["event_slug"] for p in open_pos if p["event_slug"]}
            if t["condition_id"] in held or (t.get("event_slug") and t["event_slug"] in events_held):
                continue                      # одно событие — одна позиция: разные рынки матча связаны
            if len(held) >= self.max_ai_positions or self._opened_last_hour() >= self.max_new_per_hour:
                break
            bids, asks = await self.client.book(t["asset"])
            if not asks:
                continue
            ask = asks[0][0]
            p_model = self.predictor.prob(ask, t["usd"], cat, wf)
            bankroll = self.paper.account(AI)["cash"]
            choice = None
            m = await self.client.market_by_token(t["asset"])
            fee = api.fee_rate(m or {})
            d = mdl.decide(p_model, ask + fee * ask * (1 - ask), bankroll, margin=margin, cap=cap)
            if d["bet"] and score["tier"] in ("S", "A", "B"):
                choice = ("follow", _mk(t), asks, d)
            elif score["tier"] not in ("S", "A") and fade_allowed(cat, t["price"]):
                tokens, names = api._jl((m or {}).get("clobTokenIds")), api._jl((m or {}).get("outcomes"))
                if len(tokens) == 2 and t["asset"] in tokens:
                    j = 1 - tokens.index(t["asset"])
                    _b, asks_o = await self.client.book(tokens[j])
                    if asks_o:
                        ao = asks_o[0][0]
                        d = mdl.decide(1 - p_model, ao + fee * ao * (1 - ao), bankroll, margin=margin, cap=cap)
                        if d["bet"]:
                            mk = dict(_mk(t), asset=tokens[j], outcome=names[j] if j < len(names) else "")
                            choice = ("fade", mk, asks_o, d)
            if not choice:
                continue
            side, mk, book_asks, d = choice
            if not self.store.mark_seen(("ai", mk["condition_id"] or mk["asset"])):
                continue
            try:
                r = self.paper.buy(AI, mk, book_asks, d["usd"], source=f"ai:{side}", fee_rate=fee)
            except PaperError:
                continue
            events.append(dict(kind="ai_buy", owner=AI, side=side, mk=mk, price=r["price"], usd=r["usd"],
                               p_model=p_model, edge=d["edge"], leader=t["wallet"], leader_tier=score["tier"],
                               leader_outcome=t["outcome"], leader_price=ask))
            events += self._mirror_buy(AI, mk, book_asks)
        return events

    def migrate(self, version=AI_VERSION):
        """Новая версия правил — новый счёт модели; итог прежней версии сохраняется в meta."""
        cur = self.store.meta("ai_version")
        if cur == version:
            return False
        acc = self.paper.account(AI)
        pos = self.paper.positions(AI)
        with self.store.lock:
            n_trades = self.store.c.execute("select count(*) from paper_trades where owner=?", (AI,)).fetchone()[0]
        self.store.set_meta(f"ai_archive_v{cur or 1}", dict(cash=acc["cash"], positions=len(pos), trades=n_trades,
                                                            equity_at_cost=acc["cash"] + sum(p["cost"] for p in pos)))
        self.paper.reset(AI)
        self.store.set_meta("ai_version", version)
        return True

    def _opened_last_hour(self):
        import time as _t
        with self.store.lock:
            return self.store.c.execute("select count(*) from paper_trades where owner=? and side='BUY' and ts > ?",
                                        (AI, int(_t.time()) - 3600)).fetchone()[0]

    def _mirror_buy(self, leader, mk, asks):
        out = []
        for chat, usd in self.store.copiers(leader):
            if not self.store.mark_seen(("copy", chat, mk["asset"], leader)):
                continue
            try:
                r = self.paper.buy(f"u:{chat}", mk, asks, usd, source=f"copy:{leader}")
                out.append(dict(kind="copy_buy", chat=chat, leader=leader, mk=mk, price=r["price"], usd=r["usd"]))
            except PaperError as e:
                out.append(dict(kind="copy_fail", chat=chat, leader=leader, mk=mk, reason=str(e)))
        return out

    # ------------------------------------------------------------ копирование кошельков
    async def copy_step(self):
        events = []
        for leader in self.store.copy_leaders():
            if not leader.startswith("0x"):
                continue
            acts = await self.client.leader_activity(leader)
            cursor = self.store.meta(f"copy_cursor:{leader}")
            fresh, cur = copytrade.new_trades(acts, cursor)
            self.store.set_meta(f"copy_cursor:{leader}", cur)
            buys = {}
            sells = {}
            for a in fresh:
                if a.get("side") == "BUY":
                    buys.setdefault(a["asset"], a)
                elif a.get("side") == "SELL":
                    sells.setdefault(a["asset"], [a, 0.0])
                    sells[a["asset"]][1] += float(a.get("size") or 0)
            for asset, a in buys.items():
                bids, asks = await self.client.book(asset)
                if asks:
                    events += self._mirror_buy(leader, _mk(a), asks)
            for asset, (a, sold) in sells.items():
                holders = [(c, u) for c, u in self.store.copiers(leader)
                           if any(p["asset"] == asset for p in self.paper.positions(f"u:{c}"))]
                if not holders:
                    continue
                remaining = await self.client.leader_position(leader, a.get("conditionId", ""), asset)
                frac = copytrade.sell_fraction(sold, remaining)
                bids, asks = await self.client.book(asset)
                for chat, _usd in holders:
                    try:
                        r = self.paper.sell(f"u:{chat}", asset, bids, frac, source=f"copy:{leader}")
                        events.append(dict(kind="copy_sell", chat=chat, leader=leader, mk=_mk(a), fraction=frac,
                                           price=r["price"], pnl=r["pnl"]))
                    except PaperError:
                        continue
        return events

    # ------------------------------------------------------------ расчёт по исходу
    async def settle_step(self):
        events = []
        for pos in self.paper.open_assets():
            m = await self.client.market_by_token(pos["asset"])
            win = api.winner_token(m or {})
            if not win:
                continue
            won = win == pos["asset"]
            for owner, payout, pnl in self.paper.settle(pos["asset"], won):
                events.append(dict(kind="settle", owner=owner, won=won, payout=payout, pnl=pnl,
                                   title=pos["title"], outcome=pos["outcome"]))
        return events

    async def marks(self):
        assets = [p["asset"] for p in self.paper.open_assets()]
        return await self.client.midpoints(assets) if assets else {}
