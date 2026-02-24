import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from typing import Dict, List, Optional
from datetime import datetime

from src.utils.constants import (
    COLOR_PRIMARY, COLOR_SECONDARY, COLOR_DANGER, COLOR_WARNING,
    COLOR_SUCCESS, COLOR_NEUTRAL, COLOR_PURPLE, METRIC_LABELS
)

def render_metric_cards(df: pd.DataFrame, metrics: List[str]):
    """Render summary metrics for the selected index."""
    if df.empty:
        return

    cols = st.columns(len(metrics))
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest

    for i, metric in enumerate(metrics):
        val = latest.get(metric, np.nan)
        prev_val = prev.get(metric, np.nan)

        label = METRIC_LABELS.get(metric, metric.upper())

        if pd.isna(val):
            cols[i].metric(label, "N/A")
        else:
            delta = val - prev_val if not pd.isna(prev_val) else 0
            fmt = "{:.2f}"
            if metric == "close":
                fmt = "{:,.2f}"
            elif metric in ["roe", "div_yield"]:
                fmt = "{:.2f}%"

            # Color logic for delta could be inverted for valuation ratios (PE/PB)
            # High PE delta usually bad for valuation (Red), but good for momentum (Green)
            # Keeping default Green = Up, Red = Down for now.
            cols[i].metric(label, fmt.format(val), f"{delta:+.2f}")

def render_main_chart(df: pd.DataFrame, selected_metrics: List[str]):
    """
    Render the main interactive chart with Price and selected Ratios.
    """
    if df.empty:
        st.warning("No data available to plot.")
        return

    fig = go.Figure()

    # Add Price (Always on primary Y-axis)
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['close'],
        mode='lines',
        name='Close Price',
        line=dict(color=COLOR_PRIMARY, width=2),
        yaxis='y1'
    ))

    # Add Ratios (On secondary Y-axis)
    # If multiple ratios are selected, they might clutter the secondary axis.
    # Plotly supports multiple Y-axes, but it gets messy.
    # Alternatively, we can normalize them or just plot one ratio at a time on the secondary axis
    # and toggle visibility.
    # For now, let's put them all on y2, but maybe separate traces.

    colors = {
        "pe": COLOR_SECONDARY,
        "pb": COLOR_PURPLE,
        "div_yield": COLOR_WARNING,
        "roe": COLOR_DANGER
    }

    # We will overlay y-axes for each metric to avoid scale issues
    # y2, y3, y4, y5...

    layout_update = {}

    # Base layout for y1 (Price)
    layout_update['yaxis'] = dict(
        title="Close Price",
        side="left",
        showgrid=True,
        color=COLOR_PRIMARY
    )

    # Iterate through metrics and add traces/axes
    # Start overlay axes from y2
    axis_idx = 2

    for metric in selected_metrics:
        if metric == "close":
            continue

        y_axis_name = f"yaxis{axis_idx}"
        color = colors.get(metric, "#333")
        label = METRIC_LABELS.get(metric, metric)

        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df[metric],
            mode='lines',
            name=label,
            line=dict(color=color, width=1.5),
            yaxis=f"y{axis_idx}"
        ))

        # Configure the axis
        # Shift axes to the right to avoid overlap
        offset = (axis_idx - 2) * 0.05

        layout_update[y_axis_name] = dict(
            title=label,
            overlaying="y",
            side="right",
            position=1.0 - offset if axis_idx > 2 else 1.0,
            showgrid=False,
            title_font=dict(color=color),
            tickfont=dict(color=color),
            anchor="free" if axis_idx > 2 else "x"
        )

        axis_idx += 1

    fig.update_layout(
        title="Price & Valuation History",
        xaxis=dict(title="Date", domain=[0, 1.0 - (axis_idx-3)*0.05 if axis_idx > 3 else 1.0]),
        legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"),
        template="plotly_white",
        hovermode="x unified",
        height=600
    )

    fig.update_layout(**layout_update)
    st.plotly_chart(fig, use_container_width=True)

