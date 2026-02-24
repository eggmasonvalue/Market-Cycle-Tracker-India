# NSE Indices Cycle Tracker Dashboard

This Streamlit app visualizes and analyzes historical ratios for NSE indices to identify market cycles and investment opportunities.

## Features

- **Deep Dive**: Detailed analysis of a single index with interactive charts (Price, PE, PB, Dividend Yield, ROE).
- **Cycle Analysis**: Historical distribution plots and current valuation zones.
- **Screener**: Market-wide screener to compare valuation (PE) vs profitability (ROE) across sectors/themes.
- **Data Source**: Fetches data directly from `niftyindices.com` (with caching).

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

## Project Structure

- `src/data`: Data fetching logic (API client).
- `src/processing`: Data transformation and analysis.
- `src/ui`: UI components and views.
- `src/utils`: Constants and helpers.
- `app.py`: Main application entry point.

## Deployment

Deploy directly to Streamlit Cloud. Ensure `requirements.txt` is present in the root.
