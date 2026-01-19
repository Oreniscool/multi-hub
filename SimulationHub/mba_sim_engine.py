import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURATION ---
st.set_page_config(
    page_title="MBA Business Simulation Engine",
    page_icon="💼",
    layout="wide"
)

# --- STATE MANAGEMENT ---
if 'saved_scenarios' not in st.session_state:
    st.session_state.saved_scenarios = []

# --- HEADER ---
st.title("💼 MBA Business Simulation Engine")
st.markdown("Model business scenarios, calculate financial KPIs, and compare strategies.")

# --- HELPERS ---
def calculate_kpis(price, marketing, volume, fixed_cost, variable_cost):
    revenue = price * volume
    total_variable_cost = variable_cost * volume
    total_cost = fixed_cost + total_variable_cost + marketing
    net_profit = revenue - total_cost
    if (price - variable_cost) > 0:
        breakeven_units = (fixed_cost + marketing) / (price - variable_cost)
    else:
        breakeven_units = float('inf') # Avoid division by zero
    
    return {
        "Revenue": revenue,
        "Total Cost": total_cost,
        "Net Profit": net_profit,
        "Break-even Units": breakeven_units,
        "Margin": (net_profit / revenue) * 100 if revenue > 0 else 0
    }

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Data Ingestion
    ingestion_mode = st.radio("Scenario Source", ["Default Base Case", "Upload CSV"])
    
    base_data = {
        "Base_Price": 50.0,
        "Base_Volume": 1000,
        "Fixed_Cost": 20000.0,
        "Variable_Cost": 20.0,
        "Marketing_Budget": 5000.0
    }

    if ingestion_mode == "Upload CSV":
        uploaded_file = st.file_uploader("Upload Scenario CSV", type=["csv"])
        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file)
                if not df.empty:
                    required_cols = ["Base_Price", "Base_Volume", "Fixed_Cost", "Variable_Cost"]
                    if all(col in df.columns for col in required_cols):
                         row = df.iloc[0]
                         base_data["Base_Price"] = float(row.get("Base_Price", 50.0))
                         base_data["Base_Volume"] = int(row.get("Base_Volume", 1000))
                         base_data["Fixed_Cost"] = float(row.get("Fixed_Cost", 20000.0))
                         base_data["Variable_Cost"] = float(row.get("Variable_Cost", 20.0))
                         st.success("CSV loaded successfully!")
                    else:
                        st.error(f"CSV must contain columns: {required_cols}")
            except Exception as e:
                st.error(f"Error reading CSV: {e}")

    st.divider()
    st.subheader("Operational Levers")
    
    # Sliders (initialized with base_data)
    price = st.slider("Unit Price ($)", 
                      min_value=0.0, 
                      max_value=base_data["Base_Price"] * 3, 
                      value=base_data["Base_Price"],
                      step=1.0,
                      key="price_slider")
    
    volume = st.slider("Production Volume (Units)", 
                       min_value=0, 
                       max_value=base_data["Base_Volume"] * 3, 
                       value=base_data["Base_Volume"],
                       step=10,
                       key="volume_slider")
    
    marketing = st.slider("Marketing Budget ($)", 
                          min_value=0.0, 
                          max_value=20000.0,
                          value=base_data.get("Marketing_Budget", 5000.0),
                          step=500.0,
                          key="marketing_slider")

    st.divider()
    st.subheader("Cost Structure")
    fixed_cost = st.number_input("Fixed Cost ($)", value=base_data["Fixed_Cost"], key="fixed_cost_input")
    variable_cost = st.number_input("Variable Cost per Unit ($)", value=base_data["Variable_Cost"], key="variable_cost_input")

    st.divider()
    
    # Save Scenario
    st.subheader("Save Scenario")
    scenario_name_input = st.text_input("Scenario Name", value=f"Scenario {len(st.session_state.saved_scenarios) + 1}", key="scenario_name")
    if st.button("💾 Save Scenario", use_container_width=True):
        current_kpis = calculate_kpis(price, marketing, volume, fixed_cost, variable_cost)
        scenario_data = {
            "Name": scenario_name_input,
            "Price": price,
            "Volume": volume,
            "Marketing": marketing,
            "Fixed Cost": fixed_cost,
            "Variable Cost": variable_cost,
            **current_kpis
        }
        st.session_state.saved_scenarios.append(scenario_data)
        st.success(f"Saved: {scenario_name_input}")

# --- MAIN CONTENT ---
# Calculate Current State
current_kpis = calculate_kpis(price, marketing, volume, fixed_cost, variable_cost)

st.header("📊 Real-time Analysis")

# KPIs
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Revenue", f"${current_kpis['Revenue']:,.2f}")
col2.metric("Net Profit", f"${current_kpis['Net Profit']:,.2f}")
col3.metric("Profit Margin", f"{current_kpis['Margin']:.1f}%")
col4.metric("Break-even Units", f"{current_kpis['Break-even Units']:.0f}")

st.divider()

# Visualizations
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.subheader("Break-even Analysis")
    
    # Generate range based on current volume
    max_vol_plot = max(volume * 2, current_kpis['Break-even Units'] * 1.5 if current_kpis['Break-even Units'] != float('inf') else 2000)
    if max_vol_plot <= 0:
        max_vol_plot = max(volume * 1.5, 1000)

    # Use linspace to ensure smooth curve with enough points
    vol_range = pd.DataFrame({'Volume': np.linspace(0, max_vol_plot, num=200)})
    
    vol_range['Revenue'] = vol_range['Volume'] * price
    vol_range['Total Cost'] = fixed_cost + marketing + (variable_cost * vol_range['Volume'])
    
    # Create figure manually for better control
    fig_be = go.Figure()
    
    # Add Revenue line
    fig_be.add_trace(go.Scatter(
        x=vol_range['Volume'].tolist(),
        y=vol_range['Revenue'].tolist(),
        mode='lines',
        name='Revenue',
        line=dict(color='#10b981', width=3)
    ))
    
    # Add Total Cost line
    fig_be.add_trace(go.Scatter(
        x=vol_range['Volume'].tolist(),
        y=vol_range['Total Cost'].tolist(),
        mode='lines',
        name='Total Cost',
        line=dict(color='#ef4444', width=3)
    ))
    
    # Add vertical line for current volume
    fig_be.add_vline(x=volume, line_dash="dash", line_color="#3b82f6", line_width=2,
                     annotation_text=f"Current: {volume}", annotation_position="top")
    
    # Add vertical line for break even
    if current_kpis['Break-even Units'] != float('inf') and current_kpis['Break-even Units'] > 0:
         fig_be.add_vline(x=current_kpis['Break-even Units'], line_dash="dot", line_color="#f59e0b", line_width=2,
                          annotation_text=f"B/E: {current_kpis['Break-even Units']:.0f}", annotation_position="bottom")
    
    fig_be.update_layout(
        title="Revenue vs. Cost",
        xaxis_title="Volume",
        yaxis_title="Amount ($)",
        height=400,
        hovermode='x unified'
    )
    fig_be.update_yaxes(tickformat='$,.0f')
    st.plotly_chart(fig_be, use_container_width=True, key="breakeven_chart")

with chart_col2:
    st.subheader("Profitability Waterfall")
    
    # Waterfall data
    measures = ["Revenue", "Variable Costs", "Fixed Costs", "Marketing", "Net Profit"]
    amounts = [
        current_kpis['Revenue'],
        -(variable_cost * volume),
        -fixed_cost,
        -marketing,
        current_kpis['Net Profit']
    ]
    
    # Create bar chart with explicit values
    fig_prof = go.Figure()
    
    colors = ['#10b981', '#ef4444', '#ef4444', '#ef4444', '#3b82f6']
    
    for i, (measure, amount) in enumerate(zip(measures, amounts)):
        fig_prof.add_trace(go.Bar(
            x=[measure],
            y=[amount],
            name=measure,
            text=[f'${amount:,.0f}'],
            textposition='outside',
            marker_color=colors[i],
            showlegend=False
        ))
    
    fig_prof.update_layout(
        title="Profit Breakdown",
        xaxis_title="Measure",
        yaxis_title="Amount ($)",
        height=400,
        showlegend=False
    )
    st.plotly_chart(fig_prof, use_container_width=True, key="waterfall_chart")

# --- COMPARISON SECTION ---
if st.session_state.saved_scenarios:
    st.divider()
    st.header("📈 Scenario Comparison")
    
    # Create DataFrame from scenarios
    cdf = pd.DataFrame(st.session_state.saved_scenarios)
    
    # Display Data Table
    st.dataframe(cdf.style.format({
        "Price": "${:.2f}",
        "Revenue": "${:,.2f}",
        "Total Cost": "${:,.2f}",
        "Net Profit": "${:,.2f}",
        "Margin": "{:.1f}%",
        "Break-even Units": "{:.0f}"
    }), use_container_width=True)
    
    # Comparison Charts
    c_col1, c_col2 = st.columns(2)
    
    with c_col1:
        # Revenue comparison using graph_objects
        fig_comp_rev = go.Figure()
        fig_comp_rev.add_trace(go.Bar(
            x=cdf["Name"],
            y=cdf["Revenue"],
            marker_color='#10b981',
            text=cdf["Revenue"],
            texttemplate='$%{text:,.0f}',
            textposition='outside'
        ))
        fig_comp_rev.update_layout(
            title="Revenue Comparison",
            xaxis_title="Scenario",
            yaxis_title="Revenue ($)",
            showlegend=False
        )
        st.plotly_chart(fig_comp_rev, use_container_width=True, key="revenue_comparison")
        
    with c_col2:
        # Net Profit comparison using graph_objects
        fig_comp_prof = go.Figure()
        colors_profit = ['#10b981' if x >= 0 else '#ef4444' for x in cdf["Net Profit"]]
        fig_comp_prof.add_trace(go.Bar(
            x=cdf["Name"],
            y=cdf["Net Profit"],
            marker_color=colors_profit,
            text=cdf["Net Profit"],
            texttemplate='$%{text:,.0f}',
            textposition='outside'
        ))
        fig_comp_prof.update_layout(
            title="Net Profit Comparison",
            xaxis_title="Scenario",
            yaxis_title="Net Profit ($)",
            showlegend=False
        )
        st.plotly_chart(fig_comp_prof, use_container_width=True, key="profit_comparison")
    
    # Clear scenarios button
    if st.button("🗑️ Clear All Scenarios"):
        st.session_state.saved_scenarios = []
        st.rerun()
