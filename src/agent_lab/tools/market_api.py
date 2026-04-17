from __future__ import annotations

from typing import Any

import httpx

from agent_lab.config import Settings


def fetch_market_snapshot(settings: Settings) -> dict[str, Any]:
    url = f"{settings.market_api_base_url}/api/v1/market-snapshot"

    try:
        with httpx.Client(timeout=20.0, trust_env=False) as client:
            response = client.get(url)
            response.raise_for_status()
            payload = response.json()

        return {
            "ok": True,
            "url": url,
            "data": payload,
            "source": {
                "source_id": "market_snapshot",
                "source_type": "market_api",
                "title": "Market snapshot API",
                "url": url,
            },
        }
    except Exception as exc:
        return {
            "ok": False,
            "url": url,
            "error": repr(exc),
            "source": {
                "source_id": "market_snapshot",
                "source_type": "market_api",
                "title": "Market snapshot API",
                "url": url,
            },
        }