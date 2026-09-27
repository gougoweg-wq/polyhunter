"""Polymarket «охотник на инсайдеров».

Шаги:
  python3 hunter.py trades     — собрать крупные сделки из общей ленты (кандидаты-кошельки)
  python3 hunter.py positions  — выгрузить все разрешившиеся позиции кандидатов
  python3 hunter.py analyze    — проверить, выигрывают ли кошельки чаще, чем обещали цены

Идея теста: цена покупки исхода = вероятность, которую давал рынок. Если рынок честный,
кошелёк со ставками по ценам p1..pn в среднем выигрывает sum(p) раз. Выигрывает заметно
больше — это либо умение, либо информация. Кошельков много, поэтому поправка
Бенджамини–Хохберга, иначе «гениями» окажутся везунчики.
"""
import argparse
import json
import math
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from polyhunter.classify import category
from polyhunter.scoring import bh_qvalues, held_to_resolution, poisson_binomial_tail

API = "https://data-api.polymarket.com"
DB = Path(__file__).with_name("data") / "hunter.db"
UA = {"User-Agent": "polyhunter/0.1 (research)"}


# ---------------------------------------------------------------- http + db
def get(path, **params):
    url = f"{API}/{path}?{urllib.parse.urlencode(params)}"
    for attempt in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(2 ** attempt)
                continue
            raise
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(2 ** attempt)
    raise RuntimeError(f"failed: {url}")


def db():
    DB.parent.mkdir(exist_ok=True)
    c = sqlite3.connect(DB, timeout=60)
    c.executescript("""
    create table if not exists trades(
      tx text, asset text, wallet text, side text, size real, price real, usd real, ts integer,
      title text, slug text, event_slug text, outcome text, name text,
      primary key(tx, asset, wallet, side));
    create table if not exists positions(
      wallet text, asset text, condition_id text, avg_price real, stake real, pnl real, cur_price real,
      title text, slug text, event_slug text, outcome text, end_date text, ts integer, source text,
      primary key(wallet, asset));
    create table if not exists fetched(wallet text primary key, at integer, n integer);
    create table if not exists meta(k text primary key, v text);
    """)
    if not c.execute("select 1 from meta where k='stake_usd'").fetchone():  # разовая миграция старых строк
        c.execute("update positions set stake = stake * avg_price where source='closed'")
        c.execute("insert into meta values('stake_usd','1')")
        c.commit()
    return c


# ---------------------------------------------------------------- step 1: trades
def cmd_trades(a):
    c = db()
    n = 0
    for off in range(0, 10001, 500):  # API не отдаёт глубже offset 10000
        rows = get("trades", limit=500, offset=off, filterType="CASH", filterAmount=a.min_usd)
        if not isinstance(rows, list) or not rows:
            break
        c.executemany("insert or ignore into trades values(?,?,?,?,?,?,?,?,?,?,?,?,?)", [
            (t["transactionHash"], t["asset"], t["proxyWallet"], t["side"], t["size"], t["price"],
             t["size"] * t["price"], t["timestamp"], t.get("title"), t.get("slug"), t.get("eventSlug"),
             t.get("outcome"), t.get("name")) for t in rows])
        n += len(rows)
        c.commit()
    lo, hi, w = c.execute("select min(ts), max(ts), count(distinct wallet) from trades").fetchone()
    print(f"сделок получено {n}; в базе окно {time.strftime('%d.%m %H:%M', time.gmtime(lo))}–"
          f"{time.strftime('%d.%m %H:%M', time.gmtime(hi))} UTC, кошельков {w}")


