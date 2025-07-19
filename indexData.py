import streamlit as st
import plotly.graph_objs as go
from nse import NSE
from datetime import date, timedelta

st.set_page_config(page_title="NSE Index Chart", layout="wide")

nse = NSE("d:/Misc2/Index data")

# Fetch index groups and indices from new API
equity_master = nse._NSE__req("https://www.nseindia.com/api/equity-master").json()
keys = [k for k in equity_master.keys() if k.upper() != "OTHERS"]

st.title("NSE Index Interactive Chart")

# Sidebar UI
with st.sidebar:
    st.header("Configure Chart")
    min_dt = date(1990, 1, 1)
    from_date = st.date_input("From Date", value=date.today() - timedelta(days=30), min_value=min_dt)
    to_date = st.date_input("To Date", value=date.today(), min_value=min_dt)
    selected_key = st.selectbox("Index Group", keys)
    indices_for_key = equity_master[selected_key]
    selected_index = st.selectbox("Index", indices_for_key)
    st.markdown("**Select Metrics to Plot**")
    metrics = {
        "PB": "pb",
        "PE": "pe",
        "Dividend Yield": "dy",
        "Close Price": "last",
        "ROE": "roe"
    }
    selected_metrics = []
    for label in metrics.keys():
        if st.checkbox(label):
            selected_metrics.append(label)
    plot_clicked = st.button("Plot", use_container_width=True)

if plot_clicked:
    # Fetch historical price data for selected index
    hist = nse.fetch_historical_index_data(
        index=selected_index,
        from_date=from_date,
        to_date=to_date
    )
    price_data = hist.get("price", [])
    turnover_data = hist.get("turnover", [])

    # Split date range into chunks of max 100 days
    def split_date_range(from_date, to_date, max_days=100):
        chunks = []
        current_start = from_date
        while current_start <= to_date:
            current_end = min(current_start + timedelta(days=max_days - 1), to_date)
            chunks.append((current_start, current_end))
            current_start = current_end + timedelta(days=1)
        return chunks

    yield_data = []
    for chunk_start, chunk_end in split_date_range(from_date, to_date, 100):
        resp = nse._NSE__req(
            f"https://www.nseindia.com/api/historicalOR/indicesYield",
            params={
                "indexType": selected_index,
                "from": chunk_start.strftime("%d-%m-%Y"),
                "to": chunk_end.strftime("%d-%m-%Y")
            }
        )
        yield_data += resp.json().get("data", [])

    # Map yield data by date for quick lookup (IY_DT)
    yield_by_date = {y["IY_DT"]: y for y in yield_data}

    x = [p["EOD_TIMESTAMP"] for p in price_data]
    traces = []

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
    """ Note: Turnover data date may not match exactly with price data dates because of how NSE reports it,
    so we use the HIT_TIMESTAMP from turnover data directly. """
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

    fig = go.Figure(traces)
    fig.update_layout(
        title=f"{selected_index} ({selected_key})",
        xaxis=dict(
            title="Date",
            domain=[0, 1],
            anchor="y1"
        ),
        xaxis2=dict(
            title="Date",
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
            showticklabels=False,
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