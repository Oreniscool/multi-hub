import streamlit as st
import plotly.graph_objects as go
import os
from utils.data_handler import fetch_stock_data

def show():
    st.title("📈 Market Intelligence")
    st.markdown("---")

    col1, col2 = st.columns([1, 3])

    with col1:
        st.subheader("Configuration")
        ticker = st.text_input("Stock Ticker", value="IBM").upper()
        api_key = os.getenv("ALPHA_VANTAGE_API_KEY", "").strip()
        if api_key:
            st.caption("Using server-side Alpha Vantage key from environment.")
        else:
            st.warning("ALPHA_VANTAGE_API_KEY is not configured in environment.")
        
        if st.button("Analyze Stock"):
            if not ticker:
                st.error("Please provide a ticker.")
            elif not api_key:
                st.error("ALPHA_VANTAGE_API_KEY is missing in environment.")
            else:
                with st.spinner(f"Fetching data for {ticker}..."):
                    df, error = fetch_stock_data(ticker, api_key)
                    if error:
                        st.error(error)
                    else:
                        st.session_state['market_data'] = df
                        st.session_state['current_ticker'] = ticker

    with col2:
        if 'market_data' in st.session_state:
            df = st.session_state['market_data']
            ticker = st.session_state['current_ticker']
            
            st.subheader(f"Analysis for {ticker}")
            
            # Key Statistics
            latest_date = df.index[0]
            latest_data = df.iloc[0]
            prev_data = df.iloc[1]
            change = latest_data['Close'] - prev_data['Close']
            pct_change = (change / prev_data['Close']) * 100
            
            stat_cols = st.columns(4)
            stat_cols[0].metric("Close Price", f"${latest_data['Close']:.2f}", f"{change:.2f} ({pct_change:.2f}%)")
            stat_cols[1].metric("Open", f"${latest_data['Open']:.2f}")
            stat_cols[2].metric("High", f"${latest_data['High']:.2f}")
            stat_cols[3].metric("Volume", f"{int(latest_data['Volume']):,}")
            
            # Charts
            tab1, tab2 = st.tabs(["Price History", "Candlestick"])
            
            with tab1:
                fig_line = go.Figure()
                fig_line.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name='Close Price'))
                fig_line.update_layout(title=f"{ticker} Daily Closing Price", xaxis_title="Date", yaxis_title="Price")
                st.plotly_chart(fig_line, use_container_width=True)
                
            with tab2:
                fig_candle = go.Figure(data=[go.Candlestick(x=df.index,
                        open=df['Open'],
                        high=df['High'],
                        low=df['Low'],
                        close=df['Close'])])
                fig_candle.update_layout(title=f"{ticker} Candlestick Chart", xaxis_title="Date", yaxis_title="Price")
                st.plotly_chart(fig_candle, use_container_width=True)
        else:
            st.info("Enter details in the sidebar and click Analyze Stock to view data.")