# ---------------------------------------------------------------- step 2: positions
def fetch_wallet(w, max_pages):
    """Все разрешившиеся позиции кошелька.

    Ловушка API: выигрыш после выплаты уходит в closed-positions, а непогашенный
    проигрыш остаётся в positions (redeemable=true, curPrice=0). Берём оба списка.
    """
    out = {}
    for page in range(max_pages):
        rows = get("closed-positions", user=w, limit=50, offset=page * 50,
                   sortBy="TIMESTAMP", sortDirection="DESC")
        if not rows:
            break
        for x in rows:
            # totalBought — это акции, не доллары: ставка в $ = акции × средняя цена
            out[x["asset"]] = (w, x["asset"], x["conditionId"], x["avgPrice"],
                               (x.get("totalBought") or 0) * (x.get("avgPrice") or 0),
                               x.get("realizedPnl") or 0, x["curPrice"], x.get("title"), x.get("slug"),
                               x.get("eventSlug"), x.get("outcome"), x.get("endDate"), x.get("timestamp"), "closed")
        if len(rows) < 50:
            break
    for page in range(max_pages):
        rows = get("positions", user=w, limit=500, offset=page * 500, sizeThreshold=0)
        if not rows:
            break
        for x in rows:
            if not x.get("redeemable") or x["asset"] in out:
                continue
            out[x["asset"]] = (w, x["asset"], x["conditionId"], x["avgPrice"], x.get("initialValue") or 0,
                               (x.get("cashPnl") or 0) + (x.get("realizedPnl") or 0), x["curPrice"],
                               x.get("title"), x.get("slug"), x.get("eventSlug"), x.get("outcome"),
                               x.get("endDate"), None, "open-resolved")
        if len(rows) < 500:
            break
    return w, list(out.values())


