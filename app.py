import streamlit as st
import plotly.graph_objs as go
from nse import NSE
from datetime import date, timedelta, datetime
import sqlite3
import logging

st.set_page_config(page_title="NSE Index Chart", layout="wide")

nse = NSE("d:/Misc2/Index data")

# Fetch index groups and indices from new API
equity_master = nse._NSE__req("https://www.nseindia.com/api/equity-master").json()
keys = [k for k in equity_master.keys() if k.upper() != "OTHERS"]

st.title("NSE Index Interactive Chart")

# Sidebar UI
with st.sidebar:
    st.header("Configure Chart")
    min_dt = date(2015, 1, 1)  # limitation of NSE API for yields is 2015, not the actual inception
    from_date = st.date_input("From Date", value=min_dt, min_value=min_dt)
    to_date = st.date_input("To Date", value=date.today(), min_value=min_dt)
    selected_key = st.selectbox("Index Group", keys)
    indices_for_key = equity_master[selected_key]
    selected_index = st.selectbox("Index", indices_for_key)
    st.markdown("**Select Metrics to Plot**")
    # Replace five checkboxes with two: "Price" and "Ratios"
    selected_metrics = []
    if st.checkbox("Price"):
        selected_metrics.append("Close Price")
    if st.checkbox("Ratios"):
        selected_metrics.extend(["PB", "PE", "Dividend Yield", "ROE"])
    plot_clicked = st.button("Plot", use_container_width=True)
    st.markdown("**Indices-wide Reports**")
    st.warning("Report generation time is proportional to the date range and number of indices. It may take longer for wide ranges.")
    selected_report_groups = st.multiselect("Index Groups for Report (optional)", keys)
    generate_report = st.button("Generate Reports", use_container_width=True)

DB_PATH = "d:/Misc2/Index data/nse_cache.db"

# Database schema summary:
# Table: index_price
#   index_name TEXT
#   date TEXT (ISO format 'YYYY-MM-DD')
#   EOD_CLOSE_INDEX_VAL REAL
#   EOD_TIMESTAMP TEXT
#
# Table: index_yield
#   index_name TEXT
#   date TEXT (ISO format 'YYYY-MM-DD')
#   IY_PB REAL
#   IY_PE REAL
#   IY_DY REAL
#   IY_DT TEXT
#
# Table: index_turnover
#   index_name TEXT
#   date TEXT (ISO format 'YYYY-MM-DD')
#   HIT_TURN_OVER REAL
#   HIT_TIMESTAMP TEXT

