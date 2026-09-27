"""Движок радара: новые сделки → сигналы → получатели. Сеть подаётся снаружи (history_fn)."""
import json

from . import radar
from .classify import category


class RadarEngine:
    def __init__(self, store, history_fn, smart_min=1000, fresh_min=5000, cluster_window=600,
                 cluster_wallets=3, cluster_usd=20000, busy_wallets=4, busy_usd=75000):
        self.store = store
        self.history_fn = history_fn          # async (wallet, condition_id) -> число других рынков
        self.smart_min = smart_min
        self.fresh_min = fresh_min
        self.cluster_window = cluster_window
        self.cluster_wallets = cluster_wallets
        self.cluster_usd = cluster_usd
        self.busy_wallets = busy_wallets      # спорт и крипта: много денег всегда, нужен порог выше
        self.busy_usd = busy_usd
        self.recent = []
        self.refresh()

    def refresh(self):
        self.scores = self.store.scores_map("all")
        self.followed = self.store.followed_wallets()

    def _recipients(self, kind, usd, only=None):
        out = []
        for u in self.store.users():
            if only is not None and u["chat_id"] not in only:
                continue
            if u["alerts"].get(kind) and usd >= u["threshold"]:
                out.append(u["chat_id"])
        return out

    def _emit(self, signals, kind, to, **payload):
        if not to:
            return
        sig = dict(kind=kind, to=sorted(to), **payload)
        signals.append(sig)
        ts = (payload.get("trade") or payload.get("cluster") or {}).get("ts") or \
             (payload.get("cluster") or {}).get("last_ts", 0)
        self.store.log_signal(kind, json.dumps({k: v for k, v in sig.items() if k != "to"}, ensure_ascii=False), ts)

    async def step(self, trades):
        signals = []
        self.followed = self.store.followed_wallets()
        fresh_trades = []
        for t in sorted(trades, key=lambda x: x["ts"]):
            if not self.store.mark_seen(radar.trade_key(t)):
                continue
            fresh_trades.append(t)
            if t["side"] != "BUY":
                continue
            score = self.scores.get(t["wallet"])
            kind = radar.signal_kind(t, score, min_usd=self.smart_min)
            sent_to = set()
            if kind:
                to = self._recipients(kind, t["usd"])
                self._emit(signals, kind, to, trade=t, score=score)
                sent_to.update(to)
            if t["wallet"] in self.followed:
                followers = set(self.store.followers(t["wallet"])) - sent_to
                to = self._recipients("follow", t["usd"], only=followers)
                self._emit(signals, "follow", to, trade=t, score=score)
            if (score is None and t["usd"] >= self.fresh_min and t["price"] <= 0.35
                    and category(t["title"], t["slug"]) == "news"):
                hist = self.store.wallet_history(t["wallet"])
                if hist is None:
                    hist = await self.history_fn(t["wallet"], t["condition_id"])
                    self.store.set_wallet_history(t["wallet"], hist)
                if radar.is_fresh_whale(t, hist, min_usd=self.fresh_min):
                    self._emit(signals, "fresh", self._recipients("fresh", t["usd"]), trade=t, score=None,
                               history_n=hist)
        # кластеры по окну последних сделок
        self.recent.extend(fresh_trades)
        if self.recent:
            last = max(x["ts"] for x in self.recent)
            self.recent = [x for x in self.recent if x["ts"] >= last - 3 * self.cluster_window]
        for c in radar.clusters(self.recent, self.cluster_window, self.cluster_wallets, self.cluster_usd):
            if category(c["title"], c["slug"]) != "news" and (c["wallets"] < self.busy_wallets
                                                              or c["usd"] < self.busy_usd):
                continue
            if self.store.mark_seen(("cluster", c["asset"], c["first_ts"] // 1800)):
                self._emit(signals, "cluster", self._recipients("cluster", c["usd"]), cluster=c)
        return signals
