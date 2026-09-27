"""SQLite-хранилище бота: пользователи, подписки, рейтинг, увиденные сделки, журнал сигналов."""
import json
import sqlite3
import threading
import time

ALERT_TYPES = ("smart", "fresh", "cluster", "fade", "follow", "ai", "news")
DEFAULT_ALERTS = {"smart": True, "fresh": True, "cluster": True, "fade": False, "follow": True, "ai": False,
                  "news": True}
SCORE_COLS = ("wallet", "name", "tier", "score", "post_edge", "edge", "q", "n", "events", "wins", "exp",
              "roi", "pnl", "stake", "best_category", "timing6h")


class Store:
    def __init__(self, path):
        self.c = sqlite3.connect(path, timeout=60, check_same_thread=False)
        self.c.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        with self.lock, self.c:
            self.c.executescript("""
            create table if not exists users(chat_id integer primary key, lang text, threshold real,
              alerts text, created integer);
            create table if not exists follows(chat_id integer, wallet text, primary key(chat_id, wallet));
            create table if not exists scores(cat text, wallet text, name text, tier text, score integer,
              post_edge real, edge real, q real, n integer, events integer, wins integer, exp real, roi real,
              pnl real, stake real, best_category text, timing6h real, updated integer,
              primary key(cat, wallet));
            create index if not exists scores_rank on scores(cat, score desc);
            create table if not exists seen(k text primary key, at integer);
            create table if not exists signals(id integer primary key autoincrement, kind text, text text, ts integer);
            create table if not exists wallet_hist(wallet text primary key, n integer, at integer);
            create table if not exists meta(k text primary key, v text);
            create table if not exists paper_accounts(owner text primary key, cash real, start real, created integer);
            create table if not exists paper_positions(owner text, asset text, condition_id text, outcome text,
              title text, slug text, event_slug text, shares real, cost real, opened integer, source text,
              primary key(owner, asset));
            create table if not exists paper_trades(id integer primary key autoincrement, owner text, ts integer,
              asset text, side text, shares real, price real, usd real, pnl real, source text, title text, outcome text);
            create index if not exists paper_trades_owner on paper_trades(owner, id desc);
            create table if not exists copies(chat_id integer, leader text, usd real, since integer,
              primary key(chat_id, leader));
            create table if not exists quick(id integer primary key autoincrement, payload text, created integer);
            """)

    # ------------------------------------------------------------ users
    def user(self, chat_id, lang=None):
        with self.lock:
            r = self.c.execute("select * from users where chat_id=?", (chat_id,)).fetchone()
            if not r:
                with self.c:
                    self.c.execute("insert into users values(?,?,?,?,?)",
                                   (chat_id, lang or "en", 5000, json.dumps(DEFAULT_ALERTS), int(time.time())))
                r = self.c.execute("select * from users where chat_id=?", (chat_id,)).fetchone()
            elif lang and r["lang"] != lang:
                with self.c:
                    self.c.execute("update users set lang=? where chat_id=?", (lang, chat_id))
                r = self.c.execute("select * from users where chat_id=?", (chat_id,)).fetchone()
        alerts = dict(DEFAULT_ALERTS, **json.loads(r["alerts"] or "{}"))
        return dict(chat_id=r["chat_id"], lang=r["lang"], threshold=r["threshold"], alerts=alerts)

    def users(self):
        with self.lock:
            ids = [r[0] for r in self.c.execute("select chat_id from users")]
        return [self.user(i) for i in ids]

    def toggle_alert(self, chat_id, kind):
        u = self.user(chat_id)
        u["alerts"][kind] = not u["alerts"].get(kind, False)
        with self.lock, self.c:
            self.c.execute("update users set alerts=? where chat_id=?", (json.dumps(u["alerts"]), chat_id))
        return u["alerts"][kind]

    def set_threshold(self, chat_id, usd):
        self.user(chat_id)
        with self.lock, self.c:
            self.c.execute("update users set threshold=? where chat_id=?", (float(usd), chat_id))

    # ------------------------------------------------------------ follows
    def follow(self, chat_id, wallet):
        with self.lock, self.c:
            self.c.execute("insert or ignore into follows values(?,?)", (chat_id, wallet.lower()))

    def unfollow(self, chat_id, wallet):
        with self.lock, self.c:
            self.c.execute("delete from follows where chat_id=? and wallet=?", (chat_id, wallet.lower()))

    def following(self, chat_id):
        with self.lock:
            return [r[0] for r in self.c.execute("select wallet from follows where chat_id=? order by wallet", (chat_id,))]

    def followers(self, wallet):
        with self.lock:
            return [r[0] for r in self.c.execute("select chat_id from follows where wallet=?", (wallet.lower(),))]

    def followed_wallets(self):
        with self.lock:
            return {r[0] for r in self.c.execute("select distinct wallet from follows")}

    # ------------------------------------------------------------ scores
    def save_scores(self, cat, rows):
        now = int(time.time())
        with self.lock, self.c:
            self.c.execute("delete from scores where cat=?", (cat,))
            self.c.executemany(
                f"insert into scores values(?,{','.join('?' * len(SCORE_COLS))},?)",
                [(cat, *[r.get(k) for k in SCORE_COLS], now) for r in rows])

    def upsert_score(self, cat, r):
        with self.lock, self.c:
            self.c.execute(f"insert or replace into scores values(?,{','.join('?' * len(SCORE_COLS))},?)",
                           (cat, *[r.get(k) for k in SCORE_COLS], int(time.time())))

    def _rows(self, sql, args):
        with self.lock:
            return [dict(r) for r in self.c.execute(sql, args)]

    def top(self, cat, limit=10, tiers=("S", "A", "B")):
        q = ",".join("?" * len(tiers))
        return self._rows(f"select * from scores where cat=? and tier in ({q}) "
                          f"order by case tier when 'S' then 0 when 'A' then 1 else 2 end, score desc, pnl desc limit ?",
                          (cat, *tiers, limit))

    def score(self, wallet, cat="all"):
        r = self._rows("select * from scores where cat=? and wallet=?", (cat, wallet.lower()))
        return r[0] if r else None

    def scores_map(self, cat="all"):
        return {r["wallet"]: r for r in self._rows("select * from scores where cat=?", (cat,))}

    def tier_counts(self, cat="all"):
        return {r["tier"]: r["n"] for r in self._rows("select tier, count(*) n from scores where cat=? group by tier", (cat,))}

    def find_wallet(self, query):
        q = (query or "").strip()
        if q.lower().startswith("0x"):
            ql = q.lower()
            if len(ql) == 42:
                return ql
            r = self._rows("select wallet from scores where wallet like ? limit 1", (ql + "%",))
            return r[0]["wallet"] if r else None
        r = self._rows("select wallet from scores where lower(name)=lower(?) limit 1", (q,))
        return r[0]["wallet"] if r else None

    # ------------------------------------------------------------ radar state
    def mark_seen(self, key):
        k = "|".join(map(str, key))
        with self.lock, self.c:
            cur = self.c.execute("insert or ignore into seen values(?,?)", (k, int(time.time())))
            return cur.rowcount == 1

    def prune_seen(self, older_than=3 * 86400):
        with self.lock, self.c:
            self.c.execute("delete from seen where at < ?", (int(time.time()) - older_than,))

    def log_signal(self, kind, text, ts):
        with self.lock, self.c:
            self.c.execute("insert into signals(kind, text, ts) values(?,?,?)", (kind, text, int(ts)))

    def recent_signals(self, limit=10):
        return self._rows("select kind, text, ts from signals order by id desc limit ?", (limit,))

    def wallet_history(self, wallet, max_age=6 * 3600):
        r = self._rows("select n, at from wallet_hist where wallet=?", (wallet,))
        if r and time.time() - r[0]["at"] < max_age:
            return r[0]["n"]
        return None

    def set_wallet_history(self, wallet, n):
        with self.lock, self.c:
            self.c.execute("insert or replace into wallet_hist values(?,?,?)", (wallet, n, int(time.time())))

    def set_meta(self, k, v):
        with self.lock, self.c:
            self.c.execute("insert or replace into meta values(?,?)", (k, json.dumps(v)))

    def meta(self, k, default=None):
        with self.lock:
            r = self.c.execute("select v from meta where k=?", (k,)).fetchone()
        return json.loads(r[0]) if r else default

    # ------------------------------------------------------------ копирование
    def set_copy(self, chat_id, leader, usd):
        with self.lock, self.c:
            self.c.execute("insert or replace into copies values(?,?,?,?)",
                           (chat_id, leader.lower(), float(usd), int(time.time())))

    def remove_copy(self, chat_id, leader):
        with self.lock, self.c:
            self.c.execute("delete from copies where chat_id=? and leader=?", (chat_id, leader.lower()))

    def copies_of(self, chat_id):
        with self.lock:
            return [(r[0], r[1]) for r in self.c.execute("select leader, usd from copies where chat_id=? order by leader", (chat_id,))]

    def copiers(self, leader):
        with self.lock:
            return [(r[0], r[1]) for r in self.c.execute("select chat_id, usd from copies where leader=?", (leader.lower(),))]

    def copy_leaders(self):
        with self.lock:
            return [r[0] for r in self.c.execute("select distinct leader from copies")]

    # ------------------------------------------------------------ быстрые действия кнопок
    def put_quick(self, payload):
        with self.lock, self.c:
            cur = self.c.execute("insert into quick(payload, created) values(?,?)", (json.dumps(payload), int(time.time())))
            return cur.lastrowid

    def get_quick(self, qid):
        with self.lock:
            r = self.c.execute("select payload from quick where id=?", (int(qid),)).fetchone()
        return json.loads(r[0]) if r else None
