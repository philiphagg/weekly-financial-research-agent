from __future__ import annotations

from typing import Any


DEFAULT_MOMENTUM_REQUESTS: dict[str, dict[str, Any]] = {
    "time_series": {
        "endpoint": "/api/v1/screen/tsmom",
        "title": "Time-series momentum screener",
        "body": {
            "universeCode": "SWEDEN_DEFAULT",
            "com": 60,
            "lookbackMonths": 12,
        },
    },
    "price": {
        "endpoint": "/api/v1/screen/price-momentum",
        "title": "Price momentum screener",
        "body": {
            # Provisorisk tills vi sett PriceMomentumRequest
            "universeCode": "SWEDEN_DEFAULT",
            "formationWindow": "MONTH_6",
            "skipMonths": 1,
            "percentToKeep": 100,
        },
    },
    "low_volatility": {
        "endpoint": "/api/v1/screen/low-volatility",
        "title": "Low-volatility screener",
        "body": {
            "universeCode": "SWEDEN_DEFAULT",
            "formationWindow": "YEAR_1",
            "portfolioLimit": 500,
        },
    },
    "multi_factor": {
        "endpoint": "/api/v1/screen/multi-factor",
        "title": "Multi-factor screener",
        "body": {
            "universeCode": "SWEDEN_DEFAULT",
            "momentumWindow": "MONTH_6",
            "skipMonths": 1,
            "volatilityWindow": "YEAR_1",
            "percentToKeep": 100,
        },
    },
    "residual": {
        "endpoint": "/api/v1/screen/residual-momentum",
        "title": "Residual momentum screener",
        "body": {
            "universeCode": "SWEDEN_DEFAULT",
            "betaWindowMonths": 36,
            "formationWindowMonths": 12,
            "skipMonths": 1,
            "percentToKeep": 100,
        },
    },
}