
import streamlit as st
import plotly.graph_objs as go
from datetime import date, timedelta, datetime
from niftyindicesscraper import fetch_subindex_types, fetch_indices, fetch_index_data
import numpy as np
import pandas as pd
    


st.set_page_config(page_title="NSE Index Chart", layout="wide")

# Fetch index groups and indices from niftyindicesscraper API
indexgroup = "Total returns Index Values"  # Default, can be changed by user
subindex_types_data = fetch_subindex_types(indexgroup)
if isinstance(subindex_types_data, dict) and "error" in subindex_types_data:
    st.error(f"Error fetching sub-index types: {subindex_types_data['error']}")
    subindex_types = []
else:
    subindex_types = [item["indextype"] for item in subindex_types_data]

st.title("NSE Indices Dashboard")


# Sidebar UI
with st.sidebar:
    st.header("Input Parameters")
    min_dt = date(1990, 1, 1)
    max_dt = date.today()
    from_date = st.date_input("From Date", value=min_dt, min_value=min_dt, max_value=max_dt)
    to_date = st.date_input("To Date", value=date.today(), min_value=min_dt, max_value=max_dt)
    selected_subindex_type = st.selectbox("Sub-Index Type", subindex_types)
    indices_data = fetch_indices(selected_subindex_type, indexgroup)
    if isinstance(indices_data, dict) and "error" in indices_data:
        st.error(f"Error fetching indices: {indices_data['error']}")
        indices_for_type = []
    else:
        indices_for_type = [item["indextype"] for item in indices_data]
    selected_index = st.selectbox("Index", indices_for_type)
    st.markdown("**Select Metrics to Plot**")
    selected_metrics = []
    if st.checkbox("Price"):
        selected_metrics.append("Close Price")
    if st.checkbox("Ratios"):
        selected_metrics.extend(["PB", "PE", "Dividend Yield", "ROE"])
    plot_clicked = st.button("Plot", use_container_width=True)
    st.markdown("**Indices-wide Ratio Analysis**")
    selected_report_groups = st.multiselect("Sub-Index Types for Analysis", subindex_types, default=subindex_types[1])
    report_btn_col, reset_btn_col = st.columns([5, 1])
    with report_btn_col:
        generate_report = st.button("Generate Reports", use_container_width=True)
    with reset_btn_col:
        reset_clicked = st.button("🔄", help="Reset. Click here before changing index subtypes and generating reports once again", use_container_width=True)

