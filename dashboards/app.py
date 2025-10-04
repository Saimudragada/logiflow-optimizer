"""
LogiFlow - Interactive Dashboard
Supply Chain Network Optimization Visualization
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Page config
st.set_page_config(
    page_title="LogiFlow Optimizer",
    page_icon="🚚",
    layout="wide"
)

# API endpoint
API_URL = "http://localhost:8000"

# ==========================================
# HEADER
# ==========================================

st.title("🚚 LogiFlow Network Optimizer")
st.markdown("### AI-Powered Supply Chain Network Design")
st.markdown("---")

# ==========================================
# SIDEBAR
# ==========================================

st.sidebar.header("📊 Quick Stats")

try:
    response = requests.get(f"{API_URL}/solution")
    if response.status_code == 200:
        solution = response.json()
        
        st.sidebar.metric("Annual Savings", f"${solution['annual_savings']:,.0f}")
        st.sidebar.metric("Cost Reduction", f"{solution['savings_percentage']:.1f}%")
        st.sidebar.metric("Warehouses Needed", solution['num_warehouses'])
        st.sidebar.metric("Total Routes", solution['num_routes'])
    else:
        st.sidebar.warning("Could not connect to API")
except:
    st.sidebar.error("❌ API not running. Start with: `python src/api/main.py`")

st.sidebar.markdown("---")
st.sidebar.markdown("**💡 Business Impact**")
st.sidebar.info("Reduced from 10 to 2 warehouses\nSaving $19.2M annually")

# ==========================================
# MAIN CONTENT
# ==========================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🗺️ Network Map", 
    "💰 Cost Analysis", 
    "📊 Performance Metrics",
    "🔄 Scenario Comparison",
    "📈 Business Impact"
])

# ==========================================
# TAB 1: Network Map
# ==========================================

with tab1:
    st.header("Optimized Network Map")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### Interactive Network Visualization")
        
        # Embed the HTML map
        try:
            with open('network_map.html', 'r') as f:
                map_html = f.read()
            st.components.v1.html(map_html, height=600, scrolling=True)
        except:
            st.warning("Map not found. Generate it first: `python src/visualization/network_map.py`")
            st.info("Or view directly: Open `dashboards/network_map.html` in browser")
    
    with col2:
        st.markdown("### Legend")
        st.markdown("""
        - 🟢 **Open Warehouse** - Selected by optimization
        - ⚪ **Closed Warehouse** - Not selected
        - 🔵 **Customer City** - Demand center
        - 🔴 **Route** - Shipping lane (width = volume)
        """)
        
        try:
            response = requests.get(f"{API_URL}/warehouses")
            if response.status_code == 200:
                warehouses = response.json()['warehouses']
                
                st.markdown("### Open Warehouses")
                for wh in warehouses:
                    if wh['is_open']:
                        st.success(f"✓ {wh['name']}")
                        st.caption(f"Region: {wh['region']}")
        except:
            pass

# ==========================================
# TAB 2: Cost Analysis
# ==========================================

with tab2:
    st.header("Cost Breakdown & Analysis")
    
    try:
        response = requests.get(f"{API_URL}/cost-breakdown")
        if response.status_code == 200:
            cost_data = response.json()
            
            # High-level comparison
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "Baseline Cost",
                    f"${cost_data['baseline_cost']:,.0f}",
                    delta=None
                )
            
            with col2:
                st.metric(
                    "Optimized Cost",
                    f"${cost_data['optimized_cost']:,.0f}",
                    delta=f"-${cost_data['savings']:,.0f}",
                    delta_color="inverse"
                )
            
            with col3:
                savings_pct = (cost_data['savings'] / cost_data['baseline_cost'] * 100)
                st.metric(
                    "Savings",
                    f"${cost_data['savings']:,.0f}",
                    delta=f"{savings_pct:.1f}% reduction"
                )
            
            # Cost breakdown chart
            st.markdown("### Cost Structure")
            
            fig = go.Figure(data=[
                go.Bar(
                    name='Fixed Costs',
                    x=['Optimized'],
                    y=[cost_data['fixed_cost_total']],
                    marker_color='lightblue'
                ),
                go.Bar(
                    name='Variable Costs',
                    x=['Optimized'],
                    y=[cost_data['variable_cost_total']],
                    marker_color='coral'
                )
            ])
            
            fig.update_layout(
                barmode='stack',
                title='Cost Composition',
                yaxis_title='Cost ($)',
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Per-warehouse breakdown
            st.markdown("### Per-Warehouse Analysis")
            wh_df = pd.DataFrame(cost_data['warehouse_breakdown'])
            
            fig2 = px.bar(
                wh_df,
                x='warehouse',
                y=['fixed_cost', 'variable_cost'],
                title='Cost by Warehouse',
                labels={'value': 'Cost ($)', 'variable': 'Cost Type'},
                barmode='stack'
            )
            st.plotly_chart(fig2, use_container_width=True)
            
            # Table
            st.markdown("### Detailed Breakdown")
            st.dataframe(
                wh_df.style.format({
                    'fixed_cost': '${:,.0f}',
                    'variable_cost': '${:,.0f}',
                    'total_cost': '${:,.0f}',
                    'total_shipments': '{:,.0f}'
                }),
                use_container_width=True
            )
            
    except Exception as e:
        st.error(f"Could not load cost data: {str(e)}")

# ==========================================
# TAB 3: Performance Metrics
# ==========================================

with tab3:
    st.header("Network Performance Metrics")
    
    try:
        response = requests.get(f"{API_URL}/metrics")
        if response.status_code == 200:
            metrics = response.json()
            
            # Cost metrics
            st.markdown("### 💰 Cost Metrics")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Annual Savings", f"${metrics['cost_metrics']['annual_savings']:,.0f}")
            with col2:
                st.metric("Savings %", f"{metrics['cost_metrics']['savings_percentage']:.1f}%")
            with col3:
                st.metric("Cost/Shipment", f"${metrics['cost_metrics']['cost_per_shipment']:.2f}")
            with col4:
                st.metric("Optimized Cost", f"${metrics['cost_metrics']['optimized_cost']:,.0f}")
            
            # Network metrics
            st.markdown("### 🏭 Network Metrics")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Warehouses", metrics['network_metrics']['num_warehouses'])
            with col2:
                st.metric("Active Routes", metrics['network_metrics']['num_routes'])
            with col3:
                st.metric("Total Shipments", f"{metrics['network_metrics']['total_shipments']:,.0f}")
            with col4:
                st.metric("Customers Served", metrics['network_metrics']['num_customers_served'])
            
            # Efficiency metrics
            st.markdown("### ⚡ Efficiency Metrics")
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Network Utilization", f"{metrics['efficiency_metrics']['utilization_rate']:.1f}%")
            with col2:
                st.metric("Fixed/Variable Ratio", f"{metrics['efficiency_metrics']['fixed_to_variable_ratio']:.2f}")
            
            # Demand distribution
            st.markdown("### 📍 Demand Distribution")
            demand_response = requests.get(f"{API_URL}/demand")
            if demand_response.status_code == 200:
                demand_data = demand_response.json()
                
                # Regional pie chart
                regional_df = pd.DataFrame([
                    {'region': k, 'demand': v} 
                    for k, v in demand_data['regional_demand'].items()
                ])
                
                fig = px.pie(
                    regional_df,
                    values='demand',
                    names='region',
                    title='Demand by Region'
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Top cities
                st.markdown("### 🌆 Top 10 Cities by Demand")
                cities_df = pd.DataFrame(demand_data['top_cities'])
                
                fig2 = px.bar(
                    cities_df,
                    x='demand',
                    y='city',
                    orientation='h',
                    title='Top Cities'
                )
                st.plotly_chart(fig2, use_container_width=True)
            
    except Exception as e:
        st.error(f"Could not load metrics: {str(e)}")

# ==========================================
# TAB 4: Scenario Comparison
# ==========================================

with tab4:
    st.header("Scenario Analysis: Impact of Warehouse Count")
    
    try:
        response = requests.get(f"{API_URL}/scenarios")
        if response.status_code == 200:
            scenarios = response.json()
            scenario_df = pd.DataFrame(scenarios['scenarios'])
            
            # Line chart
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=scenario_df['max_warehouses'],
                y=scenario_df['total_cost'],
                mode='lines+markers',
                name='Total Cost',
                line=dict(color='red', width=3),
                marker=dict(size=10)
            ))
            
            # Mark optimal
            optimal = scenarios['optimal']
            fig.add_trace(go.Scatter(
                x=[optimal['warehouses']],
                y=[optimal['cost']],
                mode='markers',
                name='Optimal',
                marker=dict(size=20, color='green', symbol='star')
            ))
            
            fig.update_layout(
                title='Cost vs Number of Warehouses',
                xaxis_title='Number of Warehouses',
                yaxis_title='Total Annual Cost ($)',
                height=500
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Optimal solution highlight
            st.success(f"✨ **Optimal Solution:** {optimal['warehouses']} warehouses at ${optimal['cost']:,.0f}/year")
            
            # Data table
            st.markdown("### Scenario Comparison Table")
            st.dataframe(
                scenario_df.style.format({
                    'total_cost': '${:,.0f}',
                    'fixed_cost': '${:,.0f}',
                    'variable_cost': '${:,.0f}'
                }),
                use_container_width=True
            )
            
    except Exception as e:
        st.error(f"Could not load scenarios: {str(e)}")

# ==========================================
# TAB 5: Business Impact
# ==========================================

with tab5:
    st.header("Business Impact & ROI Analysis")
    
    try:
        response = requests.get(f"{API_URL}/solution")
        if response.status_code == 200:
            solution = response.json()
            
            # Key impact metrics
            st.markdown("### 💰 Financial Impact")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Before Optimization")
                st.metric("Annual Cost", f"${solution['baseline_cost']:,.0f}")
                st.metric("Warehouses", "10")
                st.caption("All potential warehouses open")
            
            with col2:
                st.markdown("#### After Optimization")
                st.metric("Annual Cost", f"${solution['optimized_cost']:,.0f}")
                st.metric("Warehouses", solution['num_warehouses'])
                st.caption("Optimized warehouse selection")
            
            # Savings breakdown
            st.markdown("### 📊 Savings Projection")
            
            years = [1, 3, 5, 10]
            annual_savings = solution['annual_savings']
            
            savings_data = {
                'Year': years,
                'Cumulative Savings': [annual_savings * y for y in years]
            }
            
            fig = px.bar(
                savings_data,
                x='Year',
                y='Cumulative Savings',
                title='Cumulative Savings Over Time',
                labels={'Cumulative Savings': 'Total Savings ($)'}
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # ROI calculation
            st.markdown("### 📈 Return on Investment")
            
            implementation_cost = 50000  # Estimated implementation cost
            roi = (annual_savings / implementation_cost) * 100
            payback_months = (implementation_cost / annual_savings) * 12
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Implementation Cost", f"${implementation_cost:,.0f}")
            with col2:
                st.metric("ROI", f"{roi:,.0f}%")
            with col3:
                st.metric("Payback Period", f"{payback_months:.1f} months")
            
            # Business benefits
            st.markdown("### ✨ Key Benefits")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.success(f"""
                **Cost Savings:**
                - Annual: ${annual_savings:,.0f}
                - 5-Year: ${annual_savings * 5:,.0f}
                - Reduction: {solution['savings_percentage']:.1f}%
                """)
            
            with col2:
                st.info("""
                **Operational Benefits:**
                - Simplified network management
                - Reduced fixed overhead
                - Strategic positioning
                - Scalable infrastructure
                """)
            
    except Exception as e:
        st.error(f"Could not load business impact data: {str(e)}")

# ==========================================
# FOOTER
# ==========================================

st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
    <p>🚚 LogiFlow v1.0.0 | Built with PuLP, FastAPI & Streamlit</p>
    <p>Optimizing supply chain networks through AI-powered linear programming</p>
    </div>
    """,
    unsafe_allow_html=True
)