# Project Overview: NSE Index Data Viz

A Streamlit-based dashboard for tracking and visualizing NSE (National Stock Exchange of India) indices cycles using historical valuation ratios like P/E, P/B, Dividend Yield, and ROE.

## Core Purpose
The application provides investors with tools to identify market cycles by comparing current index valuations against their historical distributions.

## Key Features
- **Deep Dive Analysis**: Detailed historical view of a specific index with multiple metrics (Price, P/E, P/B, etc.).
- **Market Screener**: Comparative analysis of multiple indices within a market segment (e.g., Sectoral, Broad Market).
- **Cycle Indicators**: Z-score and percentile-based analysis of valuation ratios.
- **Interactive Visualizations**: Time-series charts and distribution plots using Plotly.

## Tech Stack
- **Frontend/App Framework**: Streamlit
- **Data Visualization**: Plotly
- **Data Processing**: Pandas, NumPy
- **HTTP Client**: Requests (for data fetching)
