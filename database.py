import os
from contextlib import contextmanager
from datetime import datetime, timezone
import psycopg
from psycopg.rows import dict_row


def db_url():
    value = os.getenv("DATABASE_URL")
    if not value:
        raise RuntimeError("DATABASE_URL belum diatur. Hubungkan PostgreSQL persisten.")
    return value


@contextmanager
def connection():
    with psycopg.connect(db_url(), row_factory=dict_row) as conn:
        yield conn


def init_db():
    with connection() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id BIGSERIAL PRIMARY KEY,
            strategy TEXT NOT NULL,
            side TEXT NOT NULL,
            candle_time TIMESTAMPTZ NOT NULL,
            entry DOUBLE PRECISION NOT NULL,
            stop_loss DOUBLE PRECISION NOT NULL,
            take_profit DOUBLE PRECISION NOT NULL,
            atr DOUBLE PRECISION NOT NULL,
            target_rr DOUBLE PRECISION NOT NULL DEFAULT 2.0,
            status TEXT NOT NULL DEFAULT 'OPEN',
            exit_time TIMESTAMPTZ,
            exit_price DOUBLE PRECISION,
            last_checked_candle TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(strategy, side, candle_time)
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS sent_reports (
            report_key TEXT PRIMARY KEY,
            sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """)


def insert_signal(strategy, side, candle_time, entry, sl, tp, atr, rr):
    with connection() as conn:
        row = conn.execute("""
            INSERT INTO signals
            (strategy, side, candle_time, entry, stop_loss, take_profit, atr, target_rr,
             last_checked_candle)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT(strategy, side, candle_time) DO NOTHING
            RETURNING id
        """, (strategy, side, candle_time, entry, sl, tp, atr, rr, candle_time)).fetchone()
        return row["id"] if row else None


def get_open_positions():
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM signals WHERE status='OPEN' ORDER BY candle_time"
        ).fetchall()
        return [dict(r) for r in rows]


def update_position(signal_id, status, exit_time, exit_price, checked_time, unused=None):
    with connection() as conn:
        if status in ("TP", "SL"):
            conn.execute("""
                UPDATE signals SET status=%s, exit_time=%s, exit_price=%s,
                last_checked_candle=%s WHERE id=%s AND status='OPEN'
            """, (status, exit_time, exit_price, checked_time, signal_id))
        else:
            conn.execute("""
                UPDATE signals SET last_checked_candle=%s
                WHERE id=%s AND status='OPEN'
            """, (checked_time, signal_id))


def get_period_stats(start, end, strategy=None):
    query = """
        SELECT COUNT(*) AS total,
        COUNT(*) FILTER (WHERE status='TP') AS tp,
        COUNT(*) FILTER (WHERE status='SL') AS sl,
        COUNT(*) FILTER (WHERE status='OPEN') AS open,
        COALESCE(COUNT(*) FILTER (WHERE status='TP') * 2.0, 0) AS tp_r
        FROM signals WHERE candle_time >= %s AND candle_time < %s
    """
    params = [start, end]
    if strategy:
        query += " AND strategy=%s"
        params.append(strategy)
    with connection() as conn:
        row = conn.execute(query, params).fetchone()
        return dict(row)


def get_period_positions(start, end):
    with connection() as conn:
        rows = conn.execute("""
            SELECT * FROM signals
            WHERE candle_time >= %s AND candle_time < %s
            ORDER BY candle_time DESC
        """, (start, end)).fetchall()
        return [dict(r) for r in rows]


def get_last_report(key):
    with connection() as conn:
        return conn.execute(
            "SELECT report_key FROM sent_reports WHERE report_key=%s", (key,)
        ).fetchone()


def save_report(key):
    with connection() as conn:
        conn.execute(
            "INSERT INTO sent_reports(report_key) VALUES (%s) ON CONFLICT DO NOTHING",
            (key,)
        )
