"""
app.py
------
Stock Market Analysis Dashboard — Main Streamlit application.

Pages
-----
  🏠 Overview          Candlestick chart + KPI cards + raw data table
  📊 Technical Analysis Price + SMA/EMA/BB, RSI, MACD with adjustable windows
  🔀 Comparison         Multi-stock normalised comparison + risk/return
  📉 Analytics          Daily returns, cumulative returns, volatility, stats
  💼 Portfolio          Position tracker with real-time P&L
  ⭐ Watchlist          Save tickers for quick access
  🕐 History            Full search log with clear option

Run
---
  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, timedelta

from utils.data_loader import (
    fetch_stock_data, fetch_stock_info,
    fetch_multiple_stocks, get_top_movers,
)

from utils.indicators import (
    apply_all_indicators, add_sma, add_ema,
    add_rsi, add_macd, add_bollinger_bands,
)

from utils.charts import (
    candlestick_chart, line_chart_with_indicators,
    rsi_chart, macd_chart,
    comparison_chart, performance_bar_chart, risk_return_scatter,
    daily_returns_chart, cumulative_returns_chart, volatility_chart,
    portfolio_pie_chart,
)

from utils.database import (
    initialize_database,
    save_search, get_recent_searches, clear_search_history,
    add_to_watchlist, get_watchlist, remove_from_watchlist,
    add_to_portfolio, get_portfolio, remove_from_portfolio,
)
# ── Page configuration ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Stock Market Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── One-time database setup ───────────────────────────────────────────────────
initialize_database()

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* KPI card container */
.kpi-card {
    background: linear-gradient(135deg, #1e1e2e 0%, #2a2a40 100%);
    border-radius: 14px;
    padding: 22px 18px;
    text-align: center;
    border: 1px solid rgba(255,255,255,0.08);
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
}
.kpi-label  { font-size: 12px; color: #888; letter-spacing: 0.5px; margin-bottom: 6px; }
.kpi-value  { font-size: 28px; font-weight: 700; color: #f0f0f0; }
.kpi-change { font-size: 13px; margin-top: 6px; }
.positive   { color: #26A69A; }
.negative   { color: #EF5350; }
.neutral    { color: #aaa; }
/* Divider */
hr { border-color: rgba(255,255,255,0.08); }
</style>
""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 📈 Stock Dashboard")
    st.markdown("---")

    page = st.radio(
        "Go to",
        options=[
            "🏠 Overview",
            "📊 Technical Analysis",
            "🔀 Comparison",
            "📉 Analytics",
            "💼 Portfolio",
            "⭐ Watchlist",
            "🕐 History",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.subheader("⚙️ Settings")

    ticker = st.text_input(
        "Ticker Symbol",
        value="AAPL",
        max_chars=12,
        help="Examples: AAPL, TSLA, RELIANCE.NS, BTC-USD",
    ).upper().strip()

    col_s, col_e = st.columns(2)
    with col_s:
        start_date = st.date_input("Start", value=date.today() - timedelta(days=365))
    with col_e:
        end_date = st.date_input("End", value=date.today())

    fetch_btn = st.button("🔍 Fetch Data", use_container_width=True, type="primary")

    st.markdown("---")

    # Recent searches preview in sidebar
    recent_tickers = get_recent_searches(5)
    if recent_tickers:
        st.caption("🕐 Recent")
        for row in recent_tickers:
            st.caption(f"• {row[0]}  —  {row[1][:10]}")


# ═════════════════════════════════════════════════════════════════════════════
# SESSION STATE  —  persist data across page switches
# ═════════════════════════════════════════════════════════════════════════════
if "df" not in st.session_state:
    st.session_state["df"]     = pd.DataFrame()
    st.session_state["ticker"] = ""
    st.session_state["info"]   = {}

# Fetch on button press or when ticker changes
if fetch_btn or (ticker and ticker != st.session_state["ticker"]):
    if not ticker:
        st.sidebar.warning("Enter a ticker symbol first.")
    else:
        with st.spinner(f"Fetching {ticker}…"):
            raw  = fetch_stock_data(ticker, str(start_date), str(end_date))
            info = fetch_stock_info(ticker)

        if raw.empty:
            st.sidebar.error(f"❌ No data for '{ticker}'. Check the symbol.")
        else:
            df = apply_all_indicators(raw.copy())
            st.session_state["df"]     = df
            st.session_state["ticker"] = ticker
            st.session_state["info"]   = info
            save_search(ticker)
            st.sidebar.success(f"✅ {len(df)} trading days loaded")

# Shorthand references used throughout the pages
df     = st.session_state["df"]
info   = st.session_state["info"]
ticker = st.session_state["ticker"]


# ═════════════════════════════════════════════════════════════════════════════
# HELPER — KPI card HTML
# ═════════════════════════════════════════════════════════════════════════════
def kpi_card(label: str, value: str, sub: str = "", css_class: str = "neutral") -> str:
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-change {css_class}">{sub}</div>
    </div>"""


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: OVERVIEW
# ═════════════════════════════════════════════════════════════════════════════
if page == "🏠 Overview":
    st.title("🏠 Market Overview")

    # Top movers banner
    gainers, losers = get_top_movers()
    g_col, l_col = st.columns(2)
    with g_col:
        st.success("🚀 **Top Gainers (Popular):** " + "  |  ".join(gainers))
    with l_col:
        st.error("📉 **Top Losers (Popular):** " + "  |  ".join(losers))

    st.markdown("---")

    if df.empty:
        st.info("👈 Enter a ticker symbol in the sidebar and click **Fetch Data** to begin.")
        st.stop()

    # Company header
    st.subheader(f"📌 {info.get('name', ticker)}  ·  `{ticker}`")
    st.caption(
        f"Sector: **{info.get('sector', 'N/A')}**  |  "
        f"Market Cap: **${info.get('market_cap', 0):,.0f}**  |  "
        f"P/E: **{info.get('pe_ratio', 'N/A')}**"
    )

    # ── KPI Cards ──────────────────────────────────────────────────────────
    current_price  = info.get("current_price")  or float(df["Close"].iloc[-1])
    previous_close = info.get("previous_close") or float(df["Close"].iloc[-2] if len(df) > 1 else current_price)
    day_change     = current_price - previous_close
    day_change_pct = (day_change / previous_close * 100) if previous_close else 0
    w52_high       = info.get("week_52_high", 0)
    w52_low        = info.get("week_52_low",  0)

    sign  = "positive" if day_change >= 0 else "negative"
    arrow = "▲" if day_change >= 0 else "▼"

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(kpi_card(
            "Current Price", f"${current_price:.2f}",
            f"{arrow} {abs(day_change):.2f}  ({abs(day_change_pct):.2f}%)", sign
        ), unsafe_allow_html=True)
    with k2:
        st.markdown(kpi_card(
            "Daily Change", f"{arrow} {abs(day_change_pct):.2f}%",
            "vs previous close", sign
        ), unsafe_allow_html=True)
    with k3:
        st.markdown(kpi_card(
            "52-Week High", f"${w52_high:.2f}",
            f"Current at {(current_price/w52_high*100):.1f}% of high" if w52_high else "",
            "positive"
        ), unsafe_allow_html=True)
    with k4:
        st.markdown(kpi_card(
            "52-Week Low", f"${w52_low:.2f}",
            f"Current at {(current_price/w52_low*100):.1f}% of low" if w52_low else "",
            "negative"
        ), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Candlestick ─────────────────────────────────────────────────────────
    st.plotly_chart(candlestick_chart(df, ticker), use_container_width=True)

    # ── Raw data table ──────────────────────────────────────────────────────
    with st.expander("📋 Raw OHLCV Data (last 50 rows)"):
        display_df = df[["Open", "High", "Low", "Close", "Volume"]].tail(50)
        st.dataframe(
            display_df.style.format({
                "Open":   "{:.2f}", "High": "{:.2f}",
                "Low":    "{:.2f}", "Close": "{:.2f}",
                "Volume": "{:,.0f}",
            }),
            use_container_width=True,
        )

    # ── CSV Download ─────────────────────────────────────────────────────────
    csv_bytes = df.to_csv().encode("utf-8")
    st.download_button(
        label="⬇️ Download Full Dataset as CSV",
        data=csv_bytes,
        file_name=f"{ticker}_historical_data.csv",
        mime="text/csv",
        use_container_width=True,
    )


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: TECHNICAL ANALYSIS
# ═════════════════════════════════════════════════════════════════════════════
elif page == "📊 Technical Analysis":
    st.title("📊 Technical Analysis")

    if df.empty:
        st.info("👈 Fetch stock data from the sidebar first.")
        st.stop()

    # ── User controls ────────────────────────────────────────────────────────
    ctrl1, ctrl2, ctrl3 = st.columns(3)
    show_sma = ctrl1.checkbox("Show SMA",             value=True)
    show_ema = ctrl2.checkbox("Show EMA",             value=True)
    show_bb  = ctrl3.checkbox("Show Bollinger Bands", value=True)

    sma_w = st.slider("SMA Window (days)", min_value=5, max_value=200, value=20, step=5)
    ema_w = st.slider("EMA Window (days)", min_value=5, max_value=200, value=20, step=5)

    # Recompute indicators with the user-selected windows
    raw2 = fetch_stock_data(ticker, str(start_date), str(end_date))
    if raw2.empty:
        st.error("Could not reload data. Please re-fetch from the sidebar.")
        st.stop()

    df2 = add_sma(raw2.copy(), sma_w)
    df2 = add_ema(df2, ema_w)
    df2 = add_rsi(df2)
    df2 = add_macd(df2)
    df2 = add_bollinger_bands(df2)

    # ── Charts ───────────────────────────────────────────────────────────────
    st.plotly_chart(
        line_chart_with_indicators(df2, ticker, show_sma, show_ema, show_bb),
        use_container_width=True,
    )

    c_rsi, c_macd = st.columns(2)
    with c_rsi:
        st.plotly_chart(rsi_chart(df2), use_container_width=True)
    with c_macd:
        st.plotly_chart(macd_chart(df2), use_container_width=True)

    # ── Legend ───────────────────────────────────────────────────────────────
    with st.expander("ℹ️ How to Read These Indicators"):
        st.markdown("""
| Indicator | Formula | Trading Signal |
|-----------|---------|----------------|
| **SMA** | Mean of last N closing prices | Price crossing above SMA → bullish |
| **EMA** | Weighted mean (recent prices weighted more) | Faster to react than SMA |
| **Bollinger Bands** | SMA ± 2 × rolling std | Price at upper band → overbought; lower → oversold |
| **RSI** | 100 − 100/(1+RS) where RS = avg gain/avg loss | > 70 overbought; < 30 oversold |
| **MACD** | EMA(12) − EMA(26); Signal = EMA(MACD,9) | MACD crossing above Signal → buy signal |
        """)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: COMPARISON
# ═════════════════════════════════════════════════════════════════════════════
elif page == "🔀 Comparison":
    st.title("🔀 Stock Comparison")
    st.caption("Compare multiple stocks over the same date range selected in the sidebar.")

    tickers_raw   = st.text_input(
        "Enter ticker symbols separated by commas",
        value="AAPL, MSFT, GOOGL, AMZN, TSLA",
    )
    tickers_list  = [t.strip().upper() for t in tickers_raw.split(",") if t.strip()]
    normalize     = st.checkbox("Normalise prices (all start at 100)", value=True)

    if st.button("📊 Run Comparison", type="primary"):
        if len(tickers_list) < 2:
            st.warning("Enter at least 2 ticker symbols.")
        else:
            with st.spinner("Fetching comparison data…"):
                price_data = fetch_multiple_stocks(tickers_list, str(start_date), str(end_date))

            if not price_data:
                st.error("No valid data returned. Check ticker symbols.")
            else:
                failed = [t for t in tickers_list if t not in price_data]
                if failed:
                    st.warning(f"Could not fetch data for: {', '.join(failed)}")

                st.plotly_chart(comparison_chart(price_data, normalize),    use_container_width=True)
                st.plotly_chart(performance_bar_chart(price_data),          use_container_width=True)
                st.plotly_chart(risk_return_scatter(price_data),            use_container_width=True)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: ANALYTICS
# ═════════════════════════════════════════════════════════════════════════════
elif page == "📉 Analytics":
    st.title("📉 Analytics")

    if df.empty:
        st.info("👈 Fetch stock data from the sidebar first.")
        st.stop()

    a1, a2 = st.columns(2)
    with a1:
        st.plotly_chart(daily_returns_chart(df, ticker),      use_container_width=True)
    with a2:
        st.plotly_chart(cumulative_returns_chart(df, ticker), use_container_width=True)

    st.plotly_chart(volatility_chart(df, ticker), use_container_width=True)

    # Summary statistics
    st.subheader("📊 Summary Statistics")
    daily_pct = df["Close"].pct_change().dropna() * 100
    stats = {
        "Mean Daily Return (%)":     round(daily_pct.mean(), 4),
        "Std Dev of Daily Return":   round(daily_pct.std(), 4),
        "Best Single Day (%)":       round(daily_pct.max(), 4),
        "Worst Single Day (%)":      round(daily_pct.min(), 4),
        "Annualised Volatility (%)": round(daily_pct.std() * np.sqrt(252), 2),
        "Total Return (%)":          round(
            (df["Close"].iloc[-1] / df["Close"].iloc[0] - 1) * 100, 2
        ),
    }
    s1, s2, s3 = st.columns(3)
    cols = [s1, s2, s3]
    for i, (label, val) in enumerate(stats.items()):
        cols[i % 3].metric(label, f"{val}%")


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: PORTFOLIO
# ═════════════════════════════════════════════════════════════════════════════
elif page == "💼 Portfolio":
    st.title("💼 Portfolio Tracker")

    # ── Add position form ─────────────────────────────────────────────────────
    st.subheader("➕ Add New Position")
    f1, f2, f3, f4 = st.columns([2, 1, 1, 1])
    p_ticker = f1.text_input("Ticker",      key="p_ticker").upper().strip()
    p_shares = f2.number_input("Shares",    min_value=0.0001, step=0.01, format="%.4f")
    p_buy    = f3.number_input("Buy Price ($)", min_value=0.0001, step=0.01, format="%.2f")
    if f4.button("Add Position", type="primary"):
        if p_ticker and p_shares > 0 and p_buy > 0:
            add_to_portfolio(p_ticker, p_shares, p_buy)
            st.success(f"✅ Added {p_shares} × {p_ticker} @ ${p_buy:.2f}")
            st.rerun()
        else:
            st.warning("Fill in all three fields.")

    st.markdown("---")

    # ── Display holdings ──────────────────────────────────────────────────────
    rows = get_portfolio()
    if not rows:
        st.info("No positions yet. Add one above.")
    else:
        holdings, total_cost, total_value = [], 0.0, 0.0

        for row_id, t, shares, buy_px, added in rows:
            inf     = fetch_stock_info(t)
            curr_px = inf.get("current_price") or buy_px
            cost    = shares * buy_px
            val     = shares * curr_px
            pnl     = val - cost
            pnl_pct = (pnl / cost * 100) if cost else 0.0
            total_cost  += cost
            total_value += val
            holdings.append({
                "id": row_id, "ticker": t,
                "shares": shares, "buy_price": buy_px,
                "current_price": curr_px, "cost": cost,
                "current_value": val, "pnl": pnl, "pnl_pct": pnl_pct,
            })

        total_pnl     = total_value - total_cost
        total_pnl_pct = (total_pnl / total_cost * 100) if total_cost else 0.0

        # Portfolio KPI row
        pk1, pk2, pk3, pk4 = st.columns(4)
        pk1.metric("Total Invested",   f"${total_cost:.2f}")
        pk2.metric("Portfolio Value",  f"${total_value:.2f}")
        pk3.metric("Total P&L",        f"${total_pnl:.2f}",
                   delta=f"{total_pnl_pct:.2f}%")
        pk4.metric("Positions",        str(len(holdings)))

        # Allocation pie chart
        st.plotly_chart(portfolio_pie_chart(holdings), use_container_width=True)

        # Holdings detail table
        st.subheader("Holdings Detail")
        for h in holdings:
            c1, c2, c3, c4, c5, c6 = st.columns([1.2, 1, 1, 1, 1.2, 0.6])
            c1.markdown(f"**{h['ticker']}**")
            c2.write(f"{h['shares']:.4f} shares")
            c3.write(f"Buy: ${h['buy_price']:.2f}")
            c4.write(f"Now: ${h['current_price']:.2f}")
            pnl_cls = "positive" if h["pnl"] >= 0 else "negative"
            c5.markdown(
                f"<span class='{pnl_cls}'>"
                f"{'▲' if h['pnl'] >= 0 else '▼'} ${abs(h['pnl']):.2f} "
                f"({abs(h['pnl_pct']):.2f}%)</span>",
                unsafe_allow_html=True,
            )
            if c6.button("🗑️", key=f"del_{h['id']}"):
                remove_from_portfolio(h["id"])
                st.rerun()


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: WATCHLIST
# ═════════════════════════════════════════════════════════════════════════════
elif page == "⭐ Watchlist":
    st.title("⭐ Watchlist")

    w1, w2 = st.columns([3, 1])
    watch_input = w1.text_input("Add ticker to watchlist", placeholder="e.g. NVDA").upper().strip()
    if w2.button("Add ⭐", type="primary"):
        if watch_input:
            add_to_watchlist(watch_input)
            st.success(f"Added **{watch_input}** to watchlist.")
            st.rerun()

    st.markdown("---")
    wl = get_watchlist()

    if not wl:
        st.info("Your watchlist is empty. Add tickers above.")
    else:
        for t, added in wl:
            wi = fetch_stock_info(t)
            curr   = wi.get("current_price", 0) or 0
            prev   = wi.get("previous_close", curr) or curr
            change = ((curr - prev) / prev * 100) if prev else 0.0

            wc1, wc2, wc3, wc4, wc5 = st.columns([1.5, 2, 1, 1, 0.8])
            wc1.markdown(f"**{t}**")
            wc2.caption(wi.get("name", "")[:35])
            wc3.metric("Price",  f"${curr:.2f}", label_visibility="collapsed")
            css = "positive" if change >= 0 else "negative"
            wc4.markdown(
                f"<span class='{css}'>{'▲' if change >= 0 else '▼'} {abs(change):.2f}%</span>",
                unsafe_allow_html=True,
            )
            if wc5.button("Remove", key=f"rm_{t}"):
                remove_from_watchlist(t)
                st.rerun()


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: HISTORY
# ═════════════════════════════════════════════════════════════════════════════
elif page == "🕐 History":
    st.title("🕐 Search History")

    history = get_recent_searches(100)
    if not history:
        st.info("No searches recorded yet.")
    else:
        df_hist = pd.DataFrame(history, columns=["Ticker", "Searched At"])
        st.dataframe(df_hist, use_container_width=True, hide_index=True)

        if st.button("🗑️ Clear All History", type="secondary"):
            clear_search_history()
            st.success("History cleared.")
            st.rerun()
