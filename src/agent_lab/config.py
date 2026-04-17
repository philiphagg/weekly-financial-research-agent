from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_model: str
    market_api_base_url: str
    macro_api_base_url: str
    sector_rotation_api_base_url: str
    momentum_api_base_url: str
    signals_api_base_url: str
    tavily_api_key: str

    @staticmethod
    def load() -> "Settings":
        openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY saknas i .env")

        return Settings(
            openai_api_key=openai_api_key,
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip(),
            market_api_base_url=os.getenv("MARKET_API_BASE_URL", "").rstrip("/"),
            macro_api_base_url=os.getenv("MACRO_API_BASE_URL", "").rstrip("/"),
            sector_rotation_api_base_url=os.getenv("SECTOR_ROTATION_API_BASE_URL", "").rstrip("/"),
            momentum_api_base_url=os.getenv("MOMENTUM_API_BASE_URL", "").rstrip("/"),
            signals_api_base_url=os.getenv("SIGNALS_API_BASE_URL", "").rstrip("/"),
            tavily_api_key=os.getenv("TAVILY_API_KEY", "").strip(),
        )
