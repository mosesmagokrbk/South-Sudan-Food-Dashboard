"""
WFP SOUTH SUDAN FOOD SECURITY ANALYSIS
Interactive Map with Free Basemap (no token required)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import pydeck as pdk
import requests
import json
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="South Sudan Food Security Dashboard",
    page_icon="🇸🇸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# LOAD & PREPARE DATA
# ============================================================================

@st.cache_data
def load_data():
    df = pd.read_csv("food_prices_ss.csv")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df["usdprice"] = pd.to_numeric(df["usdprice"], errors="coerce")
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["year_month"] = df["date"].dt.to_period("M")
    return df

df = load_data()

# ============================================================================
# CORRECT FOOD BASKET DEFINITION
# ============================================================================

FOOD_BASKET = {
    'Sorghum (white, imported)': 0.65,
    'Maize (white)': 0.15,
    'Beans (red)': 0.10,
    'Groundnuts (shelled)': 0.03,
    'Oil (vegetable)': 0.05,
    'Salt': 0.01,
    'Sugar (brown, imported)': 0.01
}

# ============================================================================
# MARKET LOCATIONS DATABASE (Hardcoded for South Sudan)
# ============================================================================

@st.cache_data
def get_market_locations():
    market_coords = {
        # Central Equatoria
        'Juba': {'lat': 4.8517, 'lon': 31.5825, 'admin1': 'Central Equatoria', 'type': 'Urban'},
        'Yei': {'lat': 4.0944, 'lon': 30.6764, 'admin1': 'Central Equatoria', 'type': 'Urban'},
        'Kajo Keji': {'lat': 3.9833, 'lon': 31.6333, 'admin1': 'Central Equatoria', 'type': 'Rural'},
        # Eastern Equatoria
        'Torit': {'lat': 4.4117, 'lon': 32.5703, 'admin1': 'Eastern Equatoria', 'type': 'Urban'},
        'Kapoeta': {'lat': 4.7725, 'lon': 33.5897, 'admin1': 'Eastern Equatoria', 'type': 'Rural'},
        'Boma': {'lat': 6.2728, 'lon': 33.9183, 'admin1': 'Eastern Equatoria', 'type': 'Rural'},
        'Pochalla': {'lat': 7.1708, 'lon': 34.0931, 'admin1': 'Eastern Equatoria', 'type': 'Rural'},
        # Jonglei
        'Bor': {'lat': 6.2106, 'lon': 31.5647, 'admin1': 'Jonglei', 'type': 'Urban'},
        'Akobo': {'lat': 7.7911, 'lon': 33.0053, 'admin1': 'Jonglei', 'type': 'Rural'},
        'Pibor': {'lat': 6.7958, 'lon': 33.1250, 'admin1': 'Jonglei', 'type': 'Rural'},
        'Fangak': {'lat': 7.3000, 'lon': 31.9000, 'admin1': 'Jonglei', 'type': 'Rural'},
        # Lakes
        'Rumbek': {'lat': 6.8061, 'lon': 29.6767, 'admin1': 'Lakes', 'type': 'Urban'},
        'Yirol': {'lat': 6.5850, 'lon': 30.4311, 'admin1': 'Lakes', 'type': 'Rural'},
        'Awerial': {'lat': 6.5000, 'lon': 30.4333, 'admin1': 'Lakes', 'type': 'Rural'},
        # Unity
        'Bentiu': {'lat': 9.2569, 'lon': 29.7981, 'admin1': 'Unity', 'type': 'Urban'},
        'Rubkona': {'lat': 9.2833, 'lon': 29.8833, 'admin1': 'Unity', 'type': 'Rural'},
        # Upper Nile
        'Malakal': {'lat': 9.5363, 'lon': 31.6561, 'admin1': 'Upper Nile', 'type': 'Urban'},
        'Renk': {'lat': 11.7428, 'lon': 32.8067, 'admin1': 'Upper Nile', 'type': 'Rural'},
        'Melut': {'lat': 10.4372, 'lon': 32.1958, 'admin1': 'Upper Nile', 'type': 'Rural'},
        # Warrap
        'Kuacjok': {'lat': 8.3019, 'lon': 27.9708, 'admin1': 'Warrap', 'type': 'Urban'},
        'Tonj': {'lat': 7.2678, 'lon': 28.6844, 'admin1': 'Warrap', 'type': 'Rural'},
        'Gogrial': {'lat': 8.5333, 'lon': 28.1000, 'admin1': 'Warrap', 'type': 'Rural'},
        # Western Bahr el Ghazal
        'Wau': {'lat': 7.7000, 'lon': 27.9833, 'admin1': 'Western Bahr el Ghazal', 'type': 'Urban'},
        'Raja': {'lat': 8.4667, 'lon': 25.6833, 'admin1': 'Western Bahr el Ghazal', 'type': 'Rural'},
        # Western Equatoria
        'Yambio': {'lat': 4.5714, 'lon': 28.4086, 'admin1': 'Western Equatoria', 'type': 'Urban'},
        'Tambura': {'lat': 5.5667, 'lon': 27.4500, 'admin1': 'Western Equatoria', 'type': 'Rural'},
        'Nzara': {'lat': 4.6425, 'lon': 28.2664, 'admin1': 'Western Equatoria', 'type': 'Rural'},
        'Ezo': {'lat': 5.1167, 'lon': 27.4500, 'admin1': 'Western Equatoria', 'type': 'Rural'},
        # Northern Bahr el Ghazal
        'Aweil': {'lat': 8.7667, 'lon': 27.4000, 'admin1': 'Northern Bahr el Ghazal', 'type': 'Urban'},
    }
    return market_coords

market_coords = get_market_locations()

# ============================================================================
# ENHANCE DATA WITH COORDINATES
# ============================================================================

def enhance_data_with_coordinates(df, market_coords):
    df['latitude'] = df['market'].map(lambda x: market_coords.get(x, {}).get('lat'))
    df['longitude'] = df['market'].map(lambda x: market_coords.get(x, {}).get('lon'))
    df['market_type'] = df['market'].map(lambda x: market_coords.get(x, {}).get('type', 'Unknown'))
    df_enhanced = df.dropna(subset=['latitude', 'longitude']).copy()
    return df_enhanced

df_enhanced = enhance_data_with_coordinates(df, market_coords)

# ============================================================================
# LOAD GEOJSON FOR SOUTH SUDAN BOUNDARIES (multiple sources)
# ============================================================================

@st.cache_data
def load_south_sudan_geojson():
    """
    Try multiple reliable sources for South Sudan boundary GeoJSON.
    Falls back to a simple bounding box if all fail.
    """
    urls = [
        "https://raw.githubusercontent.com/wmgeolab/geoBoundaries/main/releaseData/gbOpen/SSD/ADM0/geoBoundaries-SSD-ADM0.geojson",
        "https://raw.githubusercontent.com/holtzy/D3-graph-gallery/master/DATA/world.geojson",
        "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json"
    ]
    
    for url in urls:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            # Try to parse as JSON
            data = response.json()
            # If it's the world atlas, we need to extract South Sudan
            if url.endswith("countries-110m.json"):
                # Find South Sudan in the features
                features = data.get("features", [])
                for feat in features:
                    if feat.get("properties", {}).get("name") == "South Sudan":
                        return {
                            "type": "FeatureCollection",
                            "features": [feat]
                        }
                # If not found, fall through to next URL
                continue
            # For the other two, they are already FeatureCollections
            return data
        except Exception:
            continue
    
    # If all fail, return approximate bounding box
    st.warning("⚠️ Could not load precise boundary. Using approximate outline.")
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [24.0, 3.5], [36.0, 3.5], [36.0, 12.5], [24.0, 12.5], [24.0, 3.5]
                ]]
            },
            "properties": {"name": "South Sudan (approx.)"}
        }]
    }

south_sudan_geojson = load_south_sudan_geojson()

# ============================================================================
# SIDEBAR FILTERS
# ============================================================================

st.sidebar.title("🎛️ Filters")

years = sorted(df_enhanced["year"].unique())
selected_years = st.sidebar.multiselect(
    "📅 Select Years",
    years,
    default=years
)

states = sorted(df_enhanced["admin1"].dropna().unique())
selected_states = st.sidebar.multiselect(
    "🗺️ Select States",
    states,
    default=states
)

view_type = st.sidebar.radio(
    "📍 Map View Type",
    [
        "Exact Market Locations",
        "National Price Pressure (Heatmap)",
        "Combined View"
    ],
    index=0
)

df_filtered = df_enhanced[
    (df_enhanced["year"].isin(selected_years)) &
    (df_enhanced["admin1"].isin(selected_states))
]

# ============================================================================
# MAIN HEADER
# ============================================================================

st.markdown("""
# 🇸🇸 South Sudan Food Security Dashboard

