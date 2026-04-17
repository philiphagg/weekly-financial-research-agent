from __future__ import annotations

from langchain_openai import ChatOpenAI

from .config import Settings


def build_llm(settings: Settings) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0,
        max_retries=2,
    )