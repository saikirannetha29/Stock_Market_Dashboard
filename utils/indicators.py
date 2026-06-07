"""
indicators.py
-------------
Computes all technical indicators in-place on a stock DataFrame.

Every function:
  - Accepts a pd.DataFrame that must contain at least a 'Close' column.
  - Appends one or more new columns to that DataFrame.
  - Returns the modified DataFrame so calls can be chained.

apply_all_indicators() is the single entry-point used by app.py.
"""

import pandas as pd
import numpy as np


# ── Trend Indicators ──────────────────────────────────────────────────────────

def add_sma(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """
    Simple Moving Average — arithmetic mean of Close over the last `window` bars.
    Column added: SMA_{window}
    """
    df[f"SMA_{window}"] = df["Close"].rolling(window=window).mean()
    return df


def add_ema(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """
    Exponential Moving Average — gives exponentially more weight to recent prices.
    Column added: EMA_{window}
    """
    df[f"EMA_{window}"] = df["Close"].ewm(span=window, adjust=False).mean()
    return df


def add_bollinger_bands(df: pd.DataFrame, window: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    """
    Bollinger Bands — volatility envelope around a moving average.
    Upper / Lower bands widen when volatility is high, narrow when low.
    Columns added: BB_Middle, BB_Upper, BB_Lower
    """
    sma = df["Close"].rolling(window=window).mean()
    std = df["Close"].rolling(window=window).std()
    df["BB_Middle"] = sma
    df["BB_Upper"]  = sma + num_std * std
    df["BB_Lower"]  = sma - num_std * std
    return df


# ── Momentum Indicators ───────────────────────────────────────────────────────

def add_rsi(df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    """
    Relative Strength Index (0–100 scale).
      RSI > 70  → potentially overbought (consider selling)
      RSI < 30  → potentially oversold  (consider buying)

    Uses Wilder's smoothing (EWM with com = window - 1).
    Column added: RSI
    """
    delta    = df["Close"].diff()
    gain     = delta.clip(lower=0)
    loss     = (-delta).clip(lower=0)
    avg_gain = gain.ewm(com=window - 1, min_periods=window).mean()
    avg_loss = loss.ewm(com=window - 1, min_periods=window).mean()
    rs       = avg_gain / avg_loss.replace(0, float("nan"))  # avoid div-by-zero
    df["RSI"] = 100.0 - (100.0 / (1.0 + rs))
    return df


def add_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """
    MACD (Moving Average Convergence Divergence).
      MACD Line  = EMA(fast) − EMA(slow)
      Signal     = EMA(MACD Line, signal periods)
      Histogram  = MACD − Signal
    Columns added: MACD, Signal, MACD_Hist
    """
    ema_fast        = df["Close"].ewm(span=fast,   adjust=False).mean()
    ema_slow        = df["Close"].ewm(span=slow,   adjust=False).mean()
    df["MACD"]      = ema_fast - ema_slow
    df["Signal"]    = df["MACD"].ewm(span=signal, adjust=False).mean()
    df["MACD_Hist"] = df["MACD"] - df["Signal"]
    return df


# ── Return / Risk Indicators ──────────────────────────────────────────────────

def add_daily_returns(df: pd.DataFrame) -> pd.DataFrame:
    """Percentage change in Close price day-over-day. Column added: Daily_Return"""
    df["Daily_Return"] = df["Close"].pct_change() * 100
    return df


def add_cumulative_returns(df: pd.DataFrame) -> pd.DataFrame:
    """Cumulative compounded return from the first bar. Column added: Cumulative_Return"""
    df["Cumulative_Return"] = (1 + df["Close"].pct_change()).cumprod() - 1
    return df


def add_volatility(df: pd.DataFrame, window: int = 21) -> pd.DataFrame:
    """
    Rolling annualised volatility = std(daily_returns) × √252 × 100.
    Uses a 21-bar (≈ 1 trading month) rolling window by default.
    Column added: Volatility
    """
    daily = df["Close"].pct_change()
    df["Volatility"] = daily.rolling(window=window).std() * np.sqrt(252) * 100
    return df


# ── Convenience wrapper ───────────────────────────────────────────────────────

def apply_all_indicators(df: pd.DataFrame,
                          sma_window: int = 20,
                          ema_window: int = 20) -> pd.DataFrame:
    """
    Apply every indicator to the DataFrame in one call.
    This is the function imported and used by app.py after fetching data.
    """
    df = add_sma(df, sma_window)
    df = add_ema(df, ema_window)
    df = add_rsi(df)
    df = add_macd(df)
    df = add_bollinger_bands(df)
    df = add_daily_returns(df)
    df = add_cumulative_returns(df)
    df = add_volatility(df)
    return df
