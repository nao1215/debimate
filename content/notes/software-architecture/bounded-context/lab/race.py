"""値引きの判定に使う税抜きの合計と、税込みの合計を、同じ列に書くか別の列に書くかで比べる。

Saleor の PR #19801 の仕組みを、SQLite と 2 つのスレッドで小さく真似たもの（Saleor のコードではない）。
python3 race.py で、3 つの場面 × 2 つの設計を実行し、各場面の最後の値と、出来事の時刻を出す。
"""
import json
import sqlite3
import sys
import tempfile
import threading
import time
from pathlib import Path

SUBTOTAL, SHIPPING, TAX_RATE = 70, 10, 0.10  # 税抜きの小計・送料、税率 10%
TAX_CALL = 2.0     # 税の計算を外部のアプリに頼む時間（秒）
EDIT_AT = 1.0      # 別の処理が注文を触る時刻（秒）


def connect(path):
    db = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
    db.execute("PRAGMA journal_mode=WAL")
    return db


def setup(path):
    db = connect(path)
    db.execute("""CREATE TABLE orders (id INTEGER PRIMARY KEY, total INTEGER, base_total INTEGER,
                  note TEXT, updated_at INTEGER, should_refresh INTEGER, status TEXT)""")
    # 前回の計算で税込みの合計 88 が入っている下書きの注文
    db.execute("INSERT INTO orders VALUES (1, 88, 0, '', 1, 0, 'draft')")
    return db


def recalculate(db, shared, log, crash=False):
    """値引きの判定 → 税の計算 → 保存。保存の前に、他の処理が注文を変えていないかを見る。"""
    (seen,) = db.execute("SELECT updated_at FROM orders WHERE id=1").fetchone()
    base = SUBTOTAL + SHIPPING  # 80（税抜き）
    # 1. 値引きの条件を SQL で判定するので、税抜きの合計を先に DB へ書く
    col = "total" if shared else "base_total"
    db.execute(f"UPDATE orders SET {col}=? WHERE id=1", (base,))
    log("値引きの判定用に税抜きの合計を書く")
    db.execute(f"SELECT count(*) FROM orders WHERE id=1 AND {col} >= 75").fetchone()
    # 2. 税の計算（外部のアプリへの問い合わせ）
    log("税の計算を始める")
    time.sleep(TAX_CALL)
    if crash:
        log("税の計算の途中で処理が落ちる")
        raise RuntimeError("tax app timeout")
    taxed = round(base * (1 + TAX_RATE))  # 88
    # 3. 計算の間に他の処理が注文を変えていたら、古い計算で上書きしないよう保存をやめる
    (now,) = db.execute("SELECT updated_at FROM orders WHERE id=1").fetchone()
    if now != seen:
        if not shared:
            db.execute("UPDATE orders SET should_refresh=1 WHERE id=1")
        log("他の処理が注文を変えていたので、税込みの合計の保存をやめる")
        return
    db.execute("UPDATE orders SET total=? WHERE id=1", (taxed,))
    log("税込みの合計を保存する")


def edit(db, log):
    time.sleep(EDIT_AT)
    db.execute("UPDATE orders SET note='置き配', updated_at=updated_at+1 WHERE id=1")
    log("別の処理が注文の備考を変える")


def complete(db, shared, log):
    total, refresh = db.execute("SELECT total, should_refresh FROM orders WHERE id=1").fetchone()
    if not shared and refresh:
        log("保存されていない計算があるので、確定を拒否する")
        return None
    db.execute("UPDATE orders SET status='completed' WHERE id=1")
    log(f"注文を確定する（total={total}）")
    return total


def run(scene, shared, workdir):
    path = Path(workdir) / f"{scene}_{'shared' if shared else 'split'}.db"
    db = setup(path)
    t0 = time.perf_counter()
    events = []
    lock = threading.Lock()

    def log(what):
        with lock:
            t = time.perf_counter() - t0
            total, base = connect(path).execute("SELECT total, base_total FROM orders WHERE id=1").fetchone()
            events.append({"t": round(t, 3), "what": what, "total": total, "base_total": base})

    other = threading.Thread(target=edit, args=(connect(path), log)) if scene == "edit" else None
    if other:
        other.start()
    try:
        recalculate(connect(path), shared, log, crash=(scene == "crash"))
    except RuntimeError:
        pass
    if other:
        other.join()
    done = complete(db, shared, log)
    return {"scene": scene, "design": "shared" if shared else "split", "completed_total": done, "events": events}


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
        results = [run(s, sh, d) for s in ("normal", "edit", "crash") for sh in (True, False)]
    for r in results:
        print(f"{r['scene']:6} {r['design']:6} 確定した合計: {r['completed_total']}")
        for e in r["events"]:
            print(f"    {e['t']:6.3f}s  total={e['total']:>3} base_total={e['base_total']:>3}  {e['what']}")
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(results, ensure_ascii=False, indent=1))
