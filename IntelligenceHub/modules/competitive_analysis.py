import streamlit as st
import pandas as pd
import plotly.express as px

def show():
    st.title("📊 Competitive Analysis")
    st.markdown("---")

    col1, col2 = st.columns([1, 3])

    with col1:
        st.subheader("Data Source")
        data_source = st.radio("Select Source", ["AI Generation", "Upload File"])
        
        df = None
        
        if data_source == "AI Generation":
            industry = st.text_input("Industry / Market", "Smartphone", key="industry_input")
            if st.button("✨ Generate Market Data"):
                with st.spinner(f"Analyzing {industry} market..."):
                   from utils.ai_handler import AIHandler
                   ai = AIHandler()
                   data = ai.generate_competitive_data(industry)
                   if data:
                       df = pd.DataFrame(data)
                       # Ensure numeric types
                       for col in df.columns:
                           if col != 'Competitor':
                               try:
                                   df[col] = pd.to_numeric(df[col])
                               except:
                                   pass
                       st.session_state['comp_data'] = df
                       st.success("✅ Market data generated!")
                   else:
                       st.error("Failed to generate data. Please try again.")
            
            if 'comp_data' in st.session_state:
                df = st.session_state['comp_data']
        
        elif data_source == "Upload File":
            uploaded_file = st.file_uploader("Upload CSV/Excel", type=['csv', 'xlsx'])
            if uploaded_file:
                try:
                    if uploaded_file.name.endswith('.csv'):
                        df = pd.read_csv(uploaded_file)
                    else:
                        df = pd.read_excel(uploaded_file)
                    st.success("✅ File uploaded successfully!")
                except Exception as e:
                    st.error(f"Error reading file: {e}")

    with col2:
        if df is not None:
            st.subheader("Market Overview")
            
            # Identify columns
            cols = df.columns.tolist()
            cat_col = next((c for c in cols if df[c].dtype == 'object'), cols[0])
            
            # Convert to numeric where possible
            for c in cols:
                if c != cat_col:
                    try:
                        df[c] = pd.to_numeric(df[c])
                    except:
                        pass
            
            num_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
            
            if len(num_cols) < 1:
                st.error("Data needs at least one numerical column for analysis.")
            else:
                # Display summary metrics
                st.markdown("### Key Metrics")
                metric_cols = st.columns(3)
                metric_cols[0].metric("Total Companies", len(df))
                if 'Market Share (%)' in df.columns:
                    metric_cols[1].metric("Total Market Coverage", f"{df['Market Share (%)'].sum():.1f}%")
                if 'Revenue ($M)' in df.columns:
                    metric_cols[2].metric("Total Revenue", f"${df['Revenue ($M)'].sum():,.0f}M")
                
                st.markdown("---")
                
                # Visualizations
                tab1, tab2, tab3 = st.tabs(["📊 Market Share", "💰 Revenue Analysis", "📋 Raw Data"])
                
                with tab1:
                    if 'Market Share (%)' in df.columns:
                        fig_pie = px.pie(
                            df, 
                            values='Market Share (%)', 
                            names=cat_col, 
                            title=f"{industry if 'industry_input' in st.session_state else 'Industry'} Market Share Distribution",
                            hole=0.3
                        )
                        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                        st.plotly_chart(fig_pie, use_container_width=True)
                    else:
                        target_col = st.selectbox("Select Metric for Share", num_cols, index=0)
                        fig_pie = px.pie(df, values=target_col, names=cat_col, title=f"Distribution by {target_col}")
                        st.plotly_chart(fig_pie, use_container_width=True)
                    
                with tab2:
                    if 'Revenue ($M)' in df.columns:
                        # Sort by revenue for better visualization
                        df_sorted = df.sort_values('Revenue ($M)', ascending=True)
                        fig_bar = px.bar(
                            df_sorted, 
                            x='Revenue ($M)', 
                            y=cat_col, 
                            orientation='h',
                            title=f"{industry if 'industry_input' in st.session_state else 'Industry'} Revenue Comparison",
                            color='Revenue ($M)',
                            color_continuous_scale='Blues'
                        )
                        st.plotly_chart(fig_bar, use_container_width=True)
                    else:
                        target_col_bar = st.selectbox("Select Metric for Comparison", num_cols, index=min(1, len(num_cols)-1))
                        fig_bar = px.bar(df, x=cat_col, y=target_col_bar, color=cat_col, title=f"{target_col_bar} by Competitor")
                        st.plotly_chart(fig_bar, use_container_width=True)
                    
                with tab3:
                    st.dataframe(df, use_container_width=True)
            
            st.markdown("---")
            if st.button("🤖 Generate AI Strategic Insights"):
                with st.spinner("Analyzing market dynamics..."):
                    from utils.ai_handler import AIHandler
                    ai = AIHandler()
                    summary = df.to_string()
                    insights = ai.analyze_competition(summary)
                    
                    st.success("✅ Analysis Complete")
                    st.markdown("### 🎯 Strategic Insights")
                    st.markdown(insights)
        else:
            st.info("👈 Select a data source from the sidebar to begin analysis.")
            st.markdown("""
            **Available Options:**
            - **AI Generation**: Generate realistic market data for any industry
            - **Upload File**: Use your own CSV/Excel data
            """)
