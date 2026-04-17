from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from agent_lab.config import Settings
from agent_lab.reporting import render_weekly_report
from agent_lab.momentum_normalizer import (
    MOMENTUM_STRATEGY_EXPLANATIONS,
    build_momentum_screener_tables,
    normalize_all_momentum,
    summarize_momentum,
)
from agent_lab.research_schemas import (
    ResearchPacket,
    ResearchState,
    SourceSummary,
    WebContextItem,
    WebContextSummary,
)
from agent_lab.sector_rotation_normalizer import normalize_sector_rotation, summarize_sector_rotation
from agent_lab.signals_normalizer import normalize_signals, summarize_signals
from agent_lab.tools.macro_api import fetch_macro_snapshot
from agent_lab.tools.market_api import fetch_market_snapshot
from agent_lab.tools.momentum_api import fetch_all_momentum
from agent_lab.tools.regime_api import fetch_external_series, fetch_latest_regime
from agent_lab.tools.sector_rotation_api import fetch_sector_rotation
from agent_lab.tools.signals_api import fetch_signals
from agent_lab.tools.web_search import fetch_web_search


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _week_label() -> str:
    now = datetime.now(timezone.utc)
    iso = now.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _merge_source(state: ResearchState, source: dict[str, Any]) -> list[dict[str, Any]]:
    source_copy = dict(source)
    source_copy.setdefault("timestamp_utc", _utc_now_iso())
    current_by_id = {
        existing["source_id"]: dict(existing)
        for existing in state.get("sources", [])
        if isinstance(existing, dict) and existing.get("source_id")
    }
    current_by_id[source_copy["source_id"]] = source_copy
    return list(current_by_id.values())


def _merge_gap(state: ResearchState, gap: str) -> list[str]:
    current = list(state.get("data_gaps", []))
    if gap not in current:
        current.append(gap)
    return current