def cmd_positions(a):
    c = db()
    done = {r[0] for r in c.execute("select wallet from fetched")}
    wallets = [r[0] for r in c.execute(
        "select wallet from trades group by wallet having max(usd) >= ? order by sum(usd) desc", (a.min_usd,))]
    todo = [w for w in wallets if w not in done][: a.max_wallets]
    print(f"кандидатов {len(wallets)}, уже выгружено {len(done)}, сейчас {len(todo)}")
    t0 = time.time()
    with ThreadPoolExecutor(a.threads) as ex:
        for i, (w, rows) in enumerate(ex.map(lambda w: fetch_wallet(w, a.max_pages), todo), 1):
            c.executemany("insert or replace into positions values(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
            c.execute("insert or replace into fetched values(?,?,?)", (w, int(time.time()), len(rows)))
            c.commit()
            if i % 25 == 0:
                print(f"  {i}/{len(todo)} кошельков, {time.time() - t0:.0f} с", flush=True)
    print("позиций в базе:", c.execute("select count(*) from positions").fetchone()[0])


# ---------------------------------------------------------------- step 3: statistics
def bh(pvals, q):
    """Индексы, прошедшие FDR q (через q-values из пакета)."""
    return {i for i, qi in enumerate(bh_qvalues(pvals)) if qi <= q}


def cmd_analyze(a):
    c = db()
    rows = c.execute("""select wallet, avg_price, stake, pnl, cur_price, title, slug, event_slug
                        from positions
                        where cur_price in (0, 1) and avg_price between ? and ? and stake >= ?""",
                     (a.pmin, 1 - a.pmin, a.min_stake)).fetchall()
    by = {}
    dropped = 0
    for w, p, stake, pnl, cur, title, slug, ev in rows:
        if not a.include_sold and not held_to_resolution(p, stake, pnl, cur):
            dropped += 1  # продал до исхода — это не ставка на исход, а торговля
            continue
        cat = category(title, slug)
        if a.category != "all" and cat != a.category:
            continue
        by.setdefault(w, []).append((p, int(cur == 1), stake, pnl, ev, cat))

    # общая калибровка: если рынок честный и выборка не смещена, выигрышей ≈ сумма цен
    allp = [x[0] for v in by.values() for x in v]
    allw = sum(x[1] for v in by.values() for x in v)
    if allp:
        mu = sum(allp); sd = math.sqrt(sum(p * (1 - p) for p in allp))
        print(f"Отброшено проданных до исхода: {dropped}")
        print(f"Калибровка по {len(allp)} позициям {len(by)} кошельков ({a.category}): "
              f"выиграно {allw}, ожидалось {mu:.0f} ± {sd:.0f} (z = {(allw - mu) / sd:+.2f})")

    stats = []
    for w, v in by.items():
        if len(v) < a.min_n:
            continue
        ps = [x[0] for x in v]
        wins = sum(x[1] for x in v)
        exp = sum(ps)
        sd = math.sqrt(sum(p * (1 - p) for p in ps))
        pval_ind = poisson_binomial_tail(ps, wins)
        # кластерно-устойчивый z: ставки на одно событие связаны, поэтому дисперсию
        # считаем по событиям: z = Σ(W−E) / sqrt(Σ_событий (W_e − E_e)²)
        ev = {}
        for x in v:
            d = ev.setdefault(x[4], [0.0, 0.0]); d[0] += x[1]; d[1] += x[0]
        num = sum(wv - ev_ for wv, ev_ in ev.values())
        den = math.sqrt(sum((wv - ev_) ** 2 for wv, ev_ in ev.values()))
        z_cl = num / den if den else 0.0
        pval = max(pval_ind, 0.5 * math.erfc(z_cl / math.sqrt(2)))  # берём более осторожный
        stake = sum(x[2] for x in v); pnl = sum(x[3] for x in v)
        low = [x for x in v if x[0] < 0.35]
        cats = {}
        for x in v:
            cats[x[5]] = cats.get(x[5], 0) + 1
        stats.append(dict(wallet=w, n=len(v), events=len({x[4] for x in v}), wins=wins, exp=exp,
                          z=(wins - exp) / sd if sd else 0, z_cl=z_cl, p=pval, p_ind=pval_ind, stake=stake, pnl=pnl,
                          roi=pnl / stake if stake else 0, low_n=len(low), low_wins=sum(x[1] for x in low),
                          low_exp=sum(x[0] for x in low), cats=cats))
    if not stats:
        print("мало данных"); return
    sig = bh([s["p"] for s in stats], a.fdr)
    for i, s in enumerate(stats):
        s["significant"] = i in sig
    stats.sort(key=lambda s: s["p"])
    print(f"Кошельков с ≥{a.min_n} позициями: {len(stats)}; значимы после поправки BH (FDR {a.fdr:.0%}): {len(sig)}")
    print(f"{'кошелёк':12} {'n':>5} {'событ':>5} {'выигр':>6} {'ожид':>6} {'z':>5} {'z_кл':>5} {'p':>9} {'ROI':>7} "
          f"{'PnL $':>10} {'дешёвые<0.35':>13}  категории")
    for s in stats[: a.top]:
        mark = "★" if s["significant"] else " "
        cats = ",".join(f"{k}:{v}" for k, v in sorted(s["cats"].items(), key=lambda kv: -kv[1]))
        print(f"{mark}{s['wallet'][:11]} {s['n']:5} {s['events']:5} {s['wins']:6} {s['exp']:6.1f} {s['z']:5.1f} {s['z_cl']:5.1f} "
              f"{s['p']:9.2e} {s['roi']:7.1%} {s['pnl']:10,.0f} {s['low_wins']:4}/{s['low_n']:<3}({s['low_exp']:4.1f})  {cats}")
    out = DB.parent / f"wallets_{a.category}.json"
    out.write_text(json.dumps(stats, ensure_ascii=False, indent=1))
    print("полный список:", out)


# ---------------------------------------------------------------- step 4: timing
CLOB = "https://clob.polymarket.com"
HORIZONS = [("10м", 600), ("1ч", 3600), ("6ч", 6 * 3600), ("24ч", 24 * 3600)]


def get_url(url):
    for attempt in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(2 ** attempt); continue
            raise
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(2 ** attempt)
    raise RuntimeError(url)


def price_at(hist, ts, final):
    """Последняя цена не позже ts; если рынок уже закрылся — итог 0/1."""
    if not hist or ts > hist[-1][0] + 3600:
        return final
    lo, hi = 0, len(hist) - 1
    if ts < hist[0][0]:
        return None
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if hist[mid][0] <= ts:
            lo = mid
        else:
            hi = mid - 1
    return hist[lo][1]


def wallet_buys(w, condition_id, asset):
    rows = get("activity", user=w, limit=500, type="TRADE", market=condition_id)
    return [(t["timestamp"], t["price"], t["usdcSize"]) for t in rows
            if t.get("side") == "BUY" and t.get("asset") == asset and t.get("usdcSize", 0) >= 100]


def cmd_timing(a):
    c = db()
    c.executescript("""create table if not exists prices(asset text, t integer, p real, primary key(asset, t));
                       create table if not exists prices_done(asset text primary key);
                       create table if not exists buys(wallet text, asset text, ts integer, price real, usd real,
                         final integer, title text, grp text, primary key(wallet, asset, ts, price, usd));""")
    stats = json.loads((DB.parent / f"wallets_{a.category}.json").read_text())
    sig = [s["wallet"] for s in stats if s["significant"]]
    import random
    random.seed(7)
    others = [s["wallet"] for s in stats if not s["significant"] and s["p"] > 0.2]
    base = random.sample(others, min(a.baseline, len(others)))
    print(f"значимых {len(sig)}, контрольных {len(base)} (случайные кошельки без значимости)")

    jobs = []
    for grp, wallets in (("значимые", sig), ("контроль", base)):
        for w in wallets:
            pos = c.execute("""select asset, condition_id, avg_price, stake, pnl, cur_price, title, slug
                               from positions where wallet=? and cur_price in (0,1) and avg_price between ? and ?
                               and stake >= ? order by stake desc""", (w, a.pmin, 1 - a.pmin, a.min_stake)).fetchall()
            pos = [x for x in pos if (a.category == "all" or category(x[6], x[7]) == a.category)
                   and held_to_resolution(x[2], x[3], x[4], x[5])][: a.per_wallet]
            jobs += [(grp, w, x) for x in pos]
    print(f"позиций для проверки: {len(jobs)}")

    def work(job):
        grp, w, (asset, cond, p, stake, pnl, cur, title, slug) = job
        return grp, w, asset, cur, title, wallet_buys(w, cond, asset)

    t0 = time.time()
    with ThreadPoolExecutor(a.threads) as ex:
        for i, (grp, w, asset, cur, title, buys) in enumerate(ex.map(work, jobs), 1):
            with c:
                c.executemany("insert or ignore into buys values(?,?,?,?,?,?,?,?)",
                              [(w, asset, ts, pr, usd, int(cur), title, grp) for ts, pr, usd in buys])
            if i % 100 == 0:
                print(f"  сделки: {i}/{len(jobs)} позиций, {time.time() - t0:.0f} с", flush=True)
    assets = [r[0] for r in c.execute("select distinct asset from buys")]
    todo = [x for x in assets if not c.execute("select 1 from prices_done where asset=?", (x,)).fetchone()]
    print(f"истории цен: нужно {len(todo)} из {len(assets)}")

    def fetch(asset):
        h = get_url(f"{CLOB}/prices-history?market={asset}&interval=max&fidelity=10").get("history", [])
        return asset, [(x["t"], x["p"]) for x in h]

    with ThreadPoolExecutor(a.threads) as ex:
        for i, (asset, rows) in enumerate(ex.map(fetch, todo), 1):
            with c:
                c.executemany("insert or ignore into prices values(?,?,?)", [(asset, t, pr) for t, pr in rows])
                c.execute("insert or ignore into prices_done values(?)", (asset,))
            if i % 100 == 0:
                print(f"  цены: {i}/{len(todo)}", flush=True)
    timing_report(c, a)


def timing_report(c, a):
    hist = {}
    for asset, t, pr in c.execute("select asset, t, p from prices order by asset, t"):
        hist.setdefault(asset, []).append((t, pr))
    per = {}
    for w, asset, ts, price, usd, final, title, grp in c.execute("select * from buys"):
        h = hist.get(asset)
        if not h or ts < h[0][0]:
            continue
        end = h[-1][0]
        moves = []
        for _, dt in HORIZONS:
            px = price_at(h, ts + dt, final)
            moves.append(None if px is None else px - price)
        per.setdefault((grp, w), []).append(dict(ts=ts, price=price, usd=usd, final=final, title=title,
                                                  hrs_left=(end - ts) / 3600, moves=moves))

    def agg(trades):
        out = {}
        for k, (name, _) in enumerate(HORIZONS):
            xs = [t["moves"][k] for t in trades if t["moves"][k] is not None]
            out[name] = (sum(xs) / len(xs), math.sqrt(sum((x - sum(xs) / len(xs)) ** 2 for x in xs) / max(len(xs) - 1, 1)), len(xs)) if xs else (0, 0, 0)
        jumps = [t for t in trades if t["moves"][2] is not None and t["moves"][2] >= a.jump]
        out["скачок"] = len(jumps) / len(trades) if trades else 0
        hl = sorted(t["hrs_left"] for t in trades)
        out["часов_до_конца"] = hl[len(hl) // 2] if hl else 0
        return out

    base_trades = [t for (g, _), v in per.items() if g == "контроль" for t in v]
    if not base_trades:
        print("нет контрольных сделок"); return
    B = agg(base_trades)
    names = [n for n, _ in HORIZONS]
    print(f"\nДвижение цены ПОСЛЕ покупки (в пользу ставки, пункты вероятности); скачок = +{a.jump:.2f} за 6ч")
    print(f"{'кто':22} {'сделок':>6} " + " ".join(f"{n:>7}" for n in names) + f" {'скачок':>7} {'ч до конца':>10}  z(1ч vs контроль)")
    print(f"{'КОНТРОЛЬ (все)':22} {len(base_trades):6} " + " ".join(f"{B[n][0]:+7.3f}" for n in names)
          + f" {B['скачок']:7.1%} {B['часов_до_конца']:10.0f}")
    rows = []
    for (g, w), v in per.items():
        if g != "значимые" or len(v) < 5:
            continue
        A = agg(v)
        m, sd, n = A["1ч"]
        z = (m - B["1ч"][0]) / (B["1ч"][1] / math.sqrt(n)) if n and B["1ч"][1] else 0
        name = c.execute("select name from trades where wallet=? limit 1", (w,)).fetchone()
        rows.append((z, w, name[0] if name else "", len(v), A))
    for z, w, name, n, A in sorted(rows, reverse=True):
        print(f"{(name or w)[:22]:22} {n:6} " + " ".join(f"{A[k][0]:+7.3f}" for k in names)
              + f" {A['скачок']:7.1%} {A['часов_до_конца']:10.0f}  {z:+.1f}")
    out = DB.parent / f"timing_{a.category}.json"
    out.write_text(json.dumps({f"{g}|{w}": v for (g, w), v in per.items()}, ensure_ascii=False))
    print("сделки по кошелькам:", out)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("trades"); s.add_argument("--min-usd", type=float, default=2000)
    s = sub.add_parser("positions")
    s.add_argument("--min-usd", type=float, default=5000, help="кандидат, если была сделка не меньше")
    s.add_argument("--max-wallets", type=int, default=400)
    s.add_argument("--max-pages", type=int, default=40)
    s.add_argument("--threads", type=int, default=6)
    s = sub.add_parser("analyze")
    s.add_argument("--category", default="all", choices=["all", "news", "sports", "crypto"])
    s.add_argument("--min-n", type=int, default=20)
    s.add_argument("--min-stake", type=float, default=50)
    s.add_argument("--pmin", type=float, default=0.03, help="отбросить почти-гарантированные ставки")
    s.add_argument("--fdr", type=float, default=0.05)
    s.add_argument("--top", type=int, default=25)
    s.add_argument("--include-sold", action="store_true", help="учитывать и проданные до исхода позиции")
    s = sub.add_parser("timing")
    s.add_argument("--category", default="news", choices=["all", "news", "sports", "crypto"])
    s.add_argument("--baseline", type=int, default=25, help="контрольных кошельков")
    s.add_argument("--per-wallet", type=int, default=40, help="крупнейших позиций на кошелёк")
    s.add_argument("--min-stake", type=float, default=200)
    s.add_argument("--pmin", type=float, default=0.03)
    s.add_argument("--jump", type=float, default=0.25)
    s.add_argument("--threads", type=int, default=6)
    s.add_argument("--report-only", action="store_true")
    a = ap.parse_args()
    if a.cmd == "timing" and a.report_only:
        return timing_report(db(), a)
    {"trades": cmd_trades, "positions": cmd_positions, "analyze": cmd_analyze, "timing": cmd_timing}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
