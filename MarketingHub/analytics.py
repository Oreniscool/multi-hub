import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

def generate_mock_data():
    """Generates mock data for demonstration."""
    dates = pd.date_range(start="2024-01-01", periods=30)
    data = {
        "Date": dates,
        "Impressions": np.random.randint(1000, 5000, size=30),
        "Clicks": np.random.randint(100, 500, size=30),
        "Cost": np.random.randint(50, 200, size=30),
        "Conversions": np.random.randint(10, 50, size=30),
        "Platform": np.random.choice(["LinkedIn", "Twitter", "Email", "Instagram"], size=30)
    }
    return pd.DataFrame(data)

def app():
    st.title("📊 Analytics Dashboard")
    st.markdown("Visualize your campaign performance with interactive charts.")

    # Data Source Section
    st.sidebar.markdown("### Data Settings")
    use_mock_data = st.sidebar.checkbox("Use Mock Data", value=True)
    
    df = None
    
    if use_mock_data:
        df = generate_mock_data()
        st.info("Using Mock Data for demonstration.")
    else:
        uploaded_file = st.file_uploader("Upload Campaign Data", type=["csv", "xlsx"])
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                st.success("File uploaded successfully!")
            except Exception as e:
                st.error(f"Error reading file: {e}")
        else:
            st.warning("Please upload a file or enable 'Use Mock Data'.")
            return

    if df is not None:
        # Pre-process mock data (ensure numeric types)
        # Assuming minimal required columns for custom upload, or flexible fallback
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
        
        # 1. KPI Row
        st.markdown("### Key Performance Indicators")
        col1, col2, col3, col4 = st.columns(4)
        
        total_spend = df["Cost"].sum() if "Cost" in df.columns else 0
        total_conversions = df["Conversions"].sum() if "Conversions" in df.columns else 0
        total_clicks = df["Clicks"].sum() if "Clicks" in df.columns else 0
        total_impressions = df["Impressions"].sum() if "Impressions" in df.columns else 0
        
        ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        
        col1.metric("Total Spend", f"${total_spend:,.2f}")
        col2.metric("Conversions", total_conversions)
        col3.metric("CTR", f"{ctr:.2f}%")
        col4.metric("Total Clicks", total_clicks)
        
        st.markdown("---")

        # 2. Charts
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown("### Trends Over Time")
            metric_columns = [col for col in ["Clicks", "Conversions", "Cost"] if col in df.columns]
            if "Date" in df.columns and metric_columns:
                fig_trend = go.Figure()
                for metric in metric_columns:
                    fig_trend.add_trace(
                        go.Scatter(
                            x=df["Date"],
                            y=df[metric],
                            mode="lines+markers",
                            name=metric,
                            line=dict(width=3)
                        )
                    )
                fig_trend.update_layout(
                    title="Daily Metrics Trend",
                    xaxis_title="Date",
                    yaxis_title="Value",
                    hovermode="x unified",
                    height=400
                )
                st.plotly_chart(fig_trend, use_container_width=True)
            else:
                st.write("Date/Metrics columns missing for Trend Chart.")
                
        with col_right:
            st.markdown("### Channel Performance")
            if "Platform" in df.columns and "Conversions" in df.columns:
                platform_stats = df.groupby("Platform")[["Conversions", "Cost", "Clicks"]].sum().reset_index()
                fig_bar = go.Figure()
                fig_bar.add_trace(
                    go.Bar(
                        x=platform_stats["Platform"],
                        y=platform_stats["Conversions"],
                        text=[f"{val:.0f}" for val in platform_stats["Conversions"]],
                        textposition="outside",
                        marker_color="#3b82f6"
                    )
                )
                fig_bar.update_layout(
                    title="Conversions by Platform",
                    xaxis_title="Platform",
                    yaxis_title="Conversions",
                    height=400,
                    showlegend=False
                )
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.write("Platform/Conversions columns missing for Channel Chart.")
        
        # Data Table
        with st.expander("View Raw Data"):
            st.dataframe(df)

