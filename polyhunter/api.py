"""Клиент открытых API Polymarket (data-api, gamma) и чистые помощники."""
import asyncio
import json
import re

import httpx

DATA = "https://data-api.polymarket.com"
GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
UA = {"User-Agent": "polyhunter-bot/2.0 (open-data research)"}

LINK = re.compile(r"polymarket\.com/(event|market)/([\w-]+)(?:/([\w-]+))?", re.I)


# ---------------------------------------------------------------- чистые помощники
def parse_link(text):
    m = LINK.search(text or "")
    if not m:
        return None, None
    kind, first, second = m.group(1).lower(), m.group(2), m.group(3)
    if kind == "market":
        return None, first
    return first, second


def normalize_trade(t):
    return dict(tx=t["transactionHash"], asset=t["asset"], wallet=t["proxyWallet"].lower(), side=t["side"],
                price=float(t["price"]), usd=float(t["size"]) * float(t["price"]), ts=int(t["timestamp"]),
                title=t.get("title") or "", slug=t.get("slug") or "", event_slug=t.get("eventSlug") or "",
                outcome=t.get("outcome") or "", condition_id=t.get("conditionId") or "", name=t.get("name") or "")


def _jl(x):
    return json.loads(x) if isinstance(x, str) else (x or [])


def pick_market(event, market_slug=None):
    ms = event.get("markets") or []
    if market_slug:
        for m in ms:
            if m.get("slug") == market_slug:
                return m
    open_ms = [m for m in ms if not m.get("closed")] or ms
    return max(open_ms, key=lambda m: float(m.get("volume") or 0)) if open_ms else None


def smart_money(market, holders, scores, min_lean=1000):
    """Сколько денег кошельков тиров S/A и F стоит на каждом исходе."""
    outcomes, prices, tokens = _jl(market.get("outcomes")), _jl(market.get("outcomePrices")), _jl(market.get("clobTokenIds"))
    rows = []
    for i, name in enumerate(outcomes):
        price = float(prices[i]) if i < len(prices) else 0.0
        tok = tokens[i] if i < len(tokens) else None
        hs = next((h["holders"] for h in holders if h.get("token") == tok), [])
        top, smart, fade = [], 0.0, 0.0
        for h in hs:
            w = h["proxyWallet"].lower()
            usd = float(h.get("amount") or 0) * price
            sc = scores.get(w)
            if sc and sc["tier"] in ("S", "A"):
                smart += usd
            elif sc and sc["tier"] == "F":
                fade += usd
            top.append(dict(wallet=w, name=(sc or {}).get("name") or h.get("name") or "", usd=usd,
                            tier=(sc or {}).get("tier", "?")))
        top.sort(key=lambda x: (x["tier"] not in ("S", "A"), -x["usd"]))
        rows.append(dict(outcome=name, price=price, smart_usd=smart, fade_usd=fade, top=top[:4]))
    lean = None
    if rows:
        best = max(rows, key=lambda r: r["smart_usd"] - r["fade_usd"])
        if best["smart_usd"] - best["fade_usd"] >= min_lean:
            lean = best["outcome"]
    return dict(outcomes=rows, lean=lean)


def parse_book(raw):
    """Стакан CLOB → (биды от лучшего, аски от лучшего) как [(цена, размер)]."""
    bids = sorted(((float(x["price"]), float(x["size"])) for x in raw.get("bids") or []), reverse=True)
    asks = sorted((float(x["price"]), float(x["size"])) for x in raw.get("asks") or [])
    return bids, asks


def winner_token(market):
    """Токен выигравшего исхода закрытого рынка или None, пока исход не известен."""
    if not market.get("closed"):
        return None
    prices = [float(x) for x in _jl(market.get("outcomePrices"))]
    tokens = _jl(market.get("clobTokenIds"))
    if not prices or max(prices) < 0.99:
        return None
    return tokens[prices.index(max(prices))] if len(tokens) == len(prices) else None


def fee_rate(market):
    return float((market.get("feeSchedule") or {}).get("rate") or 0.0)


# ---------------------------------------------------------------- сеть
class Client:
    def __init__(self):
        self.h = httpx.AsyncClient(headers=UA, timeout=30)

    async def get(self, url, **params):
        for attempt in range(5):
            try:
                r = await self.h.get(url, params=params)
                if r.status_code in (429, 500, 502, 503, 504):
                    await asyncio.sleep(2 ** attempt)
                    continue
                r.raise_for_status()
                return r.json()
            except (httpx.TransportError, httpx.TimeoutException):
                await asyncio.sleep(2 ** attempt)
        raise RuntimeError(f"failed {url}")

    async def trades(self, min_usd=1000, limit=500):
        rows = await self.get(f"{DATA}/trades", limit=limit, filterType="CASH", filterAmount=min_usd)
        return [normalize_trade(t) for t in rows if isinstance(rows, list)]

    async def history_markets(self, wallet, exclude_condition=None):
        """Сколько других рынков у кошелька в последних 100 сделках."""
        rows = await self.get(f"{DATA}/activity", user=wallet, limit=100, type="TRADE")
        return len({r.get("conditionId") for r in rows if r.get("conditionId") != exclude_condition})

    async def event(self, slug):
        d = await self.get(f"{GAMMA}/events", slug=slug)
        return d[0] if d else None

    async def market_by_slug(self, slug):
        d = await self.get(f"{GAMMA}/markets", slug=slug)
        return d[0] if d else None

    async def holders(self, condition_id, limit=20):
        return await self.get(f"{DATA}/holders", market=condition_id, limit=limit)

    async def book(self, token):
        """Стакан исхода; у закрытого или разрешённого рынка CLOB отвечает 404 — это пустой стакан."""
        try:
            return parse_book(await self.get(f"{CLOB}/book", token_id=token))
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return [], []
            raise

    async def midpoints(self, tokens):
        out = {}
        for t in tokens:
            try:
                out[t] = float((await self.get(f"{CLOB}/midpoint", token_id=t)).get("mid"))
            except Exception:
                continue
        return out

    async def market_by_token(self, token):
        d = await self.get(f"{GAMMA}/markets", clob_token_ids=token)
        if not d:
            d = await self.get(f"{GAMMA}/markets", clob_token_ids=token, closed="true")
        return d[0] if d else None

    async def market_by_condition(self, condition_id):
        d = await self.get(f"{GAMMA}/markets", condition_ids=condition_id, closed="true")
        if not d:
            d = await self.get(f"{GAMMA}/markets", condition_ids=condition_id)
        return d[0] if d else None

    async def leader_activity(self, wallet, limit=50):
        return await self.get(f"{DATA}/activity", user=wallet, limit=limit, type="TRADE")

    async def leader_position(self, wallet, condition_id, asset):
        rows = await self.get(f"{DATA}/positions", user=wallet, market=condition_id, sizeThreshold=0)
        return sum(float(r.get("size") or 0) for r in rows if r.get("asset") == asset)

    async def close(self):
        await self.h.aclose()
