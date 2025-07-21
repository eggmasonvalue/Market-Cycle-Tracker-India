# NSE Indices Cycle Tracker Dashboard

This Streamlit app visualizes and analyzes historical ratios for NSE indices, with advanced screening and interactive analysis features.

## Value Proposition
- ROE history
- Uses indices' ratios to track cycles. This is the more appropriate way since most indices are market-cap weighted leading to more accurate representations of the state of the sector in its cycle
- Track the cycles each sector/theme/any index is in with statistical measures like median/SD
- Actionable ideas - screen for sectors/themes recovering from a downturn/disproportionately undervalued relative to history

## Features

- Interactive sidebar for selecting index group, index, date range
- Metric selection: "Price" (Close Price) and "Ratios" (PB, PE, Dividend Yield, ROE)
- Multi-metric plotting with separate y-axes
- Indices-wide advanced reports with multi-ratio filtering and SD/trend filters
- Feature-rich charts and tables

## Setup

1. Install Python 3.8+.
2. Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

3. Run the app:

    ```bash
    streamlit run app.py
    ```

## Notes
- Click on any metric in the legend to hide/show that line on the chart.
- NSE uses TTM for PE ratio so ROE changes as and when companies report
- Session state and reset button ensure persistent and intuitive report workflow.
- Trendlyne and other tools cover overlaying different indices' charts on top of one another
