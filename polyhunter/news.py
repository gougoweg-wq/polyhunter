"""Новости для рынков политики и войн: выбор рынков, сбор заголовков, решение о ставке, оценка прогнозов."""
import html
import json
import re
import time
from email.utils import parsedate_to_datetime

from . import model as mdl

NEWS_TAGS = ("geopolitics", "politics", "world", "elections", "ukraine", "middle-east")
GNEWS = "https://news.google.com/rss/search"


# ------------------------------------------------------------------ заголовки
def parse_rss(xml):
    items = []
    for block in re.findall(r"<item>(.*?)</item>", xml or "", re.S):
        def tag(name):
            m = re.search(rf"<{name}[^>]*>(.*?)</{name}>", block, re.S)
            return html.unescape(re.sub(r"<!\[CDATA\[|\]\]>", "", m.group(1)).strip()) if m else ""
        title, source = tag("title"), tag("source")
        if source and title.endswith(" - " + source):
            title = title[: -len(" - " + source)]
        else:
            title = re.sub(r"\s+-\s+[^-]{2,60}$", "", title)
        try:
            ts = int(parsedate_to_datetime(tag("pubDate")).timestamp())
        except (TypeError, ValueError):
            ts = 0
        items.append(dict(title=title, link=tag("link"), ts=ts, source=source))
    return sorted(items, key=lambda x: -x["ts"])


_TAIL = re.compile(r"\s*\b(by|before|through|in|on|after|until)\b\s*(\.\.\.|…|[A-Z][a-z]+\.? \d{1,2}(, ?\d{4})?|\d{4}|[A-Z][a-z]+)?\s*$")


def query_for(question):
    """Поисковый запрос из вопроса рынка: без «Will», дат, многоточий и хвостов «by …»."""
    q = question.strip().rstrip("?").strip()
    q = re.sub(r"^(Will|Is|Does|Did|Are)\s+(the\s+)?", "", q)
    q = q.replace("...", " ").replace("…", " ").strip()
    for _ in range(2):
        q = _TAIL.sub("", q).strip()
    q = re.sub(r"\b(19|20)\d{2}\b", "", q)
    q = re.sub(r"\s+x\s+", " ", q)                      # «US x Iran» у Polymarket значит «US и Iran»
    return re.sub(r"\s{2,}", " ", q).strip(" ,.-")


def search_params(query, days=7):
    """Google News: только свежее — оператор when:Nd."""
    return {"q": f"{query} when:{days}d", "hl": "en-US", "gl": "US", "ceid": "US:en"}


async def fetch_news(http, query, days=7):
    r = await http.get(GNEWS, params=search_params(query, days), timeout=30)
    return parse_rss(r.text) if r.status_code == 200 else []


# ------------------------------------------------------------------ рынки
def _jl(x):
    return json.loads(x) if isinstance(x, str) else (x or [])


def select_markets(events, min_liquidity=10000, limit=25, now=None):
    """Открытые бинарные рынки Yes/No из событий о политике и войнах, по объёму за сутки."""
    now = now or time.time()
    out, seen = [], set()
    for e in events:
        for m in e.get("markets") or []:
            if m.get("closed") or not m.get("active", True) or m.get("conditionId") in seen:
                continue
            outcomes, prices, tokens = _jl(m.get("outcomes")), _jl(m.get("outcomePrices")), _jl(m.get("clobTokenIds"))
            if [o.lower() for o in outcomes] != ["yes", "no"] or len(tokens) != 2 or len(prices) != 2:
                continue
            yes = float(prices[0])
            if not 0.03 <= yes <= 0.97 or float(m.get("liquidity") or 0) < min_liquidity:
                continue
            seen.add(m["conditionId"])
            out.append(dict(condition_id=m["conditionId"], question=m.get("question") or e.get("title", ""),
                            description=(m.get("description") or "")[:1500], end_date=(m.get("endDate") or "")[:10],
                            yes_token=tokens[0], no_token=tokens[1], yes_price=yes, slug=m.get("slug", ""),
                            event_slug=e.get("slug", ""), volume24=float(m.get("volume24hr") or 0)))
    return sorted(out, key=lambda x: -x["volume24"])[:limit]


# ------------------------------------------------------------------ решение
def decide(p_yes, yes_ask, no_ask, confidence, bankroll, kelly_frac=0.25, cap=0.015, min_usd=5):
    """Ставим только на уверенные прогнозы с большим перевесом: high — от 8 п.п., medium — от 12 п.п."""
    margin = {"high": 0.08, "medium": 0.12}.get(confidence)
    none = dict(side=None, usd=0.0)
    if margin is None:
        return none
    yes = mdl.decide(p_yes, yes_ask, bankroll, margin=margin, kelly_frac=kelly_frac, cap=cap, min_usd=min_usd)
    no = mdl.decide(1 - p_yes, no_ask, bankroll, margin=margin, kelly_frac=kelly_frac, cap=cap, min_usd=min_usd)
    if yes["bet"] and (not no["bet"] or yes["edge"] >= no["edge"]):
        return dict(side="YES", usd=yes["usd"], edge=yes["edge"])
    if no["bet"]:
        return dict(side="NO", usd=no["usd"], edge=no["edge"])
    return none


def score_forecasts(rows):
    """Brier прогнозов модели против цены рынка в момент прогноза (меньше — лучше)."""
    rows = [r for r in rows if r.get("outcome") in (0, 1)]
    if not rows:
        return dict(n=0, brier_model=None, brier_market=None, model_better=None)
    bm = sum((r["p_yes"] - r["outcome"]) ** 2 for r in rows) / len(rows)
    bk = sum((r["price"] - r["outcome"]) ** 2 for r in rows) / len(rows)
    return dict(n=len(rows), brier_model=bm, brier_market=bk, model_better=bm < bk)
