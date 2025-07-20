import requests
from datetime import datetime

# --- Index Mapping Logic ---


def fetch_index_mapping():
    """Fetch the mapping from long name to trading index name (no cache)."""
    url = "https://iislliveblob.niftyindices.com/assets/json/IndexMapping.json"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        mapping_list = resp.json()
        # Build dict: long_name -> trading_name
        mapping = {item["Index_long_name"].strip(): item["Trading_Index_Name"].strip() for item in mapping_list if "Index_long_name" in item and "Trading_Index_Name" in item}
        return mapping
    except Exception as e:
        return {"error": str(e)}

def fetch_subindex_types(indexgroup):
    """Fetch all sub-index types for a given index group."""
    url = "https://www.niftyindices.com/Backpage.aspx/gethistoricaltypeSubindexdata"
    payload = {"cinfo": {"indextype": "Equity", "indexgroup": indexgroup}}
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Referer": "https://www.niftyindices.com/reports/historical-data"
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        r.raise_for_status()
        resp_json = r.json()
        return resp_json.get("d", resp_json)
    except Exception as e:
        return {"error": str(e)}

def fetch_indices(subindex_type, indexgroup):
    """Fetch all indices for a given sub-index type and index group."""
    url = "https://www.niftyindices.com/Backpage.aspx/gethistoricaltypeindexdata"
    payload = {"cinfo": {"indextype": subindex_type, "indexgroup": indexgroup}}
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Referer": "https://www.niftyindices.com/reports/historical-data"
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        r.raise_for_status()
        resp_json = r.json()
        return resp_json.get("d", resp_json)
    except Exception as e:
        return {"error": str(e)}

def fetch_index_data(index_name, start_date=None, end_date=None, indexgroup="Total returns Index Values"):
    """Fetch historical data for a given index name and index group."""
    # Select data_url based on indexgroup
    if indexgroup == "Historical Index Data":
        data_url = "https://www.niftyindices.com/Backpage.aspx/getHistoricaldatatabletoString"
    elif indexgroup == "P/E, P/B & Div.Yield values":
        data_url = "https://www.niftyindices.com/Backpage.aspx/getpepbHistoricaldataDBtoString"
    else:
        data_url = "https://www.niftyindices.com/Backpage.aspx/getTotalReturnIndexString"

    if not start_date:
        start_date = "01-Jan-1995"
    if not end_date:
        end_date = datetime.now().strftime("%d-%b-%Y")

    # Map long name to trading name if possible
    mapping = fetch_index_mapping()
    trading_name = index_name
    if isinstance(mapping, dict) and not "error" in mapping:
        # Try exact, then case-insensitive, then fallback
        key = index_name.strip()
        if key in mapping:
            trading_name = mapping[key]
        else:
            # Try case-insensitive match
            lowered = {k.lower(): v for k, v in mapping.items()}
            trading_name = lowered.get(key.lower(), index_name)
    cinfo_dict = {
        "name": trading_name,
        "startDate": start_date,
        "endDate": end_date,
        "indexName": trading_name
    }
    cinfo_str = str(cinfo_dict).replace('"', "'")
    payload = {
        "cinfo": cinfo_str
    }
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "Referer": "https://www.niftyindices.com/reports/historical-data",
        "Origin": "https://www.niftyindices.com",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }
    try:
        r = requests.post(data_url, json=payload, headers=headers, timeout=30)
        try:
            resp_json = r.json()
            data = resp_json.get('d', resp_json)
        except Exception:
            data = r.text
        # Return structured data
        return data
    except Exception as e:
        return {"error": str(e)}

# Example usage for another file:
# from niftyindicesscraper import fetch_subindex_types, fetch_indices, fetch_index_data
# subindex_types = fetch_subindex_types("Total returns Index Values")
# indices = fetch_indices(subindex_types[0]["indextype"], "Total returns Index Values")
# data = fetch_index_data(indices[0]["indextype"])
