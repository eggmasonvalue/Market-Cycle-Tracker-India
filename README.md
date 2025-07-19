# NSE Index Ratio History
This Streamlit app visualizes historical price, ratios(PE, PB, Dividend Yield and ROE) and turnover for NSE indices.
It also helps in identifying where each ratio stands within their statistical measures historically.

## Value proposition
- Tracking the stage of sectors/market in their cycle. Using indices is the best approach for this since they're all market cap weighted and hence represent the state of the sector better
- ROE plot
- Plot all metrics in a single graph including turnover

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
- price and ratio data is currently fetched daily leading to a 10y window. Will be updated to a slower periodicity to allow charting for longer periods
