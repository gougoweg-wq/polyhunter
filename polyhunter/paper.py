"""Бумажный счёт: тестовые деньги, настоящие цены стакана Polymarket.

Покупка проходит по уровням стакана (как рыночная заявка), продажа — по бидам, расчёт по исходу:
выигравшая акция стоит $1, проигравшая $0. Владельцы счетов: «u:<chat_id>», «ai», «desk».
"""
import time


class PaperError(Exception):
    pass


def walk_book(levels, usd=None, shares=None):
    """Пройти уровни стакана. Покупка: levels = аски по возрастанию, лимит usd → (акции, потрачено).
    Продажа: levels = биды по убыванию, лимит shares → (продано акций, получено $)."""
    got_sh, money = 0.0, 0.0
    for price, size in levels:
        if price <= 0:
            continue
        if usd is not None:
            left = usd - money
            if left <= 1e-9:
                break
            q = min(size, left / price)
        else:
            left = shares - got_sh
            if left <= 1e-9:
                break
            q = min(size, left)
        got_sh += q
        money += q * price
    return got_sh, money


def taker_fee(shares, price, rate):
    return shares * rate * price * (1 - price) if rate else 0.0


class Paper:
    def __init__(self, store, start_cash=1000.0):
        self.s = store
        self.start = start_cash

    # ------------------------------------------------------------ чтение
    def account(self, owner):
        with self.s.lock, self.s.c:
            r = self.s.c.execute("select cash, start from paper_accounts where owner=?", (owner,)).fetchone()
            if not r:
                self.s.c.execute("insert into paper_accounts values(?,?,?,?)", (owner, self.start, self.start, int(time.time())))
                r = (self.start, self.start)
        return dict(owner=owner, cash=r[0], start=r[1])

    def positions(self, owner):
        with self.s.lock:
            rows = self.s.c.execute("select * from paper_positions where owner=? order by opened", (owner,)).fetchall()
        return [dict(r) for r in rows]

    def holders(self, asset):
        with self.s.lock:
            return [dict(r) for r in self.s.c.execute("select * from paper_positions where asset=?", (asset,))]

    def open_assets(self):
        with self.s.lock:
            return [dict(r) for r in self.s.c.execute(
                "select asset, condition_id, max(title) title, max(outcome) outcome from paper_positions group by asset")]

    def trades(self, owner, limit=10):
        with self.s.lock:
            return [dict(r) for r in self.s.c.execute(
                "select * from paper_trades where owner=? order by id desc limit ?", (owner, limit))]

    def equity(self, owner, marks):
        acc = self.account(owner)
        return acc["cash"] + sum(p["shares"] * marks.get(p["asset"], p["cost"] / p["shares"] if p["shares"] else 0)
                                 for p in self.positions(owner))

    def leaderboard(self, marks, limit=10, prefix="u:"):
        with self.s.lock:
            owners = [r[0] for r in self.s.c.execute("select owner from paper_accounts where owner like ?", (prefix + "%",))]
        rows = []
        for o in owners:
            eq = self.equity(o, marks)
            rows.append((o, eq, eq - self.account(o)["start"]))
        return sorted(rows, key=lambda r: -r[2])[:limit]

    # ------------------------------------------------------------ сделки
    def _log(self, owner, asset, side, shares, price, usd, pnl, source, mk):
        self.s.c.execute("insert into paper_trades(owner, ts, asset, side, shares, price, usd, pnl, source, title, outcome)"
                         " values(?,?,?,?,?,?,?,?,?,?,?)",
                         (owner, int(time.time()), asset, side, shares, price, usd, pnl, source,
                          mk.get("title", ""), mk.get("outcome", "")))

    def buy(self, owner, mk, asks, usd, source="manual", fee_rate=0.0, max_price=0.99):
        if usd <= 0:
            raise PaperError("amount")
        acc = self.account(owner)
        asks = sorted((p, s) for p, s in asks if p <= max_price)
        if not asks:
            raise PaperError("no_liquidity")
        shares, cost = walk_book(asks, usd=usd)
        if shares <= 0:
            raise PaperError("no_liquidity")
        avg = cost / shares
        fee = taker_fee(shares, avg, fee_rate)
        if cost + fee > acc["cash"] + 1e-9:
            raise PaperError("cash")
        with self.s.lock, self.s.c:
            self.s.c.execute("update paper_accounts set cash = cash - ? where owner=?", (cost + fee, owner))
            r = self.s.c.execute("select shares, cost from paper_positions where owner=? and asset=?", (owner, mk["asset"])).fetchone()
            if r:
                self.s.c.execute("update paper_positions set shares=?, cost=? where owner=? and asset=?",
                                 (r[0] + shares, r[1] + cost + fee, owner, mk["asset"]))
            else:
                self.s.c.execute("insert into paper_positions values(?,?,?,?,?,?,?,?,?,?,?)",
                                 (owner, mk["asset"], mk.get("condition_id", ""), mk.get("outcome", ""),
                                  mk.get("title", ""), mk.get("slug", ""), mk.get("event_slug", ""),
                                  shares, cost + fee, int(time.time()), source))
            self._log(owner, mk["asset"], "BUY", shares, avg, cost + fee, None, source, mk)
        return dict(shares=shares, price=avg, usd=cost + fee, fee=fee, partial=cost < usd - 0.01)

    def sell(self, owner, asset, bids, fraction=1.0, source="manual", fee_rate=0.0):
        with self.s.lock:
            pos = self.s.c.execute("select * from paper_positions where owner=? and asset=?", (owner, asset)).fetchone()
        if not pos:
            raise PaperError("no_position")
        pos = dict(pos)
        want = pos["shares"] * max(0.0, min(1.0, fraction))
        bids = sorted(((p, s) for p, s in bids if p > 0), reverse=True)
        sold, got = walk_book(bids, shares=want)
        if sold <= 0:
            raise PaperError("no_liquidity")
        fee = taker_fee(sold, got / sold, fee_rate)
        cost_part = pos["cost"] * sold / pos["shares"]
        pnl = got - fee - cost_part
        with self.s.lock, self.s.c:
            self.s.c.execute("update paper_accounts set cash = cash + ? where owner=?", (got - fee, owner))
            if pos["shares"] - sold <= 1e-6:
                self.s.c.execute("delete from paper_positions where owner=? and asset=?", (owner, asset))
            else:
                self.s.c.execute("update paper_positions set shares=?, cost=? where owner=? and asset=?",
                                 (pos["shares"] - sold, pos["cost"] - cost_part, owner, asset))
            self._log(owner, asset, "SELL", sold, got / sold, got - fee, pnl, source, pos)
        return dict(shares=sold, price=got / sold, proceeds=got - fee, pnl=pnl)

    def settle(self, asset, won):
        """Рынок разрешился: у всех держателей акция превращается в $1 или $0."""
        out = []
        for pos in self.holders(asset):
            payout = pos["shares"] if won else 0.0
            pnl = payout - pos["cost"]
            with self.s.lock, self.s.c:
                self.s.c.execute("update paper_accounts set cash = cash + ? where owner=?", (payout, pos["owner"]))
                self.s.c.execute("delete from paper_positions where owner=? and asset=?", (pos["owner"], asset))
                self._log(pos["owner"], asset, "WIN" if won else "LOSS", pos["shares"], 1.0 if won else 0.0,
                          payout, pnl, "settle", pos)
            out.append((pos["owner"], payout, pnl))
        return out

    def reset(self, owner):
        with self.s.lock, self.s.c:
            self.s.c.execute("delete from paper_positions where owner=?", (owner,))
            self.s.c.execute("delete from paper_accounts where owner=?", (owner,))
            self.s.c.execute("delete from paper_trades where owner=?", (owner,))
        self.account(owner)
