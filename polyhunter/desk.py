"""Сводка polydesk для бота: база открывается только на чтение."""
import sqlite3
import time
from pathlib import Path


def desk_stats(db_path, start=1000.0):
    p = Path(db_path)
    if not p.exists():
        return None
    try:
        c = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=5)
        n, pnl, won = c.execute("select count(*), coalesce(sum(pnl),0), sum(pnl>0) from markets where pnl is not null").fetchone()
        eq = c.execute("select equity from equity order by ts desc limit 1").fetchone()
        f24 = c.execute("select count(*) from fills where kind in ('take','make') and ts > ?", (time.time() - 86400,)).fetchone()[0]
        try:     # доход на $ по каждому рынку — для живой статистики; у старых баз колонок может не быть
            returns = [r[0] / r[1] for r in c.execute(
                "select pnl, spent + coalesce(fees, 0) from markets where pnl is not null and spent > 0")]
        except sqlite3.Error:
            returns = []
        last = [dict(slug=s, pnl=v) for s, v in c.execute(
            "select slug, pnl from markets where pnl is not null order by start_ts desc limit 5")]
        c.close()
    except sqlite3.Error:
        return None
    return dict(equity=eq[0] if eq else start + pnl, realized=pnl, markets=n, won=won or 0, fills_24h=f24,
                start=start, last=last, returns=returns)


DESK_STATE_URL = "https://raw.githubusercontent.com/gougoweg-wq/polydesk/state/polydesk.db.gz"


async def download_desk(http, url, dest):
    """Облако: журнал polydesk лежит в ветке state его репозитория — скачиваем сжатую копию."""
    import gzip
    r = await http.get(url, timeout=60)
    if r.status_code != 200:
        return False
    tmp = Path(str(dest) + ".tmp")
    tmp.write_bytes(gzip.decompress(r.content))
    tmp.replace(dest)
    return True
