from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import httpx

from agent_lab.core.settings import Settings


def fetch_latest_regime(settings: Settings) -> dict[str, Any]:
    base_url = settings.signals_api_base_url.rstrip("/")
    url = f"{base_url}/api/regime/composite/latest"

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
                "source_id": "regime_composite_latest",
                "source_type": "macro_api",
                "title": "Latest composite regime",
                "url": url,
            },
        }
    except Exception as exc:
        return {
            "ok": False,
            "url": url,
            "error": repr(exc),
            "source": {
                "source_id": "regime_composite_latest",
                "source_type": "macro_api",
                "title": "Latest composite regime",
                "url": url,
            },
        }


def fetch_external_series(
    settings: Settings,
    series_name: str,
    lookback_days: int = 45,
) -> dict[str, Any]:
    base_url = settings.signals_api_base_url.rstrip("/")
    end = date.today()
    start = end - timedelta(days=lookback_days)
    url = f"{base_url}/api/external-data"
    params = {
        "seriesName": series_name,
        "start": start.isoformat(),
        "end": end.isoformat(),
    }

    try:
        with httpx.Client(timeout=20.0, trust_env=False) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()

        return {
            "ok": True,
            "url": url,
            "params": params,
            "data": payload,
            "source": {
                "source_id": f"external_{series_name.lower()}",
                "source_type": "macro_api",
                "title": f"External series {series_name}",
                "url": f"{url}?seriesName={series_name}",
            },
        }
    except Exception as exc:
        return {
            "ok": False,
            "url": url,
            "params": params,
            "error": repr(exc),
            "source": {
                "source_id": f"external_{series_name.lower()}",
                "source_type": "macro_api",
                "title": f"External series {series_name}",
                "url": f"{url}?seriesName={series_name}",
            },
        }
