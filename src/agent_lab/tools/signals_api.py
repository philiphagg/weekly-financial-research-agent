from __future__ import annotations

from typing import Any

import httpx
from langchain.tools import tool

from agent_lab.config import Settings


def fetch_signals(settings: Settings) -> dict[str, Any]:
    headers: dict[str, str] = {}
    url = f"{settings.signals_api_base_url}/api/v1/signals"
    params = {
        "status": "ACTIVE",
        "assetType": "stock",
    }

    try:
        with httpx.Client(timeout=20.0, trust_env=False) as client:
            response = client.get(url, params=params, headers=headers)
            response.raise_for_status()
            payload = response.json()

        return {
            "ok": True,
            "url": url,
            "params": params,
            "data": payload,
            "source": {
                "source_id": "signals_api",
                "source_type": "signals_api",
                "title": "Signals API",
                "url": url,
            },
        }

    except Exception as exc:
        return {
            "ok": False,
            "url": url,
            "params": params,
            "error": repr(exc),
            "source": {
                "source_id": "signals_api",
                "source_type": "signals_api",
                "title": "Signals API",
                "url": url,
            },
        }


def build_signals_tool(settings: Settings):
    @tool("fetch_signals")
    def fetch_signals_tool() -> dict[str, Any]:
        """
        Fetch quantitative signals from the portfolio signal API.
        """
        return fetch_signals(settings)

    return fetch_signals_tool
