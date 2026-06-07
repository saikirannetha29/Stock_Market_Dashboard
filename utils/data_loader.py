"""
data_loader.py  (v3 - cookie-safe)
-----------------------------------
Uses yf.Ticker().history() instead of yf.download().
yf.Ticker().history() handles Cloudflare/cookie auth automatically
and is more reliable when Yahoo Finance blocks yf.download().
"""

import yfinance as yf
import pandas as pd
import streamlit as st
from datetime import datetime


@st.cache_data(ttl=300)
def fetch_stock_data(ticker: str, start: str, end: str) -> pd.DataFrame:
    """
    Fetch OHLCV data using yf.Ticker().history() — more reliable than yf.download().

    Returns
    -------
    pd.DataFrame with columns: Open, High, Low, Close, Volume
    Empty DataFrame on failure.
    """
    try:
        t  = yf.Ticker(ticker)
        df = t.history(start=start, end=end, auto_adjust=True)

        if df.empty:
            return pd.DataFrame()

        df.index = pd.to_datetime(df.index)

        # history() returns timezone-aware index — strip tz for clean plotting
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)

        # Keep only standard OHLCV columns
        cols = [c for c in ['Open', 'High', 'Low', 'Close', 'Volume'] if c in df.columns]
        if len(cols) < 5:
            return pd.DataFrame()

        return df[cols].dropna()

    except Exception as exc:
        st.error(f"❌ Could not fetch **{ticker}**: {exc}")
        return pd.DataFrame()


@st.cache_data(ttl=60)
def fetch_stock_info(ticker: str) -> dict:
    """
    Fetch key metadata using yf.Ticker().info.
    Returns empty dict on failure — UI handles gracefully.
    """
    try:
        info = yf.Ticker(ticker).info
        return {
            "name":           info.get("longName", ticker),
            "sector":         info.get("sector", "N/A"),
            "market_cap":     info.get("marketCap", 0),
            "current_price":  info.get("currentPrice") or info.get("regularMarketPrice", 0),
            "previous_close": info.get("previousClose", 0),
            "week_52_high":   info.get("fiftyTwoWeekHigh", 0),
            "week_52_low":    info.get("fiftyTwoWeekLow", 0),
            "pe_ratio":       info.get("trailingPE", 0),
            "dividend_yield": info.get("dividendYield", 0),
        }
    except Exception:
        return {}


@st.cache_data(ttl=300)
def fetch_multiple_stocks(tickers: list, start: str, end: str) -> dict:
    """
    Returns {ticker: pd.Series of Close prices} for every valid ticker.
    """
    result = {}
    for t in tickers:
        df = fetch_stock_data(t, start, end)
        if not df.empty:
            result[t] = df["Close"]
    return result


def get_top_movers() -> tuple:
    """Popular tickers shown in the Overview page banner."""
    gainers = ["NVDA", "META", "TSLA", "AMZN", "GOOGL"]
    losers  = ["INTC", "PFE",  "BA",   "DIS",  "NKE"]
    return gainers, losers


def validate_ticker(ticker: str) -> bool:
    """Return True if ticker is recognised by Yahoo Finance."""
    try:
        info = yf.Ticker(ticker).info
        return bool(info.get("regularMarketPrice") or info.get("currentPrice"))
    except Exception:
        return False
