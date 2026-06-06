"""
data_loader.py
--------------
All communication with the Yahoo Finance API via yfinance.

Key design decisions
--------------------
- @st.cache_data(ttl=300) caches results for 5 minutes to avoid hammering the API.
- Every function returns an empty DataFrame / empty dict on failure instead of
  raising, so the caller (app.py) can handle errors gracefully in the UI.
- MultiIndex column flattening handles newer yfinance versions that return
  two-level headers like ('Close', 'AAPL').
"""

import yfinance as yf
import pandas as pd
import streamlit as st


@st.cache_data(ttl=300)
def fetch_stock_data(ticker: str, start: str, end: str) -> pd.DataFrame:
    """
    Download historical OHLCV data for a single ticker.

    Parameters
    ----------
    ticker : str   Ticker symbol, e.g. 'AAPL'
    start  : str   ISO date string, e.g. '2023-01-01'
    end    : str   ISO date string, e.g. '2024-01-01'

    Returns
    -------
    pd.DataFrame  Columns: Open, High, Low, Close, Volume
                  Empty DataFrame if ticker is invalid or data unavailable.
    """
    try:
        df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
        if df.empty:
            return pd.DataFrame()

        df.index = pd.to_datetime(df.index)

        # Flatten MultiIndex columns produced by newer yfinance versions
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        return df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()

    except Exception as exc:
        st.error(f"Data fetch failed for '{ticker}': {exc}")
        return pd.DataFrame()


@st.cache_data(ttl=60)
def fetch_stock_info(ticker: str) -> dict:
    """
    Return key metadata for a ticker: name, sector, price, 52-week range, etc.
    Returns an empty dict on failure.
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
    Fetch the Close price series for each ticker in the list.

    Returns
    -------
    dict  {ticker_string: pd.Series of Close prices}
    Only includes tickers for which data was successfully retrieved.
    """
    result = {}
    for t in tickers:
        df = fetch_stock_data(t, start, end)
        if not df.empty:
            result[t] = df["Close"]
    return result


def get_top_movers() -> tuple[list, list]:
    """
    Return two hard-coded lists of popular US tickers used in the
    'Top Gainers / Losers' section on the Overview page.
    In a production app this would call a paid market-data API.
    """
    gainers = ["NVDA", "META", "TSLA", "AMZN", "GOOGL"]
    losers  = ["INTC", "PFE",  "BA",   "DIS",  "NKE"]
    return gainers, losers


def validate_ticker(ticker: str) -> bool:
    """Return True if Yahoo Finance recognises this ticker and returns a price."""
    try:
        info = yf.Ticker(ticker).info
        return bool(info.get("regularMarketPrice") or info.get("currentPrice"))
    except Exception:
        return False
