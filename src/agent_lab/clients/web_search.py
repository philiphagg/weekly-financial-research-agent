from __future__ import annotations

from typing import Any

from langchain.tools import tool
from tavily import TavilyClient

from agent_lab.core.settings import Settings


def fetch_web_search(
    settings: Settings,
    query: str,
    max_results: int = 5,
    topic: str = "news",
) -> dict[str, Any]:
    if not settings.tavily_api_key:
        return {
            "ok": False,
            "query": query,
            "error": "TAVILY_API_KEY is not configured",
            "results": [],
        }

    client = TavilyClient(api_key=settings.tavily_api_key)
    result = client.search(
        query=query,
        max_results=max_results,
        topic=topic,
        search_depth="basic",
        include_answer=True,
    )
    return {
        "ok": True,
        "query": query,
        "topic": topic,
        "data": result,
    }


def build_web_search_tool(settings: Settings):
    @tool("search_web")
    def search_web(
        query: str,
        max_results: int = 5,
        topic: str = "news",
    ) -> dict[str, Any]:
        """
        Search the web for recent information about companies, sectors, macro events,
        earnings, or risk factors relevant to portfolio construction.
        """
        return fetch_web_search(
            settings=settings,
            query=query,
            max_results=max_results,
            topic=topic,
        )

    return search_web
