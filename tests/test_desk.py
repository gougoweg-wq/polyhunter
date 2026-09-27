import sqlite3
import time
from polyhunter.desk import desk_stats


def test_desk_stats_reads_polydesk_ledger(tmp_path):
    db = tmp_path / "pd.db"
    c = sqlite3.connect(db)
    c.executescript("""create table markets(slug text primary key, start_ts int, end_ts int, outcome text, up real,
        down real, spent real, fees real, payout real, pnl real, ref real, final real, settled_at real);
        create table fills(id integer primary key, ts real, slug text, side text, price real, shares real, fee real,
        kind text, note text);
        create table equity(ts real primary key, cash real, open_value real, equity real);""")
    c.execute("insert into markets values('btc-updown-5m-100',100,400,'Up',10,0,5,0,10,5,0,0,500)")
    c.execute("insert into markets values('btc-updown-5m-400',400,700,'Down',10,0,5,0,0,-5,0,0,800)")
    c.execute("insert into fills values(1,?,'x','Up',0.5,10,0,'take','')", (time.time(),))
    c.execute("insert into equity values(1,995,10,1005)")
    c.commit()
    d = desk_stats(db, start=1000)
    assert d["equity"] == 1005 and d["realized"] == 0 and d["markets"] == 2 and d["won"] == 1
    assert d["fills_24h"] == 1 and d["last"][0]["slug"] == "btc-updown-5m-400"
    assert desk_stats(tmp_path / "missing.db") is None
