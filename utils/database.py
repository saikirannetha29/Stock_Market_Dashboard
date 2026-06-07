"""
database.py
-----------
Handles all SQLite database operations:
- Creating tables on first run
- Saving and retrieving search history
- Watchlist management (add / remove / list)
- Portfolio tracking (add / remove / list positions)
"""

import sqlite3
import os
from datetime import datetime

# Path resolves to  Stock_Market_Dashboard/database/stock.db
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'stock.db')


def get_connection() -> sqlite3.Connection:
    """Open and return a connection to the SQLite database."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)


def initialize_database() -> None:
    """Create all tables if they do not already exist. Called once at startup."""
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS search_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker      TEXT    NOT NULL,
            searched_at TEXT    NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS watchlist (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker   TEXT    UNIQUE NOT NULL,
            added_at TEXT    NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS portfolio (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker    TEXT    NOT NULL,
            shares    REAL    NOT NULL,
            buy_price REAL    NOT NULL,
            added_at  TEXT    NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# ── Search History ────────────────────────────────────────────────────────────

def save_search(ticker: str) -> None:
    """Log every ticker lookup with a timestamp."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO search_history (ticker, searched_at) VALUES (?, ?)",
        (ticker.upper(), datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()


def get_recent_searches(limit: int = 10) -> list:
    """Return the most recent `limit` search records as (ticker, timestamp) tuples."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT ticker, searched_at FROM search_history ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return rows


def clear_search_history() -> None:
    """Delete every row in search_history."""
    conn = get_connection()
    conn.execute("DELETE FROM search_history")
    conn.commit()
    conn.close()


# ── Watchlist ─────────────────────────────────────────────────────────────────

def add_to_watchlist(ticker: str) -> None:
    """Insert ticker into watchlist; silently ignore if it already exists."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO watchlist (ticker, added_at) VALUES (?, ?)",
            (ticker.upper(), datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass   # UNIQUE constraint — already on watchlist
    finally:
        conn.close()


def get_watchlist() -> list:
    """Return all watchlist entries as (ticker, added_at) tuples."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT ticker, added_at FROM watchlist ORDER BY added_at DESC"
    ).fetchall()
    conn.close()
    return rows


def remove_from_watchlist(ticker: str) -> None:
    """Delete a ticker from the watchlist."""
    conn = get_connection()
    conn.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker.upper(),))
    conn.commit()
    conn.close()


# ── Portfolio ─────────────────────────────────────────────────────────────────

def add_to_portfolio(ticker: str, shares: float, buy_price: float) -> None:
    """Insert a new position into the portfolio table."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO portfolio (ticker, shares, buy_price, added_at) VALUES (?, ?, ?, ?)",
        (ticker.upper(), shares, buy_price, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()


def get_portfolio() -> list:
    """Return all portfolio rows as (id, ticker, shares, buy_price, added_at)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, ticker, shares, buy_price, added_at FROM portfolio ORDER BY added_at DESC"
    ).fetchall()
    conn.close()
    return rows


def remove_from_portfolio(record_id: int) -> None:
    """Delete a portfolio position by its primary key."""
    conn = get_connection()
    conn.execute("DELETE FROM portfolio WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()