def init_db():
    log("Initializing database...")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS index_price (
            index_name TEXT,
            date TEXT, -- ISO format 'YYYY-MM-DD'
            EOD_CLOSE_INDEX_VAL REAL,
            EOD_TIMESTAMP TEXT,
            PRIMARY KEY (index_name, date)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS index_yield (
            index_name TEXT,
            date TEXT, -- ISO format 'YYYY-MM-DD'
            IY_PB REAL,
            IY_PE REAL,
            IY_DY REAL,
            IY_DT TEXT,
            PRIMARY KEY (index_name, date)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS index_turnover (
            index_name TEXT,
            date TEXT, -- ISO format 'YYYY-MM-DD'
            HIT_TURN_OVER REAL,
            HIT_TIMESTAMP TEXT,
            PRIMARY KEY (index_name, date)
        )
    """)
    conn.commit()
    conn.close()
    log("Database initialized.")

def normalize_nse_date(dt_str):
    """Normalize any NSE date string to ISO format '%Y-%m-%d'."""
    for fmt in ("%d-%m-%Y", "%d-%b-%Y", "%d-%B-%Y"):
        try:
            return datetime.strptime(dt_str, fmt).strftime("%Y-%m-%d")
        except Exception:
            continue
    return dt_str  # fallback

def insert_price(index_name, price_data):
    log(f"Inserting price data for {index_name} ({len(price_data)} rows)...")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for p in price_data:
        dt = normalize_nse_date(p["EOD_TIMESTAMP"])
        date_key = dt  # always ISO format
        c.execute("""
            INSERT OR IGNORE INTO index_price (index_name, date, EOD_CLOSE_INDEX_VAL, EOD_TIMESTAMP)
            VALUES (?, ?, ?, ?)
        """, (index_name, date_key, p["EOD_CLOSE_INDEX_VAL"], dt))
    conn.commit()
    conn.close()
    log(f"Inserted price data for {index_name}.")

def insert_yield(index_name, yield_data):
    log(f"Inserting yield data for {index_name} ({len(yield_data)} rows)...")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for y in yield_data:
        dt = normalize_nse_date(y["IY_DT"])
        date_key = dt  # always ISO format
        c.execute("""
            INSERT OR IGNORE INTO index_yield (index_name, date, IY_PB, IY_PE, IY_DY, IY_DT)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (index_name, date_key, y.get("IY_PB"), y.get("IY_PE"), y.get("IY_DY"), dt))
    conn.commit()
    conn.close()
    log(f"Inserted yield data for {index_name}.")

def insert_turnover(index_name, turnover_data):
    log(f"Inserting turnover data for {index_name} ({len(turnover_data)} rows)...")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for t in turnover_data:
        dt = normalize_nse_date(t["HIT_TIMESTAMP"])
        date_key = dt  # always ISO format
        c.execute("""
            INSERT OR IGNORE INTO index_turnover (index_name, date, HIT_TURN_OVER, HIT_TIMESTAMP)
            VALUES (?, ?, ?, ?)
        """, (index_name, date_key, t["HIT_TURN_OVER"], dt))
    conn.commit()
    conn.close()
    log(f"Inserted turnover data for {index_name}.")

def get_cached_price(index_name, from_date, to_date):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    from_str = from_date.strftime("%Y-%m-%d")
    to_str = to_date.strftime("%Y-%m-%d")
    c.execute("""
        SELECT EOD_CLOSE_INDEX_VAL, EOD_TIMESTAMP, date FROM index_price
        WHERE index_name=? AND date BETWEEN ? AND ?
        ORDER BY date(date) ASC
    """, (index_name, from_str, to_str))
    rows = c.fetchall()
    conn.close()
    return [{"EOD_CLOSE_INDEX_VAL": r[0], "EOD_TIMESTAMP": r[1], "date": r[2]} for r in rows]

def get_cached_yield(index_name, from_date, to_date):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    from_str = from_date.strftime("%Y-%m-%d")
    to_str = to_date.strftime("%Y-%m-%d")
    c.execute("""
        SELECT IY_PB, IY_PE, IY_DY, IY_DT, date FROM index_yield
        WHERE index_name=? AND date BETWEEN ? AND ?
        ORDER BY date(date) ASC
    """, (index_name, from_str, to_str))
    rows = c.fetchall()
    conn.close()
    return [{"IY_PB": r[0], "IY_PE": r[1], "IY_DY": r[2], "IY_DT": r[3], "date": r[4]} for r in rows]

def get_cached_turnover(index_name, from_date, to_date):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    from_str = from_date.strftime("%Y-%m-%d")
    to_str = to_date.strftime("%Y-%m-%d")
    c.execute("""
        SELECT HIT_TURN_OVER, HIT_TIMESTAMP, date FROM index_turnover
        WHERE index_name=? AND date BETWEEN ? AND ?
        ORDER BY date(date) ASC
    """, (index_name, from_str, to_str))
    rows = c.fetchall()
    conn.close()
    return [{"HIT_TURN_OVER": r[0], "HIT_TIMESTAMP": r[1], "date": r[2]} for r in rows]

LOG_PATH = "d:/Misc2/Index data/app.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
def log(msg):
    print(msg)
    logging.info(msg)

def find_missing_date_ranges(all_dates, cached_dates):
    """
    Given a list of all dates (as strings) and a set of cached dates (as strings),
    return a list of (start_date, end_date) tuples for contiguous blocks of missing dates.
    Blocks of length <= 4 are ignored (likely weekends/holidays).
    Dates should be in '%d-%m-%Y' format for all_dates, and cached_dates can be '%d-%m-%Y' or '%Y-%m-%d'.
    """
    # Convert all_dates to date objects
    all_dates_dt = [datetime.strptime(d, "%d-%m-%Y").date() for d in all_dates]

    def parse_date_any_format(d):
        for fmt in ("%d-%m-%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(d, fmt).date()
            except Exception:
                continue
        raise ValueError(f"Unknown date format: {d}")

    cached_dates_dt = set(parse_date_any_format(d) for d in cached_dates)
    missing_dates = [d for d in all_dates_dt if d not in cached_dates_dt]
    if not missing_dates:
        return []
    missing_dates.sort()
    ranges = []
    start = prev = missing_dates[0]
    for d in missing_dates[1:]:
        if (d - prev).days == 1:
            prev = d
        else:
            block_len = (prev - start).days + 1
            if block_len > 4:
                ranges.append((start, prev))
            start = prev = d
    # Final block
    block_len = (prev - start).days + 1
    if block_len > 4:
        ranges.append((start, prev))
    return ranges

def split_date_range(from_date, to_date, max_days=100):
    chunks = []
    current_start = from_date
    while current_start <= to_date:
        current_end = min(current_start + timedelta(days=max_days - 1), to_date)
        chunks.append((current_start, current_end))
        current_start = current_end + timedelta(days=1)
    return chunks

init_db()

if plot_clicked:
    log("Plot button clicked. Starting data fetch and plot preparation...")
    cached_price = get_cached_price(selected_index, from_date, to_date)
    cached_yield = get_cached_yield(selected_index, from_date, to_date)
    cached_turnover = get_cached_turnover(selected_index, from_date, to_date)

    log("Checking for missing price data...")
    all_dates = [(from_date + timedelta(days=i)).strftime("%d-%m-%Y") for i in range((to_date - from_date).days + 1)]
    cached_price_dates = set(p["date"] for p in cached_price)
    missing_price_ranges = find_missing_date_ranges(all_dates, cached_price_dates)
    log(f"Missing price ranges: {missing_price_ranges}")

    max_retries = 5
    for fetch_from, fetch_to in missing_price_ranges:
        log(f"Fetching price/turnover data from {fetch_from} to {fetch_to}...")
        for attempt in range(max_retries):
            try:
                hist = nse.fetch_historical_index_data(
                    index=selected_index,
                    from_date=fetch_from,
                    to_date=fetch_to
                )
                log(f"Fetched price/turnover data for {fetch_from} to {fetch_to}.")
                break
            except Exception as e:
                log(f"Error fetching price/turnover data (attempt {attempt+1}): {e}")
                if attempt == max_retries - 1:
                    st.error(f"Failed to fetch historical index data after {max_retries} attempts: {e}")
                    st.stop()
                else:
                    st.warning(f"Retrying fetch_historical_index_data ({attempt+1}/{max_retries}) due to error: {e}")
        insert_price(selected_index, hist.get("price", []))
        insert_turnover(selected_index, hist.get("turnover", []))
    log("Price/turnover data fetch complete. Refreshing cache...")
    cached_price = get_cached_price(selected_index, from_date, to_date)
    cached_turnover = get_cached_turnover(selected_index, from_date, to_date)

    log("Checking for missing yield data...")
    cached_yield_dates = set(y["date"] for y in cached_yield)
    missing_yield_ranges = find_missing_date_ranges(all_dates, cached_yield_dates)
    log(f"Missing yield ranges: {missing_yield_ranges}")
    for fetch_from, fetch_to in missing_yield_ranges:
        log(f"Fetching yield data from {fetch_from} to {fetch_to}...")
        yield_data = []
        for chunk_start, chunk_end in split_date_range(fetch_from, fetch_to, 100):
            for attempt in range(max_retries):
                try:
                    resp = nse._NSE__req(
                        f"https://www.nseindia.com/api/historicalOR/indicesYield",
                        params={
                            "indexType": selected_index,
                            "from": chunk_start.strftime("%d-%m-%Y"),
                            "to": chunk_end.strftime("%d-%m-%Y")
                        }
                    )
                    yield_data += resp.json().get("data", [])
                    log(f"Fetched yield data chunk {chunk_start} to {chunk_end}.")
                    break
                except Exception as e:
                    log(f"Error fetching yield data (attempt {attempt+1}): {e}")
                    if attempt == max_retries - 1:
                        st.error(f"Failed to fetch yield data after {max_retries} attempts: {e}")
                        st.stop()
                    else:
                        st.warning(f"Retrying yield data fetch ({attempt+1}/{max_retries}) due to error: {e}")
        insert_yield(selected_index, yield_data)
    log("Yield data fetch complete. Refreshing cache...")
    cached_yield = get_cached_yield(selected_index, from_date, to_date)

    log("Preparing plot data...")
    price_data = cached_price
    turnover_data = cached_turnover
    yield_data = cached_yield
    # log("Price data:")
    # log(price_data)
    # log("Turnover data:")
    # log(turnover_data)
    # log("Yield data:")
    # log(yield_data)

    yield_by_date = {y["date"]: y for y in yield_data}
    x = [p["date"] for p in price_data]
    traces = []

    log("Building plot traces...")
    # Map metric to y-axis
    metric_yaxis_map = {
        "Close Price": "y1",
        "PB": "y2",
        "PE": "y3",
        "Dividend Yield": "y4",
        "ROE": "y5"
    }

    for metric in selected_metrics:
        if metric == "Close Price":
            y = [p["EOD_CLOSE_INDEX_VAL"] for p in price_data]
        elif metric == "PB":
            y = [yield_by_date.get(ts, {}).get("IY_PB", None) for ts in x]
        elif metric == "PE":
            y = [yield_by_date.get(ts, {}).get("IY_PE", None) for ts in x]
        elif metric == "Dividend Yield":
            y = [yield_by_date.get(ts, {}).get("IY_DY", None) for ts in x]
        elif metric == "ROE":
            y = []
            for ts in x:
                pb = yield_by_date.get(ts, {}).get("IY_PB", None)
                pe = yield_by_date.get(ts, {}).get("IY_PE", None)
                roe = (float(pb)/float(pe)*100) if pb and pe and float(pe) != 0 else None
                y.append(roe)
        traces.append(go.Scatter(
            x=x, y=y, mode="lines", name=metric,
            hoverinfo="x+y", line=dict(width=1.5),
            yaxis=metric_yaxis_map[metric]
        ))

    # Add turnover bar trace at the bottom
    turnover_x = [t["HIT_TIMESTAMP"] for t in turnover_data]
    turnover_y = [t["HIT_TURN_OVER"] for t in turnover_data]
    traces.append(go.Bar(
        x=turnover_x,
        y=turnover_y,
        name="Turnover (Cr)",
        marker_color="rgba(100,100,200,0.4)",
        yaxis="y6",
        xaxis="x2",
        opacity=0.7,
        showlegend=True
    ))

    # Defensive: Only plot if there is data
    if not price_data or not x:
        st.warning("No price data available for the selected index and date range.")
        log("No price data available for plotting.")
    else:
        log("Rendering plot...")
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
            title=f"{selected_index} ({selected_key})",
            xaxis=dict(
                title="Date",
                domain=[0, 1],
                anchor="y1",
                tickmode="array",
                tickvals=tickvals,
                ticktext=ticktext
            ),
            xaxis2=dict(
                title="",
                domain=[0, 1],
                anchor="y6",
                overlaying="x",
                showgrid=False,
                showticklabels=False
            ),
            yaxis=dict(
                title="Close Price",
                side="left",
                showgrid=True,
                anchor="x"
            ),
            yaxis2=dict(
                title_text="",
                overlaying="y",
                side="right",
                anchor="x",
                position=1.0,
                showgrid=False,
                showticklabels=False,
                showline=False,
                ticks="outside",
                ticklabelposition="outside right",
                automargin=True
            ),
            yaxis3=dict(
                title_text="",
                overlaying="y",
                side="right",
                anchor="x",
                position=0.995,
                showgrid=False,
                showticklabels=False,
                showline=False,
                ticks="outside",
                ticklabelposition="outside right",
                automargin=True
            ),
            yaxis4=dict(
                title_text="",
                overlaying="y",
                side="right",
                anchor="x",
                position=0.99,
                showgrid=False,
                showticklabels=False,
                showline=False,
                ticks="outside",
                ticklabelposition="outside right",
                automargin=True
            ),
            yaxis5=dict(
                title_text="",
                overlaying="y",
                side="right",
                anchor="x",
                position=0.985,
                showgrid=False,
                showticklabels=True,
                showline=False,
                ticks="outside",
                ticklabelposition="outside right",
                automargin=True
            ),
            yaxis6=dict(
                title="",
                side="left",
                anchor="x2",
                overlaying="y",
                position=0,
                showgrid=False,
                showticklabels=False,
                showline=False,
                ticks="outside",
                automargin=True
            ),
            hovermode="x unified",
            legend_title="Metric",
            legend=dict(
                orientation="h",
                yanchor="top",
                y=1.08,
                xanchor="center",
                x=0.5
            ),
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

        log("Calculating ratio statistics...")
        import numpy as np
        import pandas as pd

        ratio_stats = []
        ratio_labels = ["Close Price", "PB", "PE", "Dividend Yield", "ROE"]
        ratio_sources = {
            "Close Price": [p["EOD_CLOSE_INDEX_VAL"] for p in price_data],
            "PB": [yield_by_date.get(ts, {}).get("IY_PB", None) for ts in x],
            "PE": [yield_by_date.get(ts, {}).get("IY_PE", None) for ts in x],
            "Dividend Yield": [yield_by_date.get(ts, {}).get("IY_DY", None) for ts in x],
            "ROE": [
                (float(yield_by_date.get(ts, {}).get("IY_PB", 0))/float(yield_by_date.get(ts, {}).get("IY_PE", 1))*100)
                if yield_by_date.get(ts, {}).get("IY_PB", None) and yield_by_date.get(ts, {}).get("IY_PE", None) and float(yield_by_date.get(ts, {}).get("IY_PE", 0)) != 0
                else None
                for ts in x
            ]
        }

        # Defensive: Only compute stats if at least one value is not None for each metric
        for label in ratio_labels:
            values = np.array([v if v is not None else np.nan for v in ratio_sources[label]])
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
        log("Plot and stats complete.")

def generate_metric_report(from_date, to_date, equity_master, nse, yield_data_cache, selected_report_groups):
    log("Starting indices-wide report generation...")
    import numpy as np
    import pandas as pd
    from datetime import timedelta
    from datetime import datetime  # Ensure datetime is explicitly imported in this scope

    metrics = [
        ("PB", "IY_PB"),
        ("PE", "IY_PE"),
        ("Dividend Yield", "IY_DY"),
        ("ROE", None)
    ]

    # Helper for missing date ranges
    def get_missing_yield_ranges(index_name, from_date, to_date):
        all_dates = [(from_date + timedelta(days=i)).strftime("%d-%m-%Y") for i in range((to_date - from_date).days + 1)]
        cached_yield = get_cached_yield(index_name, from_date, to_date)
        cached_yield_dates = set(y["date"] for y in cached_yield)
        return find_missing_date_ranges(all_dates, cached_yield_dates), cached_yield

    all_reports = {}
    for metric_name, metric_key in metrics:
        log(f"Processing report for metric: {metric_name}")
        # Filter indices by selected groups if any
        all_indices = []
        if selected_report_groups:
            for group in selected_report_groups:
                all_indices.extend(equity_master[group])
        else:
            for group in equity_master.values():
                all_indices.extend(group)

        report_rows = []
        total_indices = len(all_indices)
        valid_indices = 0
        advancing = declining = adv_lq = dec_lq = adv_ly = dec_ly = 0
        above_1sd = below_1sd = above_2sd = below_2sd = 0

        log(f"[{metric_name}] Report: {total_indices} indices")
        for idx_num, idx in enumerate(all_indices, 1):
            log(f"[{metric_name}] {idx_num}/{total_indices}: {idx}")
            try:
                # Check for missing yield data in DB, fetch only if needed
                missing_yield_ranges, cached_yield = get_missing_yield_ranges(idx, from_date, to_date)
                if missing_yield_ranges:
                    log(f"[{metric_name}] Missing yield ranges for {idx}: {missing_yield_ranges}")
                    max_retries = 5
                    for fetch_from, fetch_to in missing_yield_ranges:
                        yield_data = []
                        for chunk_start, chunk_end in split_date_range(fetch_from, fetch_to, 100):
                            for attempt in range(max_retries):
                                try:
                                    resp = nse._NSE__req(
                                        f"https://www.nseindia.com/api/historicalOR/indicesYield",
                                        params={
                                            "indexType": idx,
                                            "from": chunk_start.strftime("%d-%m-%Y"),
                                            "to": chunk_end.strftime("%d-%m-%Y")
                                        }
                                    )
                                    yield_data += resp.json().get("data", [])
                                    log(f"[{metric_name}] Fetched yield data chunk {chunk_start} to {chunk_end}.")
                                    break
                                except Exception as e:
                                    log(f"[{metric_name}] Error fetching yield data (attempt {attempt+1}): {e}")
                                    if attempt == max_retries - 1:
                                        log(f"[{metric_name}] Failed to fetch yield data for {idx}: {e}")
                                    else:
                                        continue
                        insert_yield(idx, yield_data)
                    # Refresh cache after insert
                    cached_yield = get_cached_yield(idx, from_date, to_date)
                yield_data = cached_yield
                yield_data_cache[idx] = yield_data

                # Format IY_DT keys to '%d-%m-%Y'
                def normalize_iydt(dt_str):
                    """Normalize NSE date strings to '%d-%m-%Y' format."""
                    try:
                        return datetime.strptime(dt_str, "%Y-%m-%d").strftime("%d-%m-%Y")
                    except ValueError:
                        raise ValueError(f"Unknown date format: {dt_str}")

                yield_by_date = {normalize_iydt(y["IY_DT"]): y for y in yield_data}
                x = list(yield_by_date.keys())

                # Compute metric series
                if metric_name == "ROE":
                    metric_series = [
                        (float(yield_by_date.get(ts, {}).get("IY_PB", 0))/float(yield_by_date.get(ts, {}).get("IY_PE", 1))*100)
                        if yield_by_date.get(ts, {}).get("IY_PB", None) and yield_by_date.get(ts, {}).get("IY_PE", None) and float(yield_by_date.get(ts, {}).get("IY_PE", 0)) != 0
                        else np.nan
                        for ts in x
                    ]
                else:
                    metric_series = [
                        float(yield_by_date.get(ts, {}).get(metric_key, np.nan))
                        if yield_by_date.get(ts, {}).get(metric_key, None) not in [None, ""] else np.nan
                        for ts in x
                    ]
                metric_series = np.array([v if v is not None else np.nan for v in metric_series])
                if np.all(np.isnan(metric_series)) or len(metric_series) < 2:
                    continue
                valid_indices += 1
                metric_from = metric_series[0]
                metric_to = metric_series[-1]
                metric_median = np.nanmedian(metric_series)
                metric_std = np.nanstd(metric_series)
                first_date = x[0] if x else None

                # Find last quarter and last year values
                def find_nearest_date(target, date_list):
                    from datetime import datetime, timedelta
                    # Try to find the exact date, else go back up to 10 days
                    def parse_date(dt_str):
                        orig_dt_str = dt_str
                        parts = dt_str.split('-')
                        if len(parts) == 3 and len(parts[1]) == 3 and parts[1].isupper():
                            parts[1] = parts[1].title()
                            dt_str = '-'.join(parts)
                        for fmt in ("%d-%m-%Y", "%d-%b-%Y", "%d-%B-%Y"):
                            try:
                                return datetime.strptime(dt_str, fmt)
                            except Exception:
                                continue
                        return None

                    # Build a lookup for fast access
                    date_lookup = {parse_date(dt): i for i, dt in enumerate(date_list) if parse_date(dt)}
                    target_dt = parse_date(target)
                    if not target_dt:
                        return None, None
                    # Try up to 10 days back
                    for tries in range(0, 11):
                        check_dt = target_dt - timedelta(days=tries)
                        idx = date_lookup.get(check_dt)
                        if idx is not None:
                            return idx, date_list[idx]
                    return None, None

                # Last quarter: ~90 days ago
                # Last year: ~365 days ago
                if x:
                    last_date = x[-1]
                    from datetime import datetime, timedelta
                    last_dt = datetime.strptime(last_date, "%d-%m-%Y")
                    lq_target = (last_dt - timedelta(days=90)).strftime("%d-%m-%Y")
                    ly_target = (last_dt - timedelta(days=365)).strftime("%d-%m-%Y")
                    lq_idx, lq_date = find_nearest_date(lq_target, x)
                    ly_idx, ly_date = find_nearest_date(ly_target, x)
                    metric_lq = metric_series[lq_idx] if lq_idx is not None else np.nan
                    metric_ly = metric_series[ly_idx] if ly_idx is not None else np.nan
                else:
                    metric_lq = metric_ly = np.nan

                advancing += (metric_to > metric_from if not np.isnan(metric_to) and not np.isnan(metric_from) else 0)
                declining += (metric_to < metric_from if not np.isnan(metric_to) and not np.isnan(metric_from) else 0)
                adv_lq += (metric_lq < metric_to if not np.isnan(metric_lq) and not np.isnan(metric_to) else 0)
                dec_lq += (metric_lq > metric_to if not np.isnan(metric_lq) and not np.isnan(metric_to) else 0)
                adv_ly += (metric_ly < metric_to if not np.isnan(metric_ly) and not np.isnan(metric_to) else 0)
                dec_ly += (metric_ly > metric_to if not np.isnan(metric_ly) and not np.isnan(metric_to) else 0)
                above_1sd += (metric_to > metric_median + metric_std if not np.isnan(metric_to) and not np.isnan(metric_median) and not np.isnan(metric_std) else 0)
                below_1sd += (metric_to < metric_median - metric_std if not np.isnan(metric_to) and not np.isnan(metric_median) and not np.isnan(metric_std) else 0)
                above_2sd += (metric_to > metric_median + 2*metric_std if not np.isnan(metric_to) and not np.isnan(metric_median) and not np.isnan(metric_std) else 0)
                below_2sd += (metric_to < metric_median - 2*metric_std if not np.isnan(metric_to) and not np.isnan(metric_median) and not np.isnan(metric_std) else 0)

                report_rows.append({
                    "Index": idx,
                    "from_date": first_date,
                    f"{metric_name}_from": round(float(metric_from), 4) if not np.isnan(metric_from) else None,
                    f"{metric_name}_to": round(float(metric_to), 4) if not np.isnan(metric_to) else None,
                    f"{metric_name}_median": round(float(metric_median), 4) if not np.isnan(metric_median) else None,
                    f"{metric_name}_std": round(float(metric_std), 4) if not np.isnan(metric_std) else None,
                    # Remove Advancing/Declining columns, keep LQ/LY
                    f"Advancing_LQ_{metric_name}": metric_lq < metric_to if not np.isnan(metric_lq) and not np.isnan(metric_to) else None,
                    f"Declining_LQ_{metric_name}": metric_lq > metric_to if not np.isnan(metric_lq) and not np.isnan(metric_to) else None,
                    f"Advancing_LY_{metric_name}": metric_ly < metric_to if not np.isnan(metric_ly) and not np.isnan(metric_to) else None,
                    f"Declining_LY_{metric_name}": metric_ly > metric_to if not np.isnan(metric_ly) and not np.isnan(metric_to) else None,
                    f"{metric_name}_1SD_above_median": metric_to > metric_median + metric_std if not np.isnan(metric_to) and not np.isnan(metric_median) and not np.isnan(metric_std) else None,
                    f"{metric_name}_2SD_above_median": metric_to > metric_median + 2*metric_std if not np.isnan(metric_to) and not np.isnan(metric_median) and not np.isnan(metric_std) else None,
                    f"{metric_name}_1SD_below_median": metric_to < metric_median - metric_std if not np.isnan(metric_to) and not np.isnan(metric_median) and not np.isnan(metric_std) else None,
                    f"{metric_name}_2SD_below_median": metric_to < metric_median - 2*metric_std if not np.isnan(metric_to) and not np.isnan(metric_median) and not np.isnan(metric_std) else None,
                })
            except Exception as e:
                log(f"[{metric_name}] Skipped {idx} due to error: {e}")
                continue
        log(f"[{metric_name}] Report complete.")

        df_report = pd.DataFrame(report_rows)
        summary = f"""
| Metric | Value |
|--------|-------|
| Total Indices Checked | {total_indices} |
| Indices With Valid Data | {valid_indices} |
| Advancing Last Quarter | {adv_lq} |
| Declining Last Quarter | {dec_lq} |
| Advancing Last Year | {adv_ly} |
| Declining Last Year | {dec_ly} |
| Above 1SD | {above_1sd} |
| Below 1SD | {below_1sd} |
| Above 2SD | {above_2sd} |
| Below 2SD | {below_2sd} |
"""
        all_reports[metric_name] = {
            "df": df_report,
            "summary": summary
        }
    log("All reports generated.")
    return all_reports

if generate_report:
    log("Generate Reports button clicked. Starting report generation...")
    st.markdown("## Indices-wide Reports")
    yield_data_cache = {}
    reports = generate_metric_report(from_date, to_date, equity_master, nse, yield_data_cache, selected_report_groups)

    log("Preparing summary tables...")
    # Collate all summary tables into one DataFrame with metrics as columns
    import pandas as pd
    summary_dict = {}
    for metric_name in ["ROE", "PE", "PB", "Dividend Yield"]:
        summary_lines = reports[metric_name]["summary"].strip().split("\n")[2:]  # skip header
        for line in summary_lines:
            if "|" not in line or "Metric" in line or "--------" in line or not line.strip():
                continue
            col, val = [x.strip() for x in line.split("|")[1:3]]
            if col not in summary_dict:
                summary_dict[col] = {}
            summary_dict[col][metric_name] = val
    df_summary = pd.DataFrame.from_dict(summary_dict, orient="index")
    df_summary.index.name = "Summary"
    df_summary.reset_index(inplace=True)

    with st.expander("All Reports Summary", expanded=True):
        st.dataframe(df_summary)

    for metric_name in ["ROE", "PE", "PB", "Dividend Yield"]:
        with st.expander(f"{metric_name} Report", expanded=True):
            # Remove summary markdown from each report
            st.dataframe(reports[metric_name]["df"])