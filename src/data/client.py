import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Union, Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import streamlit as st

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NiftyIndicesClient:
    """
    Client for interacting with Nifty Indices API.
    Handles data fetching, payload construction, and error management.
    """

    BASE_URL = "https://www.niftyindices.com"
    HEADERS = {
        "Content-Type": "application/json; charset=UTF-8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Referer": "https://www.niftyindices.com/reports/historical-data",
        "Origin": "https://www.niftyindices.com",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest"
    }

    def __init__(self):
        self.session = requests.Session()

        # Configure retries with exponential backoff
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        self.session.headers.update(self.HEADERS)

    def _post(self, endpoint: str, payload: Dict[str, Any]) -> Any:
        """
        Internal method to make POST requests.
        """
        url = f"{self.BASE_URL}{endpoint}"
        try:
            response = self.session.post(url, json=payload, timeout=30)
            response.raise_for_status()
            try:
                data = response.json()
                # The API typically returns data wrapped in 'd'
                return data.get("d", data)
            except ValueError:
                logger.warning(f"Response from {endpoint} is not JSON. Returning raw text.")
                return response.text
        except requests.RequestException as e:
            logger.error(f"Error fetching data from {endpoint}: {e}")
            return {"error": str(e)}

    def fetch_index_mapping(self) -> Dict[str, str]:
        """Fetch the mapping from long name to trading index name."""
        url = "https://iislliveblob.niftyindices.com/assets/json/IndexMapping.json"
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            mapping_list = resp.json()
            mapping = {
                item["Index_long_name"].strip(): item["Trading_Index_Name"].strip()
                for item in mapping_list
                if "Index_long_name" in item and "Trading_Index_Name" in item
            }
            return mapping
        except Exception as e:
            logger.error(f"Error fetching index mapping: {e}")
            return {}

    def fetch_subindex_types(self, index_group: str) -> List[Dict[str, Any]]:
        """Fetch all sub-index types for a given index group."""
        endpoint = "/Backpage.aspx/gethistoricaltypeSubindexdata"
        payload = {"cinfo": {"indextype": "Equity", "indexgroup": index_group}}
        result = self._post(endpoint, payload)

        if isinstance(result, str): # Handle potential stringified JSON response
            try:
                result = json.loads(result)
            except json.JSONDecodeError:
                pass

        if isinstance(result, list):
            return result
        elif isinstance(result, dict) and "error" in result:
             # Propagate error but as an empty list or handle gracefully in UI
             logger.error(f"Failed to fetch subindex types: {result['error']}")
             return []
        return []

    def fetch_indices(self, subindex_type: str, index_group: str) -> List[Dict[str, Any]]:
        """Fetch all indices for a given sub-index type and index group."""
        endpoint = "/Backpage.aspx/gethistoricaltypeindexdata"
        payload = {"cinfo": {"indextype": subindex_type, "indexgroup": index_group}}
        result = self._post(endpoint, payload)

        if isinstance(result, str):
            try:
                result = json.loads(result)
            except json.JSONDecodeError:
                pass

        if isinstance(result, list):
            return result
        elif isinstance(result, dict) and "error" in result:
             logger.error(f"Failed to fetch indices: {result['error']}")
             return []
        return []

    def fetch_index_data(self, index_name: str, start_date: str, end_date: str, index_group: str = "Total returns Index Values") -> List[Dict[str, Any]]:
        """
        Fetch historical data for a given index name and index group.
        Handles name mapping internally.
        """
        # Determine endpoint based on index group
        if index_group == "Historical Index Data":
            endpoint = "/Backpage.aspx/getHistoricaldatatabletoString"
        elif index_group == "P/E, P/B & Div.Yield values":
            endpoint = "/Backpage.aspx/getpepbHistoricaldataDBtoString"
        else:
            endpoint = "/Backpage.aspx/getTotalReturnIndexString"

        # Map long name to trading name if needed
        # We fetch mapping only if we suspect mismatch, or always?
        # For simplicity and robustness, let's try to map it.
        # But caching the mapping is important.
        # Since this method is cached by Streamlit (in the wrapper), we can fetch mapping here.
        # However, making a network call inside a cached function for mapping is okay if mapping is static-ish.

        mapping = self.fetch_index_mapping()
        trading_name = index_name

        # Try exact match
        if index_name.strip() in mapping:
            trading_name = mapping[index_name.strip()]
        else:
            # Case-insensitive match
            mapping_lower = {k.lower(): v for k, v in mapping.items()}
            if index_name.strip().lower() in mapping_lower:
                trading_name = mapping_lower[index_name.strip().lower()]

        cinfo_dict = {
            "name": trading_name,
            "startDate": start_date,
            "endDate": end_date,
            "indexName": trading_name
        }

        # Using json.dumps for inner JSON string as verified
        cinfo_str = json.dumps(cinfo_dict)
        payload = {"cinfo": cinfo_str}

        result = self._post(endpoint, payload)

        # The result for index data is often a stringified JSON inside the 'd' property (which _post handles)
        # So 'result' might be a string that needs parsing again.
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except json.JSONDecodeError:
                 logger.error("Failed to parse index data JSON string.")
                 return []

        if isinstance(result, list):
            return result
        elif isinstance(result, dict) and "error" in result:
             logger.error(f"Failed to fetch index data: {result['error']}")
             return []

        return []

# --- Streamlit Caching Wrapper ---

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_subindex_types(index_group: str) -> List[str]:
    client = NiftyIndicesClient()
    data = client.fetch_subindex_types(index_group)
    return [item["indextype"] for item in data if "indextype" in item]

@st.cache_data(ttl=3600)
def get_indices(subindex_type: str, index_group: str) -> List[str]:
    client = NiftyIndicesClient()
    data = client.fetch_indices(subindex_type, index_group)
    return [item["indextype"] for item in data if "indextype" in item]

@st.cache_data(ttl=3600)
def get_index_data(index_name: str, start_date: str, end_date: str, index_group: str) -> List[Dict[str, Any]]:
    client = NiftyIndicesClient()
    return client.fetch_index_data(index_name, start_date, end_date, index_group)
