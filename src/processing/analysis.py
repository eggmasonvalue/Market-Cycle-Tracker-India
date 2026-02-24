import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

def parse_date(date_str: str) -> Optional[datetime]:
    """Parse date string to datetime object."""
    if not isinstance(date_str, str):
        return None
    try:
        return datetime.strptime(date_str.strip(), "%d %b %Y")
    except ValueError:
        try:
            return datetime.strptime(date_str.strip(), "%d-%b-%Y")
        except ValueError:
            return None

def normalize_data(data: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Normalize list of dictionaries into a DataFrame with consistent columns.
    Handles 'Date'/'DATE', 'TotalReturnsIndex'/'EOD_CLOSE_INDEX_VAL', etc.
    """
    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)

    # Normalize Date column
    if "Date" in df.columns:
        df["date"] = df["Date"].apply(parse_date)
    elif "DATE" in df.columns:
        df["date"] = df["DATE"].apply(parse_date)
    else:
        # Fallback if no date column found
        return pd.DataFrame()

    # Normalize Value columns (Price)
    if "TotalReturnsIndex" in df.columns:
        df["close"] = pd.to_numeric(df["TotalReturnsIndex"], errors="coerce")
    elif "EOD_CLOSE_INDEX_VAL" in df.columns:
        df["close"] = pd.to_numeric(df["EOD_CLOSE_INDEX_VAL"], errors="coerce")

    # Normalize Ratio columns (pe, pb, divYield)
    # API usually returns: 'pe', 'pb', 'divYield' (sometimes capitalized?)
    # Based on existing code: "pe", "pb", "divYield"

    if "pe" in df.columns:
        df["pe"] = pd.to_numeric(df["pe"], errors="coerce")
    if "pb" in df.columns:
        df["pb"] = pd.to_numeric(df["pb"], errors="coerce")
    if "divYield" in df.columns:
        df["div_yield"] = pd.to_numeric(df["divYield"], errors="coerce")

    # Drop rows with invalid dates
    df = df.dropna(subset=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    return df

def calculate_roe(pb_series: pd.Series, pe_series: pd.Series) -> pd.Series:
    """
    Calculate ROE = (PB / PE) * 100.
    Handles division by zero and NaNs.
    """
    # Avoid division by zero
    pe_safe = pe_series.replace(0, np.nan)
    return (pb_series / pe_safe) * 100

def process_index_data(price_data: List[Dict[str, Any]], ratios_data: List[Dict[str, Any]] = None) -> pd.DataFrame:
    """
    Process raw price and ratios data into a single DataFrame.
    """
    df_price = normalize_data(price_data)
    df_ratios = normalize_data(ratios_data) if ratios_data else pd.DataFrame()

    if df_price.empty and df_ratios.empty:
        return pd.DataFrame()

    if not df_price.empty:
        df_final = df_price[["date", "close"]].copy() if "close" in df_price.columns else df_price[["date"]].copy()
    else:
        # If no price data, start with ratios dates
        df_final = df_ratios[["date"]].copy().drop_duplicates().sort_values("date")

    if not df_ratios.empty:
        # Merge on date
        # Ensure date formats are identical (datetime64[ns])
        if "close" in df_final.columns:
            df_final = pd.merge(df_final, df_ratios[["date", "pe", "pb", "div_yield"]], on="date", how="left")
        else:
            # If we started with ratios, just merge or use df_ratios directly,
            # but we need to ensure unique dates or handle duplicates if any
            # normalize_data already sorts by date.
            # But let's be safe and merge
            df_final = pd.merge(df_final, df_ratios[["date", "pe", "pb", "div_yield"]], on="date", how="left")

        # Calculate ROE
        if "pe" in df_final.columns and "pb" in df_final.columns:
            df_final["roe"] = calculate_roe(df_final["pb"], df_final["pe"])

    return df_final

def calculate_stats(series: pd.Series) -> Dict[str, float]:
    """
    Calculate basic statistics for a series.
    Returns: min, max, median, mean, std, latest, percentiles.
    """
    series = series.dropna()
    if series.empty:
        return {}

    stats = {
        "min": series.min(),
        "max": series.max(),
        "median": series.median(),
        "mean": series.mean(),
        "std": series.std(),
        "latest": series.iloc[-1],
        "count": len(series)
    }

    # Z-Score of latest value
    if stats["std"] and stats["std"] != 0:
        stats["z_score"] = (stats["latest"] - stats["median"]) / stats["std"]
    else:
        stats["z_score"] = 0.0

    return stats

def calculate_trend(series: pd.Series) -> Dict[str, str]:
    """
    Calculate trend direction for LQ (90 days) and LY (365 days).
    Returns: "Advancing", "Declining", or "Neutral".
    """
    # Ensure series is sorted by date (implied by index usually, but here series might just be values)
    # We assume the series passed is already chronologically sorted.

    if series.empty:
        return {"LQ": "Unknown", "LY": "Unknown"}

    latest_val = series.iloc[-1]

    # Approximate indices for 90 days and 365 days assuming daily data (approx 252 trading days/year)
    # But series might have gaps. Better to use time-based indexing if possible.
    # Here we will just use array indexing as an approximation for "Recent" vs "Old".
    # 3 months ~ 60 trading days
    # 1 year ~ 250 trading days

    lq_idx = max(0, len(series) - 60)
    ly_idx = max(0, len(series) - 250)

    lq_val = series.iloc[lq_idx]
    ly_val = series.iloc[ly_idx]

    def get_direction(current, past):
        if pd.isna(current) or pd.isna(past):
            return "Unknown"
        if current > past * 1.05: # 5% threshold
            return "Advancing"
        elif current < past * 0.95:
            return "Declining"
        else:
            return "Neutral"

    return {
        "LQ": get_direction(latest_val, lq_val),
        "LY": get_direction(latest_val, ly_val)
    }