def render_ratio_analysis(df: pd.DataFrame, metric: str):
    """
    Render distribution analysis for a single metric.
    Histogram + Box Plot + Current Value marker.
    """
    if df.empty or metric not in df.columns:
        return

    series = df[metric].dropna()
    if series.empty:
        st.warning(f"No data for {metric}")
        return

    current_val = series.iloc[-1]
    median_val = series.median()

    col1, col2 = st.columns([2, 1])

    with col1:
        # Histogram with KDE
        fig = px.histogram(
            df,
            x=metric,
            nbins=30,
            title=f"Historical Distribution: {METRIC_LABELS.get(metric, metric)}",
            color_discrete_sequence=[COLOR_NEUTRAL],
            marginal="box" # Adds boxplot at the top
        )

        # Add vertical line for current value
        fig.add_vline(x=current_val, line_dash="dash", line_color=COLOR_DANGER, annotation_text="Current", annotation_position="top left")
        fig.add_vline(x=median_val, line_dash="dot", line_color=COLOR_PRIMARY, annotation_text="Median", annotation_position="bottom right")

        fig.update_layout(showlegend=False, template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Gauge Chart logic using simple metric or progress bar
        # Calculate Percentile
        percentile = (series < current_val).mean() * 100

        st.markdown(f"### Current {METRIC_LABELS.get(metric, metric)}")
        st.metric("Value", f"{current_val:.2f}", f"Percentile: {percentile:.0f}%")

        # Zone interpretation
        if metric in ["pe", "pb"]:
            if percentile < 20:
                zone = "Undervalued (Low Percentile)"
                color = "green"
            elif percentile > 80:
                zone = "Overvalued (High Percentile)"
                color = "red"
            else:
                zone = "Fair Value"
                color = "blue"
        elif metric in ["div_yield", "roe"]: # Higher is usually better/cheaper for DY
             if percentile > 80:
                zone = "High (Top Percentile)"
                color = "green" # Good
             elif percentile < 20:
                zone = "Low (Bottom Percentile)"
                color = "red" # Bad
             else:
                zone = "Average"
                color = "blue"

        st.markdown(f"**Zone:** :{color}[{zone}]")
        st.progress(int(percentile))

        st.markdown("#### Statistics")
        stats = series.describe()
        st.dataframe(stats.to_frame(), use_container_width=True)

def render_screener_plots(screener_df: pd.DataFrame):
    """
    Render visual scatter plots for screening.
    Displays Profitability (ROE) vs Valuation (PE/PB).
    """
    if screener_df.empty:
        st.warning("No data available for screening.")
        return

    st.markdown("### Valuation vs Profitability Scanner")

    # Plot 1: ROE (X) vs PE (Y)
    plot_df = screener_df.dropna(subset=["pe_latest", "roe_latest"])
    if not plot_df.empty:
        fig1 = px.scatter(
            plot_df,
            x="roe_latest",
            y="pe_latest",
            size="div_yield_latest",
            color="Subindex Type",
            hover_name="Index",
            title="P/E Ratio vs ROE (Size = Div Yield)",
            labels={
                "pe_latest": "P/E Ratio (Valuation)",
                "roe_latest": "ROE % (Profitability)",
                "div_yield_latest": "Div Yield %"
            },
            template="plotly_white",
            height=500
        )
        pe_median = plot_df["pe_latest"].median()
        roe_median = plot_df["roe_latest"].median()
        # Horizontal line for median PE (Y)
        fig1.add_hline(y=pe_median, line_dash="dot", line_color="grey", annotation_text="Median PE")
        # Vertical line for median ROE (X)
        fig1.add_vline(x=roe_median, line_dash="dot", line_color="grey", annotation_text="Median ROE")
        st.plotly_chart(fig1, use_container_width=True)

    st.markdown("---")

    # Plot 2: ROE (X) vs PB (Y)
    plot_df_pb = screener_df.dropna(subset=["pb_latest", "roe_latest"])
    if not plot_df_pb.empty:
        fig2 = px.scatter(
            plot_df_pb,
            x="roe_latest",
            y="pb_latest",
            size="div_yield_latest",
            color="Subindex Type",
            hover_name="Index",
            title="P/B Ratio vs ROE (Size = Div Yield)",
            labels={
                "pb_latest": "P/B Ratio (Valuation)",
                "roe_latest": "ROE % (Profitability)",
                "div_yield_latest": "Div Yield %"
            },
            template="plotly_white",
            height=500
        )
        pb_median = plot_df_pb["pb_latest"].median()
        roe_median_pb = plot_df_pb["roe_latest"].median()
        # Horizontal line for median PB (Y)
        fig2.add_hline(y=pb_median, line_dash="dot", line_color="grey", annotation_text="Median PB")
        # Vertical line for median ROE (X)
        fig2.add_vline(x=roe_median_pb, line_dash="dot", line_color="grey", annotation_text="Median ROE")
        st.plotly_chart(fig2, use_container_width=True)

def render_screener_table(screener_df: pd.DataFrame):
    """
    Render detailed data table for screening.
    """
    if screener_df.empty:
        st.warning("No data available.")
        return

    st.markdown("### Detailed Data")

    display_df = screener_df.copy()

    st.dataframe(
        display_df,
        column_config={
            "pe_latest": st.column_config.NumberColumn("P/E", format="%.2f"),
            "pb_latest": st.column_config.NumberColumn("P/B", format="%.2f"),
            "roe_latest": st.column_config.NumberColumn("ROE %", format="%.2f"),
            "div_yield_latest": st.column_config.NumberColumn("Div Yld %", format="%.2f"),
        },
        use_container_width=True,
        hide_index=True
    )
