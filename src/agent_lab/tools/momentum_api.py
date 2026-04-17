from __future__ import annotations

from typing import Any

import httpx

from agent_lab.config import Settings
from agent_lab.momentum_configs import DEFAULT_MOMENTUM_REQUESTS


def _post_screening(
    base_url: str,
    endpoint: str,
    body: dict[str, Any],
    source_id: str,
    title: str,
) -> dict[str, Any]:
    url = f"{base_url}{endpoint}"

    try:
        with httpx.Client(timeout=20.0, trust_env=False) as client:
            response = client.post(url, json=body)
            response.raise_for_status()
            payload = response.json()

        return {
            "ok": True,
            "url": url,
            "request_body": body,
            "data": payload,
            "source": {
                "source_id": source_id,
                "source_type": "momentum_api",
                "title": title,
                "url": url,
            },
        }
    except httpx.HTTPStatusError as exc:
        return {
            "ok": False,
            "url": url,
            "request_body": body,
            "status_code": exc.response.status_code,
            "response_text": exc.response.text,
            "error": repr(exc),
            "source": {
                "source_id": source_id,
                "source_type": "momentum_api",
                "title": title,
                "url": url,
            },
        }
    except Exception as exc:
        return {
            "ok": False,
            "url": url,
            "request_body": body,
            "error": repr(exc),
            "source": {
                "source_id": source_id,
                "source_type": "momentum_api",
                "title": title,
                "url": url,
            },
        }


def fetch_all_momentum(settings: Settings) -> dict[str, Any]:
    results: dict[str, Any] = {}
    sources: list[dict[str, Any]] = []

    for key, cfg in DEFAULT_MOMENTUM_REQUESTS.items():
        result = _post_screening(
            base_url=settings.momentum_api_base_url,
            endpoint=cfg["endpoint"],
            body=cfg["body"],
            source_id=f"momentum_{key}",
            title=cfg["title"],
        )
        results[key] = result
        sources.append(result["source"])

    return {
        "results": results,
        "sources": sources,
    }