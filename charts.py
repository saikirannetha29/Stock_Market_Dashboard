"""
charts.py
---------
All Plotly chart builder functions.

Design rules
------------
- Every function receives a pd.DataFrame (and possibly extra params).
- Every function returns a plotly.graph_objects.Figure.
- No Streamlit calls inside this file — keep it pure visualization logic.
- Template is always "plotly_dark" for consistent dark-mode UI.
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# ── Shared colour palette ─────────────────────────────────────────────────────
C = {
    "price":   "#00B4D8",
    "sma":     "#F77F00",
    "ema":     "#9B5DE5",
    "bb_fill": "rgba(0,180,216,0.08)",
    "up":      "#26A69A",
    "down":    "#EF5350",
    "macd":    "#1565C0",
    "signal":  "#F57F17",
    "rsi":     "#9B5DE5",
    "vol":     "#FF6B6B",
}

TEMPLATE = "plotly_dark"


# ── 1. Candlestick + Volume ───────────────────────────────────────────────────

def candlestick_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    """
    Full OHLCV candlestick chart with a volume bar subplot underneath.
    Volume bars are coloured green on up-days, red on down-days.
    """
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.75, 0.25],
        vertical_spacing=0.03,
    )

    # Candlestick trace
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"], high=df["High"],
        low=df["Low"],   close=df["Close"],
        name="OHLC",
        increasing_line_color=C["up"],
        decreasing_line_color=C["down"],
    ), row=1, col=1)

    # Volume bars coloured by price direction
    bar_colors = [
        C["up"] if c >= o else C["down"]
        for c, o in zip(df["Close"], df["Open"])
    ]
    fig.add_trace(go.Bar(
        x=df.index, y=df["Volume"],
        name="Volume",
        marker_color=bar_colors,
        opacity=0.65,
    ), row=2, col=1)

    fig.update_layout(
        title=f"{ticker} — Candlestick Chart",
        xaxis_rangeslider_visible=False,
        template=TEMPLATE,
        height=600,
        hovermode="x unified",
        legend=dict(orientation="h", y=1.02),
    )
    fig.update_yaxes(title_text="Price (USD)", row=1, col=1)
    fig.update_yaxes(title_text="Volume",      row=2, col=1)
    return fig


# ── 2. Price line + Indicators ────────────────────────────────────────────────

def line_chart_with_indicators(df: pd.DataFrame, ticker: str,
                                show_sma: bool = True,
                                show_ema: bool = True,
                                show_bb:  bool = True) -> go.Figure:
    """Close price line overlaid with optional SMA, EMA, and Bollinger Bands."""
    fig = go.Figure()

    # Bollinger Bands — draw fill first so it sits behind the price line
    if show_bb and "BB_Upper" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["BB_Upper"],
            line=dict(color="rgba(0,180,216,0.35)", width=1),
            name="BB Upper", showlegend=True,
        ))
        fig.add_trace(go.Scatter(
            x=df.index, y=df["BB_Lower"],
            fill="tonexty", fillcolor=C["bb_fill"],
            line=dict(color="rgba(0,180,216,0.35)", width=1),
            name="BB Lower",
        ))

    # Close price
    fig.add_trace(go.Scatter(
        x=df.index, y=df["Close"],
        line=dict(color=C["price"], width=2),
        name="Close",
    ))

    # SMA lines
    if show_sma:
        for col in [c for c in df.columns if c.startswith("SMA_")]:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[col],
                line=dict(color=C["sma"], width=1.5, dash="dash"),
                name=col,
            ))

    # EMA lines
    if show_ema:
        for col in [c for c in df.columns if c.startswith("EMA_")]:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[col],
                line=dict(color=C["ema"], width=1.5, dash="dot"),
                name=col,
            ))

    fig.update_layout(
        title=f"{ticker} — Price & Indicators",
        xaxis_title="Date", yaxis_title="Price (USD)",
        template=TEMPLATE, height=500,
        hovermode="x unified",
        legend=dict(orientation="h", y=1.02),
    )
    return fig


# ── 3. RSI ────────────────────────────────────────────────────────────────────

def rsi_chart(df: pd.DataFrame) -> go.Figure:
    """RSI line with overbought (70) and oversold (30) reference bands."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, y=df["RSI"],
        line=dict(color=C["rsi"], width=2),
        name="RSI",
    ))
    # Shaded neutral zone
    fig.add_hrect(y0=30, y1=70, fillcolor="rgba(255,255,255,0.04)", line_width=0)
    fig.add_hline(y=70, line=dict(color=C["down"], dash="dash", width=1),
                  annotation_text="Overbought 70", annotation_position="top right")
    fig.add_hline(y=30, line=dict(color=C["up"],   dash="dash", width=1),
                  annotation_text="Oversold 30",   annotation_position="bottom right")

    fig.update_layout(
        title="RSI (14)",
        xaxis_title="Date", yaxis_title="RSI",
        yaxis=dict(range=[0, 100]),
        template=TEMPLATE, height=300,
    )
    return fig


# ── 4. MACD ───────────────────────────────────────────────────────────────────

