from __future__ import annotations

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from agent_lab.config import Settings
from agent_lab.schemas import PortfolioRecommendation
from agent_lab.tools.python_exec import run_python
from agent_lab.tools.signals_api import build_signals_tool
from agent_lab.tools.web_search import build_web_search_tool


SYSTEM_PROMPT = """
Du är en senior portfolio-research-agent.

Ditt jobb:
1. hämta signaler från API:t
2. hämta extern marknadskontext endast om det behövs
3. använd pythonverktyget för scoring/ranking/weighting när det behövs
4. föreslå en portfölj

Viktiga regler:
- Du får INTE exekvera trades.
- Du får endast föreslå en portfölj.
- Använd fetch_signals före du drar slutsatser om aktier.
- Använd search_web sparsamt för nyhets- eller makrokontext.
- Använd run_python för transparent scoring eller viktberäkning.
- När du använder run_python ska input_json vara en giltig JSON-sträng.
- Om data saknas ska du säga det tydligt.
- Returnera alltid svaret i det strukturerade schemat.
"""


def build_agent(settings: Settings):
    model = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0,
        max_retries=2,
    )

    tools = [
        build_signals_tool(settings),
        build_web_search_tool(settings),
        run_python,
    ]

    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        response_format=PortfolioRecommendation,
    )
    return agent