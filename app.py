import streamlit as st
import pandas as pd
import plotly.express as px
from functools import reduce

# Set page title and layout
st.set_page_config(page_title="AD Campaign Dashboard", layout="wide")

# Sidebar - Company Logo
logo_path = "logo.png"
try:
    st.sidebar.image(logo_path, use_container_width=True)
except FileNotFoundError:
    st.sidebar.warning("⚠️ Logo not found! Ensure 'logo.png' is in the correct folder.")

# Sidebar - File Uploader
st.sidebar.header("Upload Data")
uploaded_file = st.sidebar.file_uploader("Upload your master_data (CSV or Parquet)", type=["csv", "parquet"])

# Sidebar - Page Selector
page = st.sidebar.radio("Select Page", ["AD Campaign Dashboard", "Metrics Charts"])

@st.cache_data
def load_data(file):
    """Loads and processes the dataset efficiently."""
    if file.name.endswith(".parquet"):
        df = pd.read_parquet(file)
    else:
        df = pd.read_csv(
            file,
            parse_dates=["WE Date"],
            dayfirst=True,
            usecols=["WE Date", "Product", "Portfolio Name", "Match Type", "RTW/Prospecting", 
                     "Sales", "Spend", "Units", "Impressions", "Clicks", "Click-through Rate", 
                     "Conversion Rate", "CPC", "ROAS"],  
            dtype={"Product": "category", "Portfolio Name": "category", "Match Type": "category",
                   "RTW/Prospecting": "category"}  
        )
    return df

if uploaded_file is not None:
    df = load_data(uploaded_file)
    st.sidebar.success("✅ File uploaded successfully!")
else:
    st.warning("⚠ Please upload a CSV or Parquet file to continue.")
    st.stop()

def apply_filters(data, key_prefix=""):
    """Applies common filters to the dataset."""
    with st.expander("🔍 **Show/Hide Filters**", expanded=True):
        st.subheader("Filter Options")
        filters = {}
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            product_options = ["All"] + sorted(data["Product"].cat.categories)
            selected_product = st.selectbox("Select Product Category", product_options, key=f"{key_prefix}_product")
            if selected_product != "All":
                filters["Product"] = selected_product

        with col2:
            portfolio_options = ["All"] + sorted(data["Portfolio Name"].cat.categories)
            selected_portfolio = st.selectbox("Select Portfolio Name", portfolio_options, key=f"{key_prefix}_portfolio")
            if selected_portfolio != "All":
                filters["Portfolio Name"] = selected_portfolio

        with col3:
            match_type_options = ["All"] + sorted(data["Match Type"].cat.categories)
            selected_match_type = st.selectbox("Select Match Type", match_type_options, key=f"{key_prefix}_match_type")
            if selected_match_type != "All":
                filters["Match Type"] = selected_match_type

        with col4:
            rtw_options = ["All"] + sorted(data["RTW/Prospecting"].cat.categories)
            selected_rtw = st.selectbox("Select RTW/Prospecting", rtw_options, key=f"{key_prefix}_rtw")
            if selected_rtw != "All":
                filters["RTW/Prospecting"] = selected_rtw

        for col, val in filters.items():
            data = data[data[col] == val]

        return data

def aggregate_data(df, selected_metrics):
    """Aggregates data correctly as per original logic."""
    sum_metrics = ["Sales", "Spend", "Units", "Impressions", "Clicks"]
    median_metrics = ["Click-through Rate", "Conversion Rate", "CPC", "ROAS"]
    
    agg_dfs = []
    
    for metric in selected_metrics:
        if metric in sum_metrics:
            temp = df.groupby("WE Date").agg({metric: "sum"}).reset_index()
        elif metric in median_metrics:
            temp = df[df[metric] > 0].groupby("WE Date").agg({metric: "median"}).reset_index()
        agg_dfs.append(temp)
    
    if agg_dfs:
        agg_df = reduce(lambda left, right: pd.merge(left, right, on="WE Date", how="outer"), agg_dfs)
    else:
        agg_df = pd.DataFrame()
    
    return agg_df

def plot_metric(df, selected_metrics):
    """Plots multiple metrics on the same chart with unified tooltips and y-axis starting from 0."""
    fig = px.line(df, x="WE Date", y=selected_metrics, markers=True, title="Trend Over Time")

    # Set y-axis to start from 0
    fig.update_layout(
        xaxis_title="Week Ending Date",
        yaxis_title="Value",
        hovermode="x unified",
        legend_title="Metrics",
        yaxis=dict(range=[0, max(df[selected_metrics].max()) * 1.1])  # Ensures y-axis starts at 0
    )
    return fig

if page == "AD Campaign Dashboard":
    st.title("📊 AD Campaign Dashboard")
    st.info("This is the main dashboard. For detailed metric charts, select 'Metrics Charts' from the sidebar.")

elif page == "Metrics Charts":
    st.title("📈 Metrics Charts")
    
    # Create tabs for different metrics
    tab_names = ["General", "Impressions", "Clicks", "Click-through Rate", "Conversion Rate", "CPC", "ROAS"]
    tabs = st.tabs(tab_names)

    # General Tab
    with tabs[0]:
        st.header("General Metrics Overview")
        filtered_df = apply_filters(df, key_prefix="general")
        selected_metrics = st.multiselect(
            "Select Metrics to Visualize",
            ["Sales", "Spend", "Units", "Click-through Rate", "Conversion Rate", "CPC", "ROAS"],
            default=["Sales", "Spend"]
        )

        if selected_metrics:
            agg_df = aggregate_data(filtered_df, selected_metrics)
            st.plotly_chart(plot_metric(agg_df, selected_metrics), use_container_width=True)
        else:
            st.warning("⚠ Please select at least one metric.")

    # Impressions Tab
    with tabs[1]:
        st.header("Impressions")
        filtered_df = apply_filters(df, key_prefix="impressions")
        agg_df = filtered_df.groupby("WE Date").agg({"Impressions": "sum"}).reset_index()

        if agg_df.empty:
            st.warning("⚠ No data available for the selected filters.")
        else:
            st.plotly_chart(plot_metric(agg_df, ["Impressions"]), use_container_width=True)

    # Clicks Tab
    with tabs[2]:
        st.header("Clicks")
        filtered_df = apply_filters(df, key_prefix="clicks")
        agg_df = filtered_df.groupby("WE Date").agg({"Clicks": "sum"}).reset_index()

        if agg_df.empty:
            st.warning("⚠ No data available for the selected filters.")
        else:
            st.plotly_chart(plot_metric(agg_df, ["Clicks"]), use_container_width=True)

    # Other Metrics Tabs
    for metric, tab in zip(["Click-through Rate", "Conversion Rate", "CPC", "ROAS"], tabs[3:]):
        with tab:
            st.header(metric)
            filtered_df = apply_filters(df, key_prefix=metric.lower().replace(" ", "_"))
            filtered_df = filtered_df[filtered_df[metric] > 0]
            agg_df = filtered_df.groupby("WE Date").agg({metric: "median"}).reset_index()

            if agg_df.empty:
                st.warning(f"⚠ No data available for {metric} after filtering.")
            else:
                st.plotly_chart(plot_metric(agg_df, [metric]), use_container_width=True)