def macd_chart(df: pd.DataFrame) -> go.Figure:
    """MACD line, Signal line, and colour-coded histogram."""
    hist_colors = [C["up"] if v >= 0 else C["down"] for v in df["MACD_Hist"].fillna(0)]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df.index, y=df["MACD_Hist"],
        marker_color=hist_colors, opacity=0.6, name="Histogram",
    ))
    fig.add_trace(go.Scatter(
        x=df.index, y=df["MACD"],
        line=dict(color=C["macd"], width=2), name="MACD",
    ))
    fig.add_trace(go.Scatter(
        x=df.index, y=df["Signal"],
        line=dict(color=C["signal"], width=1.5, dash="dash"), name="Signal",
    ))

    fig.update_layout(
        title="MACD (12, 26, 9)",
        xaxis_title="Date", yaxis_title="Value",
        template=TEMPLATE, height=300,
        hovermode="x unified",
        legend=dict(orientation="h", y=1.02),
    )
    return fig


# ── 5. Comparison charts ──────────────────────────────────────────────────────

def comparison_chart(price_data: dict, normalize: bool = True) -> go.Figure:
    """
    Overlay multiple stock Close series on one chart.
    If normalize=True, all series start at 100 for fair comparison.
    """
    fig    = go.Figure()
    colors = px.colors.qualitative.Plotly

    for i, (ticker, series) in enumerate(price_data.items()):
        y = (series / series.iloc[0] * 100) if normalize else series
        fig.add_trace(go.Scatter(
            x=series.index, y=y,
            line=dict(width=2, color=colors[i % len(colors)]),
            name=ticker,
        ))

    fig.update_layout(
        title="Stock Comparison" + (" — Normalised to 100" if normalize else ""),
        xaxis_title="Date",
        yaxis_title="Normalised Price" if normalize else "Price (USD)",
        template=TEMPLATE, height=450,
        hovermode="x unified",
        legend=dict(orientation="h", y=1.02),
    )
    return fig


def performance_bar_chart(price_data: dict) -> go.Figure:
    """Horizontal bar chart showing total % return per ticker over the period."""
    tickers, returns = [], []
    for ticker, series in price_data.items():
        pct = (series.iloc[-1] - series.iloc[0]) / series.iloc[0] * 100
        tickers.append(ticker)
        returns.append(round(pct, 2))

    colors = [C["up"] if r >= 0 else C["down"] for r in returns]
    fig = go.Figure(go.Bar(
        x=tickers, y=returns,
        marker_color=colors,
        text=[f"{r}%" for r in returns],
        textposition="auto",
    ))
    fig.update_layout(
        title="Performance Comparison (%)",
        xaxis_title="Ticker", yaxis_title="Return (%)",
        template=TEMPLATE, height=400,
    )
    return fig


def risk_return_scatter(price_data: dict) -> go.Figure:
    """Scatter: X = annualised volatility, Y = total return. Tickers labelled."""
    tickers, risks, rets = [], [], []
    for ticker, series in price_data.items():
        daily = series.pct_change().dropna()
        tickers.append(ticker)
        risks.append(round(daily.std() * np.sqrt(252) * 100, 2))
        rets.append(round((series.iloc[-1] / series.iloc[0] - 1) * 100, 2))

    fig = go.Figure(go.Scatter(
        x=risks, y=rets,
        mode="markers+text",
        text=tickers, textposition="top center",
        marker=dict(size=16, color=rets, colorscale="RdYlGn", showscale=True,
                    colorbar=dict(title="Return %")),
    ))
    fig.update_layout(
        title="Risk vs Return",
        xaxis_title="Annualised Volatility (%)",
        yaxis_title="Total Return (%)",
        template=TEMPLATE, height=450,
    )
    return fig


# ── 6. Analytics charts ───────────────────────────────────────────────────────

def daily_returns_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    """Bar chart of daily returns, green positive / red negative."""
    ret    = df["Daily_Return"].fillna(0)
    colors = [C["up"] if r >= 0 else C["down"] for r in ret]
    fig = go.Figure(go.Bar(
        x=df.index, y=ret, marker_color=colors, name="Daily Return",
    ))
    fig.update_layout(
        title=f"{ticker} — Daily Returns (%)",
        xaxis_title="Date", yaxis_title="Return (%)",
        template=TEMPLATE, height=350,
    )
    return fig


def cumulative_returns_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    """Area chart of cumulative compounded return over the selected period."""
    fig = go.Figure(go.Scatter(
        x=df.index, y=df["Cumulative_Return"] * 100,
        fill="tozeroy", line=dict(color=C["price"], width=2),
        name="Cumulative Return",
    ))
    fig.update_layout(
        title=f"{ticker} — Cumulative Return (%)",
        xaxis_title="Date", yaxis_title="Return (%)",
        template=TEMPLATE, height=350,
    )
    return fig


def volatility_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    """Area chart of rolling 21-day annualised volatility."""
    fig = go.Figure(go.Scatter(
        x=df.index, y=df["Volatility"],
        fill="tozeroy", line=dict(color=C["vol"], width=2),
        name="Volatility",
    ))
    fig.update_layout(
        title=f"{ticker} — Rolling Volatility — Annualised (%)",
        xaxis_title="Date", yaxis_title="Volatility (%)",
        template=TEMPLATE, height=350,
    )
    return fig


# ── 7. Portfolio ──────────────────────────────────────────────────────────────

def portfolio_pie_chart(holdings: list) -> go.Figure:
    """
    Donut chart of portfolio allocation by current market value.

    Parameters
    ----------
    holdings : list of dicts, each with keys 'ticker' and 'current_value'
    """
    labels = [h["ticker"]        for h in holdings]
    values = [h["current_value"] for h in holdings]

    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.42,
        marker=dict(colors=px.colors.qualitative.Plotly),
        textinfo="label+percent",
    ))
    fig.update_layout(
        title="Portfolio Allocation by Current Value",
        template=TEMPLATE, height=420,
    )
    return fig
