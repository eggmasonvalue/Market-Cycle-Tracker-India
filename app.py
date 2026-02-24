import logging
import streamlit as st
import pandas as pd
from datetime import date, timedelta

from src.data.client import get_subindex_types, get_indices, get_index_data
from src.processing.analysis import process_index_data, calculate_stats, calculate_trend
from src.ui.views import render_main_chart, render_metric_cards, render_ratio_analysis, render_screener
from src.ui.styles import load_css
from src.utils.constants import DEFAULT_INDEX_GROUP, DATE_FMT_API

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="NSE Cycles Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    load_css()

    st.title("NSE Indices Cycle Tracker")
    st.markdown("Track market cycles using historical valuation ratios (PE, PB, Dividend Yield, ROE).")

    # --- Sidebar ---
    with st.sidebar:
        st.header("Settings")

        # Date Range
        min_dt = date(1990, 1, 1)
        max_dt = date.today()

        col1, col2 = st.columns(2)
        with col1:
            from_date = st.date_input("From", value=min_dt, min_value=min_dt, max_value=max_dt)
        with col2:
            to_date = st.date_input("To", value=max_dt, min_value=min_dt, max_value=max_dt)

        st.divider()

        # Navigation
        view_mode = st.radio("View Mode", ["Deep Dive", "Screener"], index=0)

        st.divider()

        # Index Selection
        index_group = DEFAULT_INDEX_GROUP # Or allow user to select if needed
        subindex_types = get_subindex_types(index_group)

        selected_subindex_type = st.selectbox("Market Segment", subindex_types)

        indices = get_indices(selected_subindex_type, index_group) if selected_subindex_type else []

        if view_mode == "Deep Dive":
            selected_index = st.selectbox("Select Index", indices)

            st.divider()
            st.markdown("**Chart Metrics**")
            show_price = st.checkbox("Price", value=True)
            show_pe = st.checkbox("P/E Ratio", value=True)
            show_pb = st.checkbox("P/B Ratio", value=False)
            show_div = st.checkbox("Dividend Yield", value=False)
            show_roe = st.checkbox("ROE", value=False)

            selected_metrics = []
            if show_price: selected_metrics.append("close")
            if show_pe: selected_metrics.append("pe")
            if show_pb: selected_metrics.append("pb")
            if show_div: selected_metrics.append("div_yield")
            if show_roe: selected_metrics.append("roe")

        else:
            # Screener settings
            st.info("Screener analyzes all indices in the selected segment.")
            selected_index = None
            selected_metrics = []

    # --- Main Content ---

    if view_mode == "Deep Dive" and selected_index:
        st.subheader(f"{selected_index} Analysis")

        with st.spinner("Fetching data..."):
            # Fetch data
            start_str = from_date.strftime(DATE_FMT_API)
            end_str = to_date.strftime(DATE_FMT_API)

            price_raw = get_index_data(selected_index, start_str, end_str, "Total returns Index Values")
            ratios_raw = get_index_data(selected_index, start_str, end_str, "P/E, P/B & Div.Yield values")

            df = process_index_data(price_raw, ratios_raw)

        if df.empty:
            st.error("No data found for the selected index and date range.")
            return

        # Metrics Summary
        render_metric_cards(df, ["close", "pe", "pb", "div_yield", "roe"])

        st.markdown("---")

        # Main Chart
        render_main_chart(df, selected_metrics)

        st.markdown("### Cycle Analysis")
        tab1, tab2, tab3, tab4 = st.tabs(["P/E Ratio", "P/B Ratio", "Dividend Yield", "ROE"])

        with tab1:
            render_ratio_analysis(df, "pe")
        with tab2:
            render_ratio_analysis(df, "pb")
        with tab3:
            render_ratio_analysis(df, "div_yield")
        with tab4:
            render_ratio_analysis(df, "roe")

    elif view_mode == "Screener":
        st.subheader(f"Market Screener: {selected_subindex_type}")

        if st.button("Run Screener"):
            with st.spinner(f"Analyzing {len(indices)} indices... This may take a moment."):
                screener_data = []
                start_str = from_date.strftime(DATE_FMT_API)
                end_str = to_date.strftime(DATE_FMT_API)

                # Progress bar
                progress_bar = st.progress(0)

                for i, idx in enumerate(indices):
                    # Fetch only necessary data (maybe only last year for efficiency?)
                    # But user selected date range. stick to it.
                    # Optimization: Maybe fetch shorter range if range is huge?
                    # For accurate percentiles, we need history.

                    ratios_raw = get_index_data(idx, start_str, end_str, "P/E, P/B & Div.Yield values")
                    # We might not need price for screener unless we want price trend
                    # But let's keep it simple and skip price fetch for speed if only ratios needed
                    # However, process_index_data expects price_data usually for dates?
                    # process_index_data handles missing price data gracefully.

                    df = process_index_data([], ratios_raw)

                    if not df.empty:
                        latest = df.iloc[-1]

                        # Calculate simple stats
                        pe_stats = calculate_stats(df["pe"])
                        pb_stats = calculate_stats(df["pb"])
                        div_stats = calculate_stats(df["div_yield"])
                        roe_stats = calculate_stats(df["roe"]) if "roe" in df.columns else {}

                        row = {
                            "Index": idx,
                            "Subindex Type": selected_subindex_type,

                            "pe_latest": latest.get("pe"),
                            "pe_median": pe_stats.get("median"),
                            "pe_z": pe_stats.get("z_score"),

                            "pb_latest": latest.get("pb"),
                            "pb_median": pb_stats.get("median"),
                            "pb_z": pb_stats.get("z_score"),

                            "div_yield_latest": latest.get("div_yield"),
                            "div_yield_median": div_stats.get("median"),

                            "roe_latest": latest.get("roe"),
                            "roe_median": roe_stats.get("median"),
                        }
                        screener_data.append(row)

                    progress_bar.progress((i + 1) / len(indices))

                screener_df = pd.DataFrame(screener_data)
                render_screener(screener_df)

if __name__ == "__main__":
    main()