# Plotting logic using API
if plot_clicked:
    info_msg = st.info("Fetching index data...")
    # Fetch price data
    price_data = fetch_index_data(selected_index, start_date=from_date.strftime("%d-%b-%Y"), end_date=to_date.strftime("%d-%b-%Y"), indexgroup=indexgroup)
    # If ratios are selected, fetch those too
    ratios_data = None
    if any(m in selected_metrics for m in ["PB", "PE", "Dividend Yield", "ROE"]):
        ratios_data = fetch_index_data(selected_index, start_date=from_date.strftime("%d-%b-%Y"), end_date=to_date.strftime("%d-%b-%Y"), indexgroup="P/E, P/B & Div.Yield values")
    # Remove the info message after data is fetched
    info_msg.empty()

    # Parse and clean price data
    import json
    price_data_parsed = price_data
    if isinstance(price_data, str):
        try:
            price_data_parsed = json.loads(price_data)
        except Exception:
            price_data_parsed = []
    price_data_clean = [p for p in price_data_parsed if isinstance(p, dict)]
    def parse_date(d):
        try:
            return datetime.strptime(d, "%d %b %Y")
        except Exception:
            return datetime.strptime(d, "%d-%b-%Y")
    price_data_clean.sort(key=lambda p: parse_date(p.get("Date") or p.get("DATE")))
    x = [p.get("Date") or p.get("DATE") for p in price_data_clean]
    close_price = [float(p.get("TotalReturnsIndex") or p.get("EOD_CLOSE_INDEX_VAL") or np.nan) for p in price_data_clean]
    pb, pe, dy, roe = [], [], [], []
    ratios_data_clean = []
    if ratios_data:
        ratios_data_parsed = ratios_data
        if isinstance(ratios_data, str):
            try:
                ratios_data_parsed = json.loads(ratios_data)
            except Exception:
                ratios_data_parsed = []
        ratios_data_clean = [r for r in ratios_data_parsed if isinstance(r, dict)]
        def parse_ratio_date(d):
            try:
                return datetime.strptime(d, "%d %b %Y")
            except Exception:
                return datetime.strptime(d, "%d-%b-%Y")
        ratios_data_clean.sort(key=lambda r: parse_ratio_date(r.get("DATE") or r.get("Date")))
        ratio_by_date = {str((r.get("DATE") or r.get("Date")).strip().lower()): r for r in ratios_data_clean if r.get("DATE") or r.get("Date")}
        pb, pe, dy, roe = [], [], [], []
        for ts in x:
            ts_key = str(ts).strip().lower()
            r = ratio_by_date.get(ts_key, None)
            pb_val = r.get("pb") if r else None
            pe_val = r.get("pe") if r else None
            dy_val = r.get("divYield") if r else None
            try:
                pb.append(float(pb_val) if pb_val not in [None, ""] else np.nan)
            except Exception:
                pb.append(np.nan)
            try:
                pe.append(float(pe_val) if pe_val not in [None, ""] else np.nan)
            except Exception:
                pe.append(np.nan)
            try:
                dy.append(float(dy_val) if dy_val not in [None, ""] else np.nan)
            except Exception:
                dy.append(np.nan)
            try:
                roe_val = (float(pb_val)/float(pe_val)*100) if pb_val and pe_val and float(pe_val) != 0 else np.nan
            except Exception:
                roe_val = np.nan
            roe.append(roe_val)

    # Defensive: Only plot if there is data
    if not price_data or (isinstance(price_data, dict) and "error" in price_data):
        st.error(f"No price data available or error: {price_data.get('error', 'Unknown error')}")
    else:
        # Use cleaned and parsed data from debug block
        traces = []
        if "Close Price" in selected_metrics:
            traces.append(go.Scatter(
                x=x, y=close_price, mode="lines", name="Close Price",
                hoverinfo="x+y", line=dict(width=1.5), yaxis="y1"
            ))
        # Use previously computed pb, pe, dy, roe and x_aligned from debug block
        if 'pb' in locals() and pb:
            traces.append(go.Scatter(x=x, y=pb, mode="lines", name="PB", yaxis="y2"))
        if 'pe' in locals() and pe:
            traces.append(go.Scatter(x=x, y=pe, mode="lines", name="PE", yaxis="y3"))
        if 'dy' in locals() and dy:
            traces.append(go.Scatter(x=x, y=dy, mode="lines", name="Dividend Yield", yaxis="y4"))
        if 'roe' in locals() and roe:
            traces.append(go.Scatter(x=x, y=roe, mode="lines", name="ROE", yaxis="y5"))

    # Build figure
    fig = go.Figure(traces)
    # Limit x-axis ticks to 8 evenly spaced dates
    num_ticks = 8
    if len(x) > 1:
        step = max(1, len(x) // (num_ticks - 1))
        tick_idxs = list(range(0, len(x), step))
        if tick_idxs[-1] != len(x) - 1:
            tick_idxs.append(len(x) - 1)
        tickvals = [x[i] for i in tick_idxs]
        ticktext = tickvals
    else:
        tickvals = x
        ticktext = x
    fig.update_layout(
        title=f"{selected_index} ({selected_subindex_type})",
        xaxis=dict(title="Date", domain=[0, 1], anchor="y1", tickmode="array", tickvals=tickvals, ticktext=ticktext),
        yaxis=dict(title="Close Price", side="left", showgrid=True, anchor="x"),
        yaxis2=dict(title="PB", overlaying="y", side="right", anchor="x", position=1.0, showgrid=False, showticklabels=True),
        yaxis3=dict(title="PE", overlaying="y", side="right", anchor="x", position=0.995, showgrid=False, showticklabels=True),
        yaxis4=dict(title="Dividend Yield", overlaying="y", side="right", anchor="x", position=0.99, showgrid=False, showticklabels=True),
        yaxis5=dict(title="ROE", overlaying="y", side="right", anchor="x", position=0.985, showgrid=False, showticklabels=True),
        hovermode="x unified",
        legend_title="Metric",
        legend=dict(orientation="h", yanchor="top", y=1.08, xanchor="center", x=0.5),
        template="plotly_white"
    )
    fig.update_yaxes(autorange=True)
    st.plotly_chart(fig, use_container_width=True)

    # Ratio statistics
    ratio_stats = []
    ratio_labels = ["Close Price", "PB", "PE", "Dividend Yield", "ROE"]
    ratio_sources = {
        "Close Price": close_price,
        "PB": pb if pb else [],
        "PE": pe if pe else [],
        "Dividend Yield": dy if dy else [],
        "ROE": roe if roe else []
    }
    for label in ratio_labels:
        values = np.array([float(v) if v not in [None, ""] else np.nan for v in ratio_sources[label]])
        dates = np.array(x)
        if len(values) == 0 or np.all(np.isnan(values)):
            ratio_stats.append({
                "Metric": label,
                "High": None, "High Date": None,
                "Low": None, "Low Date": None,
                "Median": None,
                "Mean": None,
                "Latest": None
            })
            continue
        high_idx = np.nanargmax(values)
        low_idx = np.nanargmin(values)
        latest_idx = len(values) - 1 if len(values) > 0 else None
        ratio_stats.append({
            "Metric": label,
            "High": round(float(values[high_idx]), 4) if not np.isnan(values[high_idx]) else None,
            "High Date": dates[high_idx] if not np.isnan(values[high_idx]) else None,
            "Low": round(float(values[low_idx]), 4) if not np.isnan(values[low_idx]) else None,
            "Low Date": dates[low_idx] if not np.isnan(values[low_idx]) else None,
            "Median": round(float(np.nanmedian(values)), 4) if not np.isnan(np.nanmedian(values)) else None,
            "Mean": round(float(np.nanmean(values)), 4) if not np.isnan(np.nanmean(values)) else None,
            "Latest": round(float(values[latest_idx]), 4) if latest_idx is not None and not np.isnan(values[latest_idx]) else None
        })
    df_stats = pd.DataFrame(ratio_stats)
    st.markdown("### Ratio Statistics")
    st.dataframe(df_stats)

# Reporting logic using API
if st.session_state.get("report_ready", False) or generate_report:
    if generate_report:
        st.session_state.report_ready = True
    if 'reset_clicked' in locals() and reset_clicked:
        st.session_state.report_ready = False
        st.rerun()

    # --- Data Preparation ---
    import json
    reports = {}
    indices_by_subindex = {}
    ratios_by_index = {}
    metric_key_map = {
        "PB": "pb",
        "PE": "pe",
        "Dividend Yield": "divYield",
    }
    for subindex_type in selected_report_groups:
        indices_data = fetch_indices(subindex_type, indexgroup)
        if isinstance(indices_data, dict) and "error" in indices_data:
            st.warning(f"Error fetching indices for {subindex_type}: {indices_data['error']}")
            indices_by_subindex[subindex_type] = []
        else:
            indices_by_subindex[subindex_type] = [item["indextype"] for item in indices_data]
    for subindex_type in selected_report_groups:
        indices_for_type = indices_by_subindex.get(subindex_type, [])
        for idx in indices_for_type:
            ratios_data = fetch_index_data(idx, start_date=from_date.strftime("%d-%b-%Y"), end_date=to_date.strftime("%d-%b-%Y"), indexgroup="P/E, P/B & Div.Yield values")
            if not ratios_data or isinstance(ratios_data, dict):
                st.warning(f"No ratios data for {idx}")
                ratios_by_index[idx] = None
                continue
            ratios_data_parsed = ratios_data
            if isinstance(ratios_data, str):
                try:
                    ratios_data_parsed = json.loads(ratios_data)
                except Exception:
                    st.warning(f"Failed to parse ratios_data for {idx} as JSON string.")
                    ratios_data_parsed = []
            ratios_data_clean = [r for r in ratios_data_parsed if isinstance(r, dict)]
            ratios_by_index[idx] = ratios_data_clean

    ratio_labels = ["PB", "PE", "Dividend Yield", "ROE"]
    sd_options = ["Any", "+1SD", "+2SD", "-1SD", "-2SD"]
    trend_options = ["Any", "Advancing LQ", "Advancing LY", "Declining LQ", "Declining LY"]
    period_map = {"LQ": 90, "LY": 365}
    with st.expander("Advanced Analysis Filters", expanded=False):
        with st.form("advanced_report_form"):
            sd_filter = {}
            trend_filter = {}
            filter_grid = st.columns(len(ratio_labels))
            for i, ratio in enumerate(ratio_labels):
                with filter_grid[i]:
                    sd_filter[ratio] = st.selectbox(f"SD threshold for {ratio}", sd_options, key=f"sd_{ratio}")
            filter_grid2 = st.columns(len(ratio_labels))
            for i, ratio in enumerate(ratio_labels):
                with filter_grid2[i]:
                    trend_filter[ratio] = st.selectbox(f"Trend for {ratio}", trend_options, key=f"trend_{ratio}")
            apply_filters = st.form_submit_button("Apply Advanced Filters")

    # --- Advanced Report Calculation ---
    advanced_rows = []
    for subindex_type in selected_report_groups:
        indices_for_type = indices_by_subindex.get(subindex_type, [])
        for idx in indices_for_type:
            row = {"Index": idx, "Subindex Type": subindex_type}
            for ratio in ratio_labels:
                ratios_data_clean = ratios_by_index.get(idx, None)
                if not ratios_data_clean:
                    row[f"{ratio}_Latest"] = None
                    row[f"{ratio}_Median"] = None
                    row[f"{ratio}_SD"] = None
                    row[f"{ratio}_SD_from_Median"] = None
                    row[f"{ratio}_Trend_LQ"] = None
                    row[f"{ratio}_Trend_LY"] = None
                    continue
                ratio_by_date = {r.get("DATE") or r.get("Date"): r for r in ratios_data_clean}
                dates_sorted = sorted(ratio_by_date.keys(), key=lambda d: datetime.strptime(d, "%d %b %Y") if d else datetime.min)
                metric_series = []
                for d in dates_sorted:
                    if ratio == "ROE":
                        pb_val = ratio_by_date.get(d, {}).get("pb", None)
                        pe_val = ratio_by_date.get(d, {}).get("pe", None)
                        try:
                            pb = float(pb_val) if pb_val not in [None, ""] else np.nan
                            pe = float(pe_val) if pe_val not in [None, "", 0] else np.nan
                            val = pb / pe * 100 if not np.isnan(pb) and not np.isnan(pe) and pe != 0 else np.nan
                        except Exception:
                            val = np.nan
                    else:
                        key = metric_key_map.get(ratio, ratio.lower())
                        val = ratio_by_date.get(d, {}).get(key, None)
                        try:
                            val = float(val) if val not in [None, ""] else np.nan
                        except Exception:
                            val = np.nan
                    metric_series.append(val)
                metric_series = np.array([v if v is not None else np.nan for v in metric_series])
                if len(metric_series) < 2 or np.all(np.isnan(metric_series)):
                    row[f"{ratio}_Latest"] = None
                    row[f"{ratio}_Median"] = None
                    row[f"{ratio}_SD"] = None
                    row[f"{ratio}_SD_from_Median"] = None
                    row[f"{ratio}_Trend_LQ"] = None
                    row[f"{ratio}_Trend_LY"] = None
                    continue
                median = np.nanmedian(metric_series)
                std = np.nanstd(metric_series)
                latest = metric_series[-1]
                sd_from_median = (latest - median) / std if std and not np.isnan(std) else np.nan
                # Trend calculation for LQ and LY
                for period_label, period_n in period_map.items():
                    if len(metric_series) > period_n:
                        start_val = metric_series[-period_n] if not np.isnan(metric_series[-period_n]) else None
                    else:
                        start_val = metric_series[0] if not np.isnan(metric_series[0]) else None
                    trend_val = None
                    if start_val is not None and not np.isnan(latest):
                        if latest > start_val:
                            trend_val = "Advancing"
                        elif latest < start_val:
                            trend_val = "Declining"
                    row[f"{ratio}_Trend_{period_label}"] = trend_val
                row[f"{ratio}_Latest"] = round(float(latest), 4) if not np.isnan(latest) else None
                row[f"{ratio}_Median"] = round(float(median), 4) if not np.isnan(median) else None
                row[f"{ratio}_SD"] = round(float(std), 4) if not np.isnan(std) else None
                row[f"{ratio}_SD_from_Median"] = round(float(sd_from_median), 2) if not np.isnan(sd_from_median) else None
            advanced_rows.append(row)
    df_advanced = pd.DataFrame(advanced_rows)

    # --- Filtering ---
    filtered_df = df_advanced.copy()
    if apply_filters:
        for ratio in ratio_labels:
            sd_val = sd_filter[ratio]
            trend_val = trend_filter[ratio]
            # SD filtering
            if sd_val != "Any":
                if sd_val.startswith("+"):
                    sd_num = int(sd_val[1])
                    filtered_df = filtered_df[filtered_df[f"{ratio}_SD_from_Median"] >= sd_num]
                elif sd_val.startswith("-"):
                    sd_num = int(sd_val[1])
                    filtered_df = filtered_df[filtered_df[f"{ratio}_SD_from_Median"] <= -sd_num]
            # Trend filtering
            if trend_val != "Any":
                if "LQ" in trend_val:
                    period = "LQ"
                else:
                    period = "LY"
                direction = "Advancing" if "Advancing" in trend_val else "Declining"
                filtered_df = filtered_df[filtered_df[f"{ratio}_Trend_{period}"] == direction]

    # --- Presentation ---
    with st.expander("Advanced Filtered Report (All Ratios)", expanded=False):
        st.dataframe(filtered_df)

    st.markdown("## Indices-wide Ratio Snapshot")
    for metric_name in ["ROE", "PE", "PB", "Dividend Yield"]:
        report_rows = []
        for subindex_type in selected_report_groups:
            indices_for_type = indices_by_subindex.get(subindex_type, [])
            for idx in indices_for_type:
                ratios_data_clean = ratios_by_index.get(idx, None)
                if not ratios_data_clean:
                    st.warning(f"No ratios data for {idx}")
                    continue
                ratio_by_date = {r.get("DATE") or r.get("Date"): r for r in ratios_data_clean}
                x = list(ratio_by_date.keys())
                # Find last date with yield data available (non-empty, not None, not '-')
                from_date_val = None
                for ts in reversed(x):
                    val = ratio_by_date.get(ts, {}).get("pe", None)
                    if val not in [None, "", "-"]:
                        from_date_val = ts
                        break
                if metric_name == "ROE":
                    def safe_float(val):
                        if val in [None, "", "-", 0]:
                            return np.nan
                        try:
                            return float(val)
                        except Exception:
                            return np.nan
                    pb_series = [safe_float(ratio_by_date.get(ts, {}).get("pb", np.nan)) for ts in x]
                    pe_series = [safe_float(ratio_by_date.get(ts, {}).get("pe", np.nan)) for ts in x]
                    metric_series = [pb / pe * 100 if not np.isnan(pe) and not np.isnan(pb) and pe != 0 else np.nan for pb, pe in zip(pb_series, pe_series)]
                else:
                    key = metric_key_map.get(metric_name, metric_name.lower())
                    def safe_float(val):
                        if val in [None, "", "-", 0]:
                            return np.nan
                        try:
                            return float(val)
                        except Exception:
                            return np.nan
                    metric_series = [safe_float(ratio_by_date.get(ts, {}).get(key, np.nan)) for ts in x]
                metric_series = np.array([v if v is not None else np.nan for v in metric_series])
                if np.all(np.isnan(metric_series)) or len(metric_series) < 2:
                    st.warning(f"Metric series for {idx} is empty or too short.")
                    continue
                metric_from = metric_series[0]
                metric_to = metric_series[-1]
                metric_median = np.nanmedian(metric_series)
                metric_std = np.nanstd(metric_series)
                report_rows.append({
                    "Index": idx,
                    "from_date": from_date_val,
                    f"{metric_name}_from": round(float(metric_from), 4) if not np.isnan(metric_from) else None,
                    f"{metric_name}_to": round(float(metric_to), 4) if not np.isnan(metric_to) else None,
                    f"{metric_name}_median": round(float(metric_median), 4) if not np.isnan(metric_median) else None,
                    f"{metric_name}_std": round(float(metric_std), 4) if not np.isnan(metric_std) else None,
                })
        df_report = pd.DataFrame(report_rows)
        reports[metric_name] = df_report
    for metric_name in ["ROE", "PE", "PB", "Dividend Yield"]:
        with st.expander(f"{metric_name} Snapshot", expanded=False):
            st.dataframe(reports[metric_name])

# --- Advanced Report Calculation (moved after main reporting logic) ---
    # ...advanced report logic is now handled above, no duplicate or obsolete code...

# --- Advanced Report Calculation ---




