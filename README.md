# NSE Index Interactive Chart

This Streamlit app visualizes historical metrics and turnover for NSE indices.  
It supports interactive selection of index group, index, date range, and metrics (PB, PE, Dividend Yield, Close Price, ROE).  
Turnover is displayed as a volume bar at the bottom of the chart.

## Features

- Interactive sidebar for selecting index group, index, date range, and metrics
- Plots up to five metrics on separate y-axes
- Plots turnover as a bar chart at the bottom
- Fetches data directly from NSE APIs

## Setup

1. Install Python 3.8+.
2. Install dependencies:

    ```
    pip install -r requirements.txt
    ```

3. Run the app:

    ```
    streamlit run indexData.py
    ```

## Files

- `indexData.py`: Main Streamlit app

## Notes

- Turnover bar date may not align with the index date perfectly due to NSE's reporting.
- Click on any of the metrics in the legend to not see that line on the chart