### Interactive Map – Zoom, Pan, and Hover for Details
""")

# ============================================================================
# TABS
# ============================================================================

tabs = st.tabs([
    "📍 Geographic Analysis",
    "📈 Family Food Cost",
    "📅 Seasonal Pattern",
    "⚠️ Volatility",
    "🚨 Crisis Timeline"
])

# ============================================================================
# TAB 1: ENHANCED GEOGRAPHIC ANALYSIS
# ============================================================================

with tabs[0]:
    st.subheader("🗺️ South Sudan Market Monitoring System")
    
    market_data = (
        df_filtered
        .groupby(['market', 'latitude', 'longitude', 'admin1', 'market_type'])
        .agg({'usdprice': ['mean', 'std', 'count', 'min', 'max']})
        .reset_index()
    )
    market_data.columns = [
        'market', 'latitude', 'longitude', 'admin1', 'market_type',
        'avg_price', 'volatility', 'count', 'min_price', 'max_price'
    ]
    market_data = market_data.dropna(subset=['latitude', 'longitude'])
    
    if len(market_data) == 0:
        st.error("❌ No market data available for selected filters. Please adjust your selections.")
        st.stop()
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Normalize prices for coloring
        min_price = market_data['avg_price'].min()
        max_price = market_data['avg_price'].max()
        price_range = max_price - min_price if max_price > min_price else 1
        market_data['price_norm'] = (market_data['avg_price'] - min_price) / price_range
        
        # Tooltip
        market_data['tooltip_text'] = (
            "🏪 Market: " + market_data['market'] +
            "\n📍 State: " + market_data['admin1'] +
            "\n🏷️ Type: " + market_data['market_type'] +
            "\n💵 Avg Price: $" + market_data['avg_price'].round(2).astype(str) +
            "\n📊 Volatility: " + market_data['volatility'].round(2).astype(str) +
            "\n📈 Records: " + market_data['count'].astype(int).astype(str) +
            "\n🔼 Min Price: $" + market_data['min_price'].round(2).astype(str) +
            "\n🔽 Max Price: $" + market_data['max_price'].round(2).astype(str)
        )
        
        def get_price_color(price_norm):
            if price_norm < 0.33:
                return [97, 153, 34, 200]
            elif price_norm < 0.66:
                return [255, 159, 39, 200]
            else:
                return [232, 75, 74, 200]
        
        market_data['color'] = market_data['price_norm'].apply(get_price_color)
        # Circle size proportional to price
        max_radius = 1000
        min_radius = 200
        market_data['radius'] = min_radius + (market_data['price_norm'] * (max_radius - min_radius))
        
        view_state = pdk.ViewState(
            latitude=7.2,
            longitude=30.2,
            zoom=5.5,
            pitch=0,
            bearing=0
        )
        
        # --- LAYERS ---
        scatterplot_layer = pdk.Layer(
            "ScatterplotLayer",
            data=market_data,
            get_position='[longitude, latitude]',
            get_radius='radius',
            get_fill_color='color',
            get_line_color='[255, 255, 255]',
            line_width_min_pixels=2,
            pickable=True,
            opacity=0.85,
            auto_highlight=True
        )
        
        heatmap_layer = pdk.Layer(
            "HeatmapLayer",
            data=market_data,
            get_position='[longitude, latitude]',
            get_weight='avg_price',
            radius_pixels=60,
            intensity=0.5,
            threshold=0.03,
            color_range=[
                [97, 153, 34],
                [255, 204, 0],
                [255, 159, 39],
                [232, 75, 74],
                [150, 20, 20]
            ]
        )
        
        text_layer = pdk.Layer(
            "TextLayer",
            data=market_data,
            get_position='[longitude, latitude]',
            get_text='market',
            get_color='[255, 255, 255, 200]',
            get_size=12,
            get_alignment_baseline='"bottom"',
            get_pixel_offset='[0, -20]',
            get_text_anchor='"middle"',
            font_family='"Arial"'
        )
        
        # Boundary layer
        boundary_layer = pdk.Layer(
            "GeoJsonLayer",
            data=south_sudan_geojson,
            opacity=0.6,
            stroked=True,
            filled=False,
            get_line_color=[50, 50, 50],
            line_width_min_pixels=2,
            get_line_width=2,
            pickable=False
        )
        
        # Assemble layers
        layers = [boundary_layer]  # always show outline
        if view_type in ["Exact Market Locations", "Combined View"]:
            layers.append(scatterplot_layer)
            layers.append(text_layer)
        if view_type in ["National Price Pressure (Heatmap)", "Combined View"]:
            layers.append(heatmap_layer)
        
        # ============================================================
        # 🗺️  Use a token‑free map style (light)
        # ============================================================
        deck = pdk.Deck(
            map_style='light',          # no token required
            initial_view_state=view_state,
            layers=layers,
            tooltip={"text": "{tooltip_text}"}
        )
        
        st.pydeck_chart(deck, use_container_width=True)
        
        # Legend
        col_legend1, col_legend2, col_legend3, col_legend4 = st.columns(4)
        with col_legend1:
            st.markdown("🟢 **Affordable** (Lowest 33%)")
        with col_legend2:
            st.markdown("🟠 **Moderate** (Mid 33%)")
        with col_legend3:
            st.markdown("🔴 **Crisis** (Top 33%)")
        with col_legend4:
            st.markdown(f"📊 **{len(market_data)}** markets displayed")
        
        # Data table
        st.markdown("### 📋 Market Details with Coordinates")
        display_df = market_data[['market', 'admin1', 'market_type', 'latitude', 'longitude', 
                                'avg_price', 'volatility', 'count', 'min_price', 'max_price']].copy()
        display_df.columns = ['Market', 'State', 'Type', 'Latitude', 'Longitude', 
                            'Avg Price ($)', 'Volatility', 'Records', 'Min Price', 'Max Price']
        display_df = display_df.sort_values('Avg Price ($)', ascending=False).round(2)
        st.dataframe(display_df, use_container_width=True)
        
        csv = display_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Market Data (CSV)",
            data=csv,
            file_name="south_sudan_market_data.csv",
            mime="text/csv"
        )
    
    with col2:
        st.markdown("#### 📊 Price Statistics")
        st.metric("🔴 Highest Price", f"${market_data['avg_price'].max():.2f}")
        st.metric("🟢 Lowest Price", f"${market_data['avg_price'].min():.2f}")
        st.metric("📈 Average Price", f"${market_data['avg_price'].mean():.2f}")
        st.metric("📊 Price Range", f"${market_data['avg_price'].max() - market_data['avg_price'].min():.2f}")
        st.divider()
        st.markdown("#### 🎯 Top 5 Expensive Markets")
        top_markets = market_data.nlargest(5, 'avg_price')[['market', 'admin1', 'avg_price']]
        for _, row in top_markets.iterrows():
            st.write(f"**{row['market']}** ({row['admin1']})")
            st.write(f"💵 ${row['avg_price']:.2f}")
            st.divider()
        st.markdown("#### 📍 Market Type Distribution")
        type_counts = market_data['market_type'].value_counts()
        for mtype, count in type_counts.items():
            st.write(f"• {mtype}: {count} markets")
        st.divider()
        st.markdown("#### 🗺️ Covered States")
        states_covered = market_data['admin1'].nunique()
        st.metric("States", f"{states_covered}/{len(selected_states)}")

# ============================================================================
# TAB 2: FOOD BASKET COST
# ============================================================================

with tabs[1]:
    st.subheader("📈 Family Food Basket Cost")
    st.info("""
    **Food Basket Composition:**
    - Sorghum (white, imported): 65% 
    - Maize (white): 15%
    - Beans (red): 10%
    - Groundnuts (shelled): 3%
    - Oil (vegetable): 5%
    - Salt: 1%
    - Sugar (brown, imported): 1%
    """)
    basket_df = df_filtered[df_filtered['commodity'].isin(FOOD_BASKET.keys())]
    if len(basket_df) == 0:
        st.warning("No data available for the selected food basket items. Please adjust filters.")
    else:
        monthly_prices = (
            basket_df
            .groupby(['year_month', 'commodity'])['usdprice']
            .mean()
            .reset_index()
        )
        pivot = monthly_prices.pivot(index='year_month', columns='commodity', values='usdprice')
        weighted = pivot.copy()
        for commodity, weight in FOOD_BASKET.items():
            if commodity in weighted.columns:
                weighted[commodity] = weighted[commodity] * weight
        weighted['basket_cost'] = weighted[list(FOOD_BASKET.keys())].sum(axis=1)
        weighted = weighted.reset_index()
        weighted['month_str'] = weighted['year_month'].astype(str)
        fig = px.line(
            weighted,
            x='month_str',
            y='basket_cost',
            title='Family Food Basket Cost Over Time (Corrected Weights)',
            markers=True,
            line_shape='spline'
        )
        fig.update_layout(height=400, template='plotly_white')
        st.plotly_chart(fig, use_container_width=True)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Current", f"${weighted['basket_cost'].iloc[-1]:.2f}")
        with col2:
            st.metric("Average", f"${weighted['basket_cost'].mean():.2f}")
        with col3:
            st.metric("Min", f"${weighted['basket_cost'].min():.2f}")
        with col4:
            st.metric("Max", f"${weighted['basket_cost'].max():.2f}")

# ============================================================================
# TAB 3: SEASONALITY
# ============================================================================

with tabs[2]:
    st.subheader("📅 Seasonal Pattern")
    seasonal = df_filtered[df_filtered['commodity'].isin(FOOD_BASKET.keys())].groupby('month').agg({
        'usdprice': ['mean', 'std', 'min', 'max']
    }).reset_index()
    seasonal.columns = ['month', 'avg_price', 'std_dev', 'min_price', 'max_price']
    month_names = {1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
                   7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}
    seasonal['month_name'] = seasonal['month'].map(month_names)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=seasonal['month_name'],
        y=seasonal['avg_price'],
        marker_color=['#e84c3d' if x > seasonal['avg_price'].mean() else '#61992a' for x in seasonal['avg_price']]
    ))
    fig.update_layout(title='Average Prices by Month', height=400, template='plotly_white')
    st.plotly_chart(fig, use_container_width=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🔴 Hardest Months")
        for _, row in seasonal.nlargest(3, 'avg_price').iterrows():
            st.write(f"• {row['month_name']}: ${row['avg_price']:.2f}")
    with col2:
        st.markdown("#### 🟢 Easiest Months")
        for _, row in seasonal.nsmallest(3, 'avg_price').iterrows():
            st.write(f"• {row['month_name']}: ${row['avg_price']:.2f}")

# ============================================================================
# TAB 4: VOLATILITY
# ============================================================================

with tabs[3]:
    st.subheader("⚠️ Commodity Volatility")
    volatility = df_filtered.groupby('commodity').agg({
        'usdprice': ['mean', 'std']
    }).reset_index()
    volatility.columns = ['commodity', 'mean_price', 'std_dev']
    volatility['cv'] = (volatility['std_dev'] / volatility['mean_price'] * 100).round(1)
    volatility = volatility.sort_values('cv', ascending=False)
    fig = px.bar(volatility.head(10), x='cv', y='commodity', orientation='h',
                 color='cv', color_continuous_scale=['#61992a', '#ff9f27', '#e84c3d'])
    fig.update_layout(height=400, template='plotly_white')
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(volatility[['commodity', 'mean_price', 'std_dev', 'cv']], use_container_width=True)

# ============================================================================
# TAB 5: CRISIS TIMELINE
# ============================================================================

with tabs[4]:
    st.subheader("🚨 Crisis Timeline")
    monthly = df_filtered.groupby('year_month')['usdprice'].mean().reset_index()
    monthly['month_str'] = monthly['year_month'].astype(str)
    monthly.columns = ['month', 'price', 'month_str']
    monthly['mom_change'] = monthly['price'].pct_change() * 100
    monthly['crisis_flag'] = monthly['mom_change'].abs() > 15
    crisis = monthly[monthly['crisis_flag']]
    non_crisis = monthly[~monthly['crisis_flag']]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=non_crisis['month_str'], y=non_crisis['mom_change'], name='Normal', marker_color='#61992a'))
    fig.add_trace(go.Bar(x=crisis['month_str'], y=crisis['mom_change'], name='Crisis', marker_color='#e84c3d'))
    fig.update_layout(title='Month-over-Month Price Changes', height=400, template='plotly_white', barmode='group')
    st.plotly_chart(fig, use_container_width=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Crisis Months", f"{len(crisis)}/{len(monthly)}")
    with col2:
        st.metric("Worst Shock", f"{monthly['mom_change'].abs().max():.1f}%")
    with col3:
        st.metric("Avg Crisis", f"{crisis['mom_change'].abs().mean():.1f}%")

# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.markdown("""
<div style='text-align: center; color: #666; font-size: 12px;'>
<p>WFP Food Security Analysis Dashboard | Interactive Map with Market Locations</p>
<p>Data Source: WFP Food Prices Database | South Sudan (2006-2026)</p>
<p>Food Basket Weights: Sorghum 65% | Maize 15% | Beans 10% | Groundnuts 3% | Oil 5% | Salt 1% | Sugar 1%</p>
</div>
""", unsafe_allow_html=True)