import unittest
from unittest.mock import MagicMock
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import sys
import os

# Add the project root to the python path so we can import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data.client import NiftyIndicesClient

class TestNiftyIndicesClientRetries(unittest.TestCase):
    def test_retry_configuration(self):
        client = NiftyIndicesClient()

        # Check if adapters are mounted for https:// and http://
        adapter_https = client.session.adapters.get("https://")
        self.assertIsNotNone(adapter_https)
        self.assertIsInstance(adapter_https, HTTPAdapter)

        adapter_http = client.session.adapters.get("http://")
        self.assertIsNotNone(adapter_http)
        self.assertIsInstance(adapter_http, HTTPAdapter)

        # Verify the retry configuration
        retry_config = adapter_https.max_retries
        self.assertIsInstance(retry_config, Retry)
        self.assertEqual(retry_config.total, 3)
        self.assertEqual(retry_config.backoff_factor, 1)
        self.assertEqual(set(retry_config.status_forcelist), {429, 500, 502, 503, 504})
        self.assertEqual(set(retry_config.allowed_methods), {"GET", "POST"})

        # Verify both adapters share the same configuration (or are similar)
        retry_config_http = adapter_http.max_retries
        self.assertEqual(retry_config_http.total, 3)

if __name__ == '__main__':
    unittest.main()