def _dedupe_source_ids(source_ids: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for source_id in source_ids:
        if source_id and source_id not in seen:
            seen.add(source_id)
            ordered.append(source_id)
    return ordered


def _safe_json_loads(content: str) -> dict[str, Any]:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if "\n" in stripped:
            stripped = stripped.split("\n", 1)[1]
        if stripped.endswith("```"):
            stripped = stripped[:-3]
    return json.loads(stripped.strip())


def _summarize_source(source: dict[str, Any], details: str) -> dict[str, Any]:
    summary = SourceSummary(
        source_id=source["source_id"],
        title=source["title"],
        source_type=source["source_type"],
        summary=details,
        url=source.get("url"),
    )
    return summary.model_dump()


def _top_names(items: list[dict[str, Any]], key: str, limit: int = 5) -> list[str]:
    values = [str(item.get(key, "")).strip() for item in items if item.get(key)]
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            deduped.append(value)
    return deduped[:limit]


def _clean_text(text: str, max_sentences: int = 2, max_chars: int = 260) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    cleaned = re.sub(r"\[[^\]]+\]\([^)]+\)", "", cleaned)
    cleaned = re.sub(r"#+\s*", "", cleaned)
    cleaned = re.sub(r"\*+", "", cleaned)
    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    cleaned = " ".join(part.strip() for part in parts[:max_sentences] if part.strip())
    if len(cleaned) > max_chars:
        cleaned = cleaned[: max_chars - 3].rstrip() + "..."
    return cleaned


def _latest_series_point(points: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not points:
        return None
    sorted_points = sorted(
        [point for point in points if point.get("date") is not None],
        key=lambda point: point.get("date"),
    )
    return sorted_points[-1] if sorted_points else None


def _build_market_summary(state: ResearchState) -> dict[str, Any]:
    sector_summary = state.get("sector_rotation_summary", {})
    momentum_summary = state.get("momentum_summary", {})
    signal_summary = state.get("signal_summary", {})
    web_context = state.get("web_context_summary", {})
    market_raw = state.get("market_raw", {})
    market_source_ids = ["market_snapshot"]
    if not market_raw:
        market_source_ids = _dedupe_source_ids(
            ["sector_rotation", "signals_api"]
            + momentum_summary.get("source_ids", [])
            + web_context.get("source_ids", [])[:2]
        )

    leaders = _top_names(sector_summary.get("leading_observations", []), "name", limit=3)
    laggards = _top_names(sector_summary.get("lagging_observations", []), "name", limit=3)
    momentum_leaders = _top_names(momentum_summary.get("leaders", []), "ticker", limit=5)
    signal_bullish = _top_names(signal_summary.get("bullish_signals", []), "ticker", limit=5)

    if leaders or momentum_leaders:
        market_regime = "Constructive risk appetite with concentrated leadership"
    else:
        market_regime = "Market regime unclear because direct market snapshot data is missing"

    breadth_parts: list[str] = []
    if leaders:
        breadth_parts.append(f"Leadership is concentrated in {', '.join(leaders)}")
    if laggards:
        breadth_parts.append(f"while weakness remains in {', '.join(laggards)}")
    if not breadth_parts:
        breadth_parts.append("Breadth cannot be measured directly because market snapshot data is unavailable")

    price_parts: list[str] = []
    if momentum_leaders:
        price_parts.append(f"Momentum leaders include {', '.join(momentum_leaders)}")
    if signal_bullish:
        price_parts.append(f"and the signal block also highlights {', '.join(signal_bullish)}")
    if not price_parts:
        price_parts.append("Price-action context is limited because the market snapshot endpoint is unavailable")

    return {
        "market_regime": market_regime,
        "breadth_comment": "; ".join(breadth_parts) + ".",
        "price_action_comment": " ".join(price_parts).strip() + ".",
        "source_ids": market_source_ids,
    }


def _build_macro_summary(state: ResearchState) -> dict[str, Any]:
    macro_raw = state.get("macro_raw", {})
    external_series = macro_raw.get("external_series", {}) if isinstance(macro_raw, dict) else {}
    regime = macro_raw.get("regime") if isinstance(macro_raw, dict) else None

    hy_points = external_series.get("HY_OAS", [])
    vix_points = external_series.get("VIX", [])
    claims_points = external_series.get("UNEMPLOYMENT_CLAIMS", [])
    ism_points = external_series.get("ISM_PMI", [])

    hy_latest = _latest_series_point(hy_points)
    vix_latest = _latest_series_point(vix_points)
    claims_latest = _latest_series_point(claims_points)
    ism_latest = _latest_series_point(ism_points)

    macro_regime_parts: list[str] = []
    if regime:
        macro_regime_parts.append(
            f"Composite regime fallback reports {regime.get('regimeState', 'an unknown state')} with score {regime.get('compositeScore', 'n/a')}"
        )
    if hy_latest:
        macro_regime_parts.append(f"HY OAS latest reading is {hy_latest.get('value')} on {hy_latest.get('date')}")
    if vix_latest:
        macro_regime_parts.append(f"VIX latest reading is {vix_latest.get('value')} on {vix_latest.get('date')}")
    if not macro_regime_parts:
        macro_regime_parts.append("Primary macro snapshot failed and fallback macro data is only partially available")

    credit_comment = "Credit conditions are hard to assess because HY OAS fallback data is missing."
    if hy_points:
        hy_first = hy_points[0]
        hy_last = hy_points[-1]
        credit_comment = (
            f"HY OAS moved from {hy_first.get('value')} on {hy_first.get('date')} "
            f"to {hy_last.get('value')} on {hy_last.get('date')}."
        )

    risk_parts: list[str] = []
    if not claims_points:
        risk_parts.append("Initial claims fallback data is missing")
    elif claims_latest:
        risk_parts.append(
            f"initial claims latest reading is {claims_latest.get('value')} on {claims_latest.get('date')}"
        )
    if not ism_points:
        risk_parts.append("ISM PMI fallback data is missing")
    elif ism_latest:
        risk_parts.append(f"ISM PMI latest reading is {ism_latest.get('value')} on {ism_latest.get('date')}")
    if vix_latest:
        risk_parts.append(f"VIX latest reading is {vix_latest.get('value')}")
    if not risk_parts:
        risk_parts.append("Macro risk is hard to assess because both primary and fallback macro feeds are thin")

    return {
        "macro_regime": ". ".join(macro_regime_parts) + ".",
        "credit_comment": credit_comment,
        "risk_comment": "; ".join(risk_parts) + ".",
        "term_explanations": {
            "HY_OAS": "HY_OAS means High Yield Option-Adjusted Spread. It tracks the extra yield demanded for lower-quality corporate debt, and wider spreads usually point to rising stress or tighter financial conditions.",
            "VIX": "VIX is the CBOE Volatility Index. It is an options-implied volatility measure for US equities, and sharp increases usually signal more fear and demand for downside protection.",
        },
        "source_ids": _dedupe_source_ids(
            ["macro_snapshot", "regime_composite_latest", "external_hy_oas", "external_unemployment_claims", "external_ism_pmi", "external_vix"]
        ),
    }


def _fallback_computed_analysis(state: ResearchState) -> dict[str, Any]:
    sector_summary = state.get("sector_rotation_summary", {})
    momentum_summary = state.get("momentum_summary", {})
    signal_summary = state.get("signal_summary", {})
    web_context = state.get("web_context_summary", {})

    leading = _top_names(sector_summary.get("leading_observations", []), "name", limit=3)
    lagging = _top_names(sector_summary.get("lagging_observations", []), "name", limit=3)
    momentum_leaders = _top_names(momentum_summary.get("leaders", []), "ticker", limit=5)
    contradictions = signal_summary.get("contradictions_to_momentum", [])
    watchlist = _top_names(web_context.get("watchlist", []), "headline", limit=2)

    base_case_parts: list[str] = []
    if momentum_leaders:
        base_case_parts.append(f"Stay with the strongest momentum names such as {', '.join(momentum_leaders[:3])}")
    if leading:
        base_case_parts.append(f"while leaning toward leading areas like {', '.join(leading)}")
    if lagging:
        base_case_parts.append(f"and staying cautious on lagging areas like {', '.join(lagging)}")
    if watchlist:
        base_case_parts.append(f"ahead of this week's catalysts including {', '.join(watchlist)}")
    if not base_case_parts:
        base_case_parts.append("Stay selective until the data picture improves")

    key_risks = [
        "Leadership remains concentrated rather than broad-based",
        "Primary market and macro snapshot endpoints are unavailable",
    ]
    if contradictions:
        key_risks.append("Signal contradictions are appearing beneath the headline momentum trend")
    if state.get("data_gaps"):
        key_risks.append("Data gaps reduce confidence in the weekly base case")

    what_would_change = [
        "Leadership broadens beyond the current narrow set of leaders",
        "Signal contradictions start to dominate the current bullish signal mix",
        "Macro fallback data deteriorates further through wider credit spreads or higher volatility",
    ]

    return {
        "base_case": " ".join(base_case_parts).strip() + ".",
        "key_risks": key_risks,
        "what_would_change_my_mind": what_would_change,
        "source_ids": _dedupe_source_ids(
            state.get("momentum_summary", {}).get("source_ids", [])
            + ["sector_rotation", "signals_api"]
            + state.get("web_context_summary", {}).get("source_ids", [])
        ),
    }


def build_research_graph(settings: Settings):
    model = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0,
        max_retries=2,
    )

    def collect_market_snapshot(state: ResearchState) -> dict[str, Any]:
        result = fetch_market_snapshot(settings)
        updates: dict[str, Any] = {
            "sources": _merge_source(state, result["source"]),
            "source_summaries": list(state.get("source_summaries", [])),
        }
        if result["ok"]:
            updates["market_raw"] = result["data"]
            updates["source_summaries"].append(
                _summarize_source(result["source"], "Market snapshot API response was collected successfully.")
            )
        else:
            updates["market_raw"] = {}
            updates["data_gaps"] = _merge_gap(
                state, f"Market snapshot unavailable: {result['error']}"
            )
            updates["source_summaries"].append(
                _summarize_source(result["source"], f"Market snapshot API failed: {result['error']}")
            )
        return updates

    def collect_macro_snapshot(state: ResearchState) -> dict[str, Any]:
        result = fetch_macro_snapshot(settings)
        updates: dict[str, Any] = {
            "sources": _merge_source(state, result["source"]),
            "source_summaries": list(state.get("source_summaries", [])),
        }
        if result["ok"]:
            updates["macro_raw"] = result["data"]
            updates["source_summaries"].append(
                _summarize_source(result["source"], "Macro snapshot API response was collected successfully.")
            )
        else:
            fallback_sources = list(updates["sources"])
            fallback_summaries = list(updates["source_summaries"])
            macro_fallback: dict[str, Any] = {
                "snapshot_error": result["error"],
                "regime": None,
                "external_series": {},
            }

            regime_result = fetch_latest_regime(settings)
            fallback_sources = _merge_source({"sources": fallback_sources}, regime_result["source"])
            fallback_summaries.append(
                _summarize_source(
                    regime_result["source"],
                    "Latest regime composite retrieved successfully."
                    if regime_result["ok"]
                    else f"Latest regime composite request failed: {regime_result['error']}",
                )
            )
            if regime_result["ok"]:
                macro_fallback["regime"] = regime_result["data"]
            else:
                updates["data_gaps"] = _merge_gap(
                    state, f"Regime fallback unavailable: {regime_result['error']}"
                )

            for series_name in ("HY_OAS", "UNEMPLOYMENT_CLAIMS", "ISM_PMI", "VIX"):
                series_result = fetch_external_series(settings, series_name=series_name)
                fallback_sources = _merge_source({"sources": fallback_sources}, series_result["source"])
                fallback_summaries.append(
                    _summarize_source(
                        series_result["source"],
                        f"External series {series_name} returned {len(series_result.get('data', []))} points."
                        if series_result["ok"]
                        else f"External series {series_name} request failed: {series_result['error']}",
                    )
                )
                if series_result["ok"]:
                    macro_fallback["external_series"][series_name] = series_result["data"]
                else:
                    existing_gaps = list(updates.get("data_gaps", state.get("data_gaps", [])))
                    gap = f"External macro series {series_name} unavailable: {series_result['error']}"
                    if gap not in existing_gaps:
                        existing_gaps.append(gap)
                    updates["data_gaps"] = existing_gaps

            updates["macro_raw"] = macro_fallback
            updates["sources"] = fallback_sources
            updates["source_summaries"] = fallback_summaries
            updates["data_gaps"] = _merge_gap(
                {"data_gaps": updates.get("data_gaps", state.get("data_gaps", []))},
                f"Macro snapshot unavailable: {result['error']}",
            )
            updates["source_summaries"].append(
                _summarize_source(
                    result["source"],
                    f"Primary macro snapshot API failed, fallback macro sources were attempted: {result['error']}",
                )
            )
        return updates

    def collect_sector_rotation(state: ResearchState) -> dict[str, Any]:
        result = fetch_sector_rotation(settings)
        updates: dict[str, Any] = {
            "sources": _merge_source(state, result["source"]),
            "source_summaries": list(state.get("source_summaries", [])),
        }
        if result["ok"]:
            updates["sector_rotation_raw"] = result["data"]
            instrument_count = len(result["data"].get("instruments", []))
            updates["source_summaries"].append(
                _summarize_source(
                    result["source"],
                    f"Sector rotation API returned {instrument_count} instruments for weekly analysis.",
                )
            )
        else:
            updates["sector_rotation_raw"] = {}
            updates["data_gaps"] = _merge_gap(
                state, f"Sector rotation unavailable: {result['error']}"
            )
            updates["source_summaries"].append(
                _summarize_source(result["source"], f"Sector rotation API failed: {result['error']}")
            )
        return updates

    def normalize_sector_rotation_node(state: ResearchState) -> dict[str, Any]:
        observations = normalize_sector_rotation(state.get("sector_rotation_raw", {}))
        summary = summarize_sector_rotation(observations).model_dump()
        summary["source_ids"] = ["sector_rotation"]

        return {
            "normalized_sector_rotation": [o.model_dump() for o in observations],
            "sector_rotation_summary": summary,
        }

    def collect_momentum(state: ResearchState) -> dict[str, Any]:
        result = fetch_all_momentum(settings)

        sources = list(state.get("sources", []))
        for source in result["sources"]:
            sources = _merge_source({"sources": sources}, source)

        source_summaries = list(state.get("source_summaries", []))
        data_gaps = list(state.get("data_gaps", []))
        momentum_raw: dict[str, Any] = {}

        for key, payload in result["results"].items():
            source_summaries.append(
                _summarize_source(
                    payload["source"],
                    f"Momentum screen '{key}' {'succeeded' if payload['ok'] else 'failed'}."
                )
            )
            if payload["ok"]:
                momentum_raw[key] = payload["data"]
            else:
                momentum_raw[key] = {}
                gap = f"Momentum source '{key}' unavailable: {payload['error']}"
                if gap not in data_gaps:
                    data_gaps.append(gap)

        return {
            "momentum_raw": momentum_raw,
            "sources": sources,
            "source_summaries": source_summaries,
            "data_gaps": data_gaps,
        }

    def normalize_momentum(state: ResearchState) -> dict[str, Any]:
        observations = normalize_all_momentum(state.get("momentum_raw", {}))
        summary = summarize_momentum(observations).model_dump()
        summary["strategy_explanations"] = MOMENTUM_STRATEGY_EXPLANATIONS
        summary["screener_tables"] = build_momentum_screener_tables(
            state.get("momentum_raw", {}),
            limit=20,
        )
        summary["source_ids"] = _dedupe_source_ids(
            [
                source.get("source_id", "")
                for source in state.get("sources", [])
                if source.get("source_type") == "momentum_api"
            ]
        )

        return {
            "normalized_momentum": [obs.model_dump() for obs in observations],
            "momentum_summary": summary,
        }

    def collect_signals(state: ResearchState) -> dict[str, Any]:
        result = fetch_signals(settings)
        updates: dict[str, Any] = {
            "sources": _merge_source(state, result["source"]),
            "source_summaries": list(state.get("source_summaries", [])),
        }
        if result["ok"]:
            updates["signals_raw"] = result["data"]
            total_count = result["data"].get("totalCount")
            if total_count is None and isinstance(result["data"].get("signals"), list):
                total_count = len(result["data"]["signals"])
            updates["source_summaries"].append(
                _summarize_source(
                    result["source"],
                    f"Signals API returned {total_count if total_count is not None else 'an unknown number of'} active stock signals.",
                )
            )
        else:
            updates["signals_raw"] = {}
            updates["data_gaps"] = _merge_gap(state, f"Signals API unavailable: {result['error']}")
            updates["source_summaries"].append(
                _summarize_source(result["source"], f"Signals API failed: {result['error']}")
            )
        return updates

    def normalize_signals_node(state: ResearchState) -> dict[str, Any]:
        observations = normalize_signals(state.get("signals_raw", {}))
        summary = summarize_signals(
            observations,
            momentum_summary=state.get("momentum_summary", {}),
        ).model_dump()
        summary["source_ids"] = ["signals_api"]
        return {
            "normalized_signals": [obs.model_dump() for obs in observations],
            "signal_summary": summary,
        }

    def collect_web_context(state: ResearchState) -> dict[str, Any]:
        source_summaries = list(state.get("source_summaries", []))
        sources = list(state.get("sources", []))
        data_gaps = list(state.get("data_gaps", []))
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        queries = {
            "weekend_context": (
                "Most important stock market developments, macro catalysts, and sector news affecting US equities "
                f"heading into the next trading week as of {now}"
            ),
            "what_to_watch": (
                "Key stock market events, earnings, macro releases, and catalysts to watch in the coming US trading week "
                f"as of {now}"
            ),
        }

        weekend_context: list[dict[str, Any]] = []
        watchlist: list[dict[str, Any]] = []
        overview_parts: list[str] = []
        seen_urls: set[str] = set()

        for key, query in queries.items():
            result = fetch_web_search(settings, query=query, max_results=3, topic="news")
            if not result["ok"]:
                gap = f"Web search unavailable for {key}: {result['error']}"
                if gap not in data_gaps:
                    data_gaps.append(gap)
                continue

            raw = result["data"]
            answer = raw.get("answer") or ""
            if answer:
                overview_parts.append(_clean_text(answer, max_sentences=2, max_chars=260))

            for index, item in enumerate(raw.get("results", []), start=1):
                item_url = item.get("url")
                if item_url and item_url in seen_urls:
                    continue
                if item_url:
                    seen_urls.add(item_url)

                short_summary = _clean_text(
                    item.get("content") or answer or "No summary provided.",
                    max_sentences=2,
                    max_chars=240,
                )
                source_id = f"web_{key}_{index}"
                source = {
                    "source_id": source_id,
                    "source_type": "web",
                    "title": item.get("title") or f"Web result for {key}",
                    "url": item_url,
                    "timestamp_utc": _utc_now_iso(),
                    "summary": short_summary,
                }
                sources = _merge_source({"sources": sources}, source)
                source_summaries.append(
                    _summarize_source(
                        source,
                        short_summary or f"Web enrichment result for {key}.",
                    )
                )
                entry = WebContextItem(
                    headline=item.get("title") or f"Web result {index}",
                    summary=short_summary,
                    url=item_url,
                    source_id=source_id,
                ).model_dump()
                if key == "weekend_context":
                    weekend_context.append(entry)
                else:
                    watchlist.append(entry)

        summary = WebContextSummary(
            weekend_context=weekend_context[:5],
            watchlist=watchlist[:5],
            overview=" ".join(part.strip() for part in overview_parts if part).strip(),
            data_gaps=[],
        ).model_dump()
        summary["source_ids"] = _dedupe_source_ids(
            [item.get("source_id", "") for item in weekend_context + watchlist]
        )

        if not weekend_context:
            summary["data_gaps"].append("No weekend context results were collected.")
        if not watchlist:
            summary["data_gaps"].append("No weekly watchlist results were collected.")

        return {
            "web_search_raw": {"queries": queries},
            "web_context_summary": summary,
            "sources": sources,
            "source_summaries": source_summaries,
            "data_gaps": data_gaps,
        }

    def analyze_packet(state: ResearchState) -> dict[str, Any]:
        market_summary = _build_market_summary(state)
        macro_summary = _build_macro_summary(state)
        computed_analysis = _fallback_computed_analysis(state)

        prompt = f"""
You are a systematic market analyst refining a weekly stock market research packet.

Rules:
- Do not invent facts that are not supported by the supplied packet inputs.
- Improve the clarity of the existing draft rather than changing its meaning.
- Keep the output concise.
- If data is thin or missing, say so explicitly.
- Return JSON only.

Desired JSON structure:
{{
  "computed_analysis": {{
    "base_case": "",
    "key_risks": [],
    "what_would_change_my_mind": []
  }}
}}

INPUT:
{json.dumps({
    "draft_market_summary": market_summary,
    "draft_macro_summary": macro_summary,
    "sector_rotation_summary": state.get("sector_rotation_summary", {}),
    "momentum_summary": state.get("momentum_summary", {}),
    "signal_summary": state.get("signal_summary", {}),
    "web_context_summary": state.get("web_context_summary", {}),
    "draft_computed_analysis": computed_analysis,
    "data_gaps": state.get("data_gaps", []),
}, ensure_ascii=False)}
""".strip()

        try:
            response = model.invoke(prompt)
            content = response.content if isinstance(response.content, str) else str(response.content)
            parsed = _safe_json_loads(content)
            computed_analysis = parsed.get("computed_analysis", computed_analysis)
        except Exception:
            pass

        computed_analysis["source_ids"] = _dedupe_source_ids(
            computed_analysis.get("source_ids", [])
            or [
                "market_snapshot",
                "macro_snapshot",
                "sector_rotation",
                "signals_api",
            ]
            + state.get("momentum_summary", {}).get("source_ids", [])
            + state.get("web_context_summary", {}).get("source_ids", [])
        )

        run_metadata = {
            **state.get("run_metadata", {}),
            "completed_at_utc": _utc_now_iso(),
            "week_label": state["week_label"],
            "model": settings.openai_model,
            "source_count": len(state.get("sources", [])),
            "source_summary_count": len(state.get("source_summaries", [])),
            "data_gap_count": len(state.get("data_gaps", [])),
            "data_gaps": state.get("data_gaps", []),
        }

        packet = ResearchPacket(
            week_label=state["week_label"],
            run_metadata=run_metadata,
            market_summary=market_summary,
            macro_summary=macro_summary,
            sector_rotation_summary=state.get("sector_rotation_summary", {}),
            momentum_summary=state.get("momentum_summary", {}),
            signal_summary=state.get("signal_summary", {}),
            web_context_summary=state.get("web_context_summary", {}),
            computed_analysis=computed_analysis,
            sources=state.get("sources", []),
            source_summaries=state.get("source_summaries", []),
            data_gaps=state.get("data_gaps", []),
        )

        return {
            "run_metadata": packet.run_metadata,
            "market_summary": packet.market_summary,
            "macro_summary": packet.macro_summary,
            "computed_analysis": packet.computed_analysis,
            "final_packet": packet.model_dump(),
        }

    def build_weekly_report(state: ResearchState) -> dict[str, Any]:
        report = render_weekly_report(state.get("final_packet", {}))
        return {"weekly_report": report}

    builder = StateGraph(ResearchState)
    builder.add_node("collect_market_snapshot", collect_market_snapshot)
    builder.add_node("collect_macro_snapshot", collect_macro_snapshot)
    builder.add_node("collect_sector_rotation", collect_sector_rotation)
    builder.add_node("normalize_sector_rotation", normalize_sector_rotation_node)
    builder.add_node("collect_momentum", collect_momentum)
    builder.add_node("normalize_momentum", normalize_momentum)
    builder.add_node("collect_signals", collect_signals)
    builder.add_node("normalize_signals", normalize_signals_node)
    builder.add_node("collect_web_context", collect_web_context)
    builder.add_node("analyze_packet", analyze_packet)
    builder.add_node("build_weekly_report", build_weekly_report)

    builder.add_edge(START, "collect_market_snapshot")
    builder.add_edge("collect_market_snapshot", "collect_macro_snapshot")
    builder.add_edge("collect_macro_snapshot", "collect_sector_rotation")
    builder.add_edge("collect_sector_rotation", "normalize_sector_rotation")
    builder.add_edge("normalize_sector_rotation", "collect_momentum")
    builder.add_edge("collect_momentum", "normalize_momentum")
    builder.add_edge("normalize_momentum", "collect_signals")
    builder.add_edge("collect_signals", "normalize_signals")
    builder.add_edge("normalize_signals", "collect_web_context")
    builder.add_edge("collect_web_context", "analyze_packet")
    builder.add_edge("analyze_packet", "build_weekly_report")
    builder.add_edge("build_weekly_report", END)

    graph = builder.compile()
    return graph


def initial_state() -> ResearchState:
    return {
        "week_label": _week_label(),
        "run_metadata": {
            "started_at_utc": _utc_now_iso(),
        },
        "sources": [],
        "source_summaries": [],
        "data_gaps": [],
    }
