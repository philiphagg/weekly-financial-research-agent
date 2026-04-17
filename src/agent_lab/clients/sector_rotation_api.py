from __future__ import annotations

from typing import Any

import httpx

from agent_lab.core.settings import Settings


def fetch_sector_rotation(settings: Settings) -> dict[str, Any]:
    url = f"{settings.sector_rotation_api_base_url}/api/v1/sector-rotation/weekly"

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
                "source_id": "sector_rotation",
                "source_type": "sector_rotation_api",
                "title": "Sector rotation API",
                "url": url,
            },
        }
    except Exception as exc:
        return {
            "ok": False,
            "url": url,
            "error": repr(exc),
            "source": {
                "source_id": "sector_rotation",
                "source_type": "sector_rotation_api",
                "title": "Sector rotation API",
                "url": url,
            },
        }
