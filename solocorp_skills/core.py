"""Core client for interacting with Central Bus."""

import os
import time
import json
from pathlib import Path
from typing import Any, Optional
from datetime import datetime

BASE_URL = os.environ.get(
    "SOLOCORP_API_URL",
    "http://localhost:8099"
)

API_KEY = os.environ.get(
    "SOLOCORP_API_KEY",
    ""
)

BUS_DIR = Path(__file__).parent.parent / "bus"
PROFILES_DIR = Path(__file__).parent.parent / "profiles"


class SolocorpError(Exception):
    """Base error for Solocorp operations."""
    def __init__(self, message: str, code: int = 500):
        self.message = message
        self.code = code
        super().__init__(message)


class SolocorpClient:
    """Client for SoloCorp OS operations.

    Provides a unified interface for all Solocorp operations.
    Falls back to file-based operations when Central Bus is unavailable.
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or API_KEY
        self.base_url = base_url or BASE_URL
        self._ready = False
        self._init_check()

    def _init_check(self) -> bool:
        """Check if Central Bus is available."""
        try:
            import urllib.request
            req = urllib.request.Request(
                f"{self.base_url}/v1/health",
                headers={"X-API-Key": self.api_key} if self.api_key else {}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                self._ready = resp.status == 200
        except Exception:
            self._ready = False
        return self._ready

    def _api_get(self, path: str) -> dict:
        """GET request to Central Bus."""
        import urllib.request
        url = f"{self.base_url}{path}"
        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())

    def _api_post(self, path: str, data: dict) -> dict:
        """POST request to Central Bus."""
        import urllib.request
        url = f"{self.base_url}{path}"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        body = json.dumps(data).encode()
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())

    def is_ready(self) -> bool:
        return self._ready
