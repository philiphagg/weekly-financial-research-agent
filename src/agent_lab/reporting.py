from __future__ import annotations

import re
from typing import Any


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def _citation(source_ids: list[str]) -> str:
    clean_ids = [source_id for source_id in source_ids if source_id]
    if not clean_ids:
        return ""
    refs = ", ".join(clean_ids)
    return f" (sources: {refs})"


def _bullet_lines(items: list[str], fallback: str) -> str:
    clean_items = [item for item in items if item]
    if not clean_items:
        clean_items = [fallback]
    return "\n".join(f"- {item}" for item in clean_items)


def _context_lines(items: list[dict[str, Any]], fallback: str) -> str:
    if not items:
        return f"- {fallback}"

    lines: list[str] = []
    for item in items:
        headline = item.get("headline") or "Untitled"
        summary = _clean_text(item.get("summary") or "", max_sentences=2, max_chars=280)
        source_id = item.get("source_id")
        source_ref = f" [{source_id}]" if source_id else ""
        lines.append(f"- {headline}: {summary}{source_ref}")
    return "\n".join(lines)


def _render_ranked_table(items: list[dict[str, Any]], heading: str, limit: int = 10) -> str:
    if not items:
        return f"### {heading}\nNo entries available."

    header = f"### {heading}\n| Rank | Name | Score | Price |\n| --- | --- | --- | --- |"
    rows = []
    for index, item in enumerate(items[:limit], start=1):
        score = item.get("score")
        price = item.get("price")
        score_text = f"{score:.4f}" if isinstance(score, (int, float)) else "n/a"
        price_text = f"{price:.2f}" if isinstance(price, (int, float)) else "n/a"
        rows.append(f"| {index} | {item.get('ticker', 'Unknown')} | {score_text} | {price_text} |")
    return header + "\n" + "\n".join(rows)


def _render_signal_table(items: list[dict[str, Any]], limit: int = 12) -> str:
    if not items:
        return "No active signal table available."

    header = "| Name | Signal | Direction | Confidence | Notes |\n| --- | --- | --- | --- | --- |"
    rows = []
    for item in items[:limit]:
        confidence = item.get("confidence")
        confidence_text = f"{confidence:.2f}" if isinstance(confidence, (int, float)) else "n/a"
        rows.append(
            f"| {item.get('ticker', 'Unknown')} | {item.get('signal_name', 'Unknown')} | {item.get('direction', 'n/a')} | {confidence_text} | {_clean_text(item.get('notes') or '', max_sentences=1, max_chars=80) or 'n/a'} |"
        )
    return header + "\n" + "\n".join(rows)


def _render_sector_rotation_table(items: list[dict[str, Any]], limit: int = 16) -> str:
    if not items:
        return "No sector rotation table available."

    header = (
        "| Name | Quadrant | Week-anchor | 1W | 2W | Rotation score |\n"
        "| --- | --- | --- | --- | --- | --- |"
    )
    rows = []
    for item in items[:limit]:
        wa = item.get("week_anchor_return")
        ow = item.get("one_week_return")
        tw = item.get("two_week_return")
        score = item.get("rotation_score")
        rows.append(
            "| {name} | {quadrant} | {wa} | {ow} | {tw} | {score} |".format(
                name=item.get("name", "Unknown"),
                quadrant=item.get("quadrant", "n/a"),
                wa=f"{wa:.2%}" if isinstance(wa, (int, float)) else "n/a",
                ow=f"{ow:.2%}" if isinstance(ow, (int, float)) else "n/a",
                tw=f"{tw:.2%}" if isinstance(tw, (int, float)) else "n/a",
                score=f"{score:.4f}" if isinstance(score, (int, float)) else "n/a",
            )
        )
    return header + "\n" + "\n".join(rows)


def _clean_text(text: str, max_sentences: int = 2, max_chars: int = 240) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    cleaned = re.sub(r"\[[^\]]+\]\([^)]+\)", "", cleaned)
    cleaned = re.sub(r"#+\s*", "", cleaned)
    cleaned = re.sub(r"\*+", "", cleaned)

    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    cleaned = " ".join(part.strip() for part in parts[:max_sentences] if part.strip())
    if len(cleaned) > max_chars:
        cleaned = cleaned[: max_chars - 3].rstrip() + "..."
    return cleaned


def render_weekly_report(packet: dict[str, Any]) -> str:
    market_summary = packet.get("market_summary", {})
    macro_summary = packet.get("macro_summary", {})
    sector_rotation = packet.get("sector_rotation_summary", {})
    momentum_summary = packet.get("momentum_summary", {})
    signal_summary = packet.get("signal_summary", {})
    web_context = packet.get("web_context_summary", {})
    computed = packet.get("computed_analysis", {})
    run_metadata = packet.get("run_metadata", {})
    sources = _as_list(packet.get("sources"))
    source_summaries = _as_list(packet.get("source_summaries"))
    data_gaps = _as_list(packet.get("data_gaps"))
    strategy_explanations = momentum_summary.get("strategy_explanations", {})
    screener_tables = _as_list(momentum_summary.get("screener_tables"))
    term_explanations = macro_summary.get("term_explanations", {})
    sector_rotation_table = _as_list(sector_rotation.get("rotation_table"))

    source_summary_map = {
        item.get("source_id"): item
        for item in source_summaries
        if isinstance(item, dict) and item.get("source_id")
    }

    executive_points = [
        market_summary.get("market_regime", ""),
        macro_summary.get("macro_regime", ""),
        computed.get("base_case", ""),
    ]
    executive_points = [point for point in executive_points if point]

    source_lines = []
    for source in sources:
        source_id = source.get("source_id", "unknown_source")
        title = source.get("title", "Untitled source")
        source_type = source.get("source_type", "unknown")
        url = source.get("url") or "n/a"
        summary = (
            source.get("summary")
            or source_summary_map.get(source_id, {}).get("summary")
            or "No summary available."
        )
        summary = _clean_text(summary, max_sentences=1, max_chars=220)
        source_lines.append(f"- [{source_id}] {title} ({source_type}) - {summary} - {url}")

    screener_blocks = []
    for screener in screener_tables:
        title = screener.get("title", "Momentum screener")
        description = screener.get("description", "")
        leaders_table = _render_ranked_table(screener.get("leaders", []), "Top leaders", limit=20)
        laggards_table = _render_ranked_table(list(reversed(screener.get("laggards", []))), "Bottom laggards", limit=20)
        screener_blocks.append(
            f"### {title}\n{description}\n\n{leaders_table}\n\n{laggards_table}"
        )

    strategy_lines = []
    for key, description in strategy_explanations.items():
        strategy_lines.append(f"`{key}`: {description}")

    macro_explanation_lines = []
    for term, description in term_explanations.items():
        macro_explanation_lines.append(f"`{term}`: {description}")

    chart_section = "![VIX chart](./vix_chart.svg)"

    sections = [
        f"# Weekly Stock Market Science Report\n\nWeek: {packet.get('week_label', 'unknown')}\nGenerated: {run_metadata.get('completed_at_utc', 'unknown')}",
        "## Executive summary\n"
        + _bullet_lines(executive_points, "Base case could not be generated.")
        + _citation(_as_list(computed.get("source_ids"))),
        "## Facts\n"
        + _bullet_lines(
            [
                market_summary.get("breadth_comment", ""),
                market_summary.get("price_action_comment", ""),
                macro_summary.get("credit_comment", ""),
                sector_rotation.get("positioning_comment", ""),
            ],
            "No factual snapshot available.",
        ),
        "## Interpretation\n"
        + _bullet_lines(
            [
                momentum_summary.get("interpretation", ""),
                signal_summary.get("interpretation", ""),
                macro_summary.get("risk_comment", ""),
            ],
            "No interpretation available.",
        ),
        "## Positioning for the week\n"
        + _bullet_lines(
            [computed.get("base_case", ""), sector_rotation.get("positioning_comment", "")],
            "No positioning guidance available.",
        ),
        "## How to read the momentum strategies\n"
        + _bullet_lines(
            strategy_lines,
            "No strategy explanations available.",
        ),
        "## Sector / theme rotation\n"
        + _bullet_lines(
            [
                "Leading sectors: " + ", ".join(_as_list(sector_rotation.get("leading_sectors"))),
                "Lagging sectors: " + ", ".join(_as_list(sector_rotation.get("lagging_sectors"))),
            ],
            "No sector rotation observations available.",
        )
        + _citation(_as_list(sector_rotation.get("source_ids")))
        + "\n\n### Quadrant scatter\n"
        + "![Sector rotation scatter](./sector_rotation_scatter.svg)"
        + "\n\n### Category grid\n"
        + "![Sector rotation category grid](./sector_rotation_grid.svg)"
        + "\n\n### Sector rotation table\n"
        + _render_sector_rotation_table(sector_rotation_table, limit=20),
        "## Momentum leaders and laggards\n"
        + _bullet_lines(
            [
                "Leaders: " + ", ".join(
                    item.get("ticker", "") for item in _as_list(momentum_summary.get("leaders"))
                ),
                "Laggards: " + ", ".join(
                    item.get("ticker", "") for item in _as_list(momentum_summary.get("laggards"))
                ),
            ],
            "No momentum leaders or laggards available.",
        )
        + _citation(_as_list(momentum_summary.get("source_ids"))),
        "## Signals in focus\n"
        + "This section highlights which active technical signals confirm the current momentum picture and which names have repeated bullish or bearish setups.\n\n"
        + _bullet_lines(
            signal_summary.get("support_for_momentum", [])
            + signal_summary.get("contradictions_to_momentum", []),
            "No signal conclusions available.",
        )
        + _citation(_as_list(signal_summary.get("source_ids")))
        + "\n\n### Active signal table\n"
        + _render_signal_table(_as_list(signal_summary.get("signal_table")), limit=15),
        "## Momentum screener detail\n"
        + ("This section shows the exact ranked names behind each screener so the report carries the actual evidence, not just a compressed summary.\n\n" + "\n\n".join(screener_blocks) if screener_blocks else "No screener tables available."),
        "## Macro context notes\n"
        + _bullet_lines(
            macro_explanation_lines,
            "No macro term explanations available.",
        )
        + ("\n\n## VIX chart\n" + chart_section if chart_section else ""),
        "## Weekend context / what happened\n"
        + _context_lines(
            _as_list(web_context.get("weekend_context")),
            "No weekend context available.",
        ),
        "## What to watch this week\n"
        + _context_lines(
            _as_list(web_context.get("watchlist")),
            "No weekly watchlist available.",
        ),
        "## Risks / uncertainty\n"
        + _bullet_lines(
            _as_list(computed.get("key_risks")) + data_gaps,
            "No explicit risks were generated.",
        ),
        "## What would change my mind\n"
        + _bullet_lines(
            _as_list(computed.get("what_would_change_my_mind")),
            "No change-of-mind triggers were generated.",
        ),
        "## Sources\n" + ("\n".join(source_lines) if source_lines else "- No sources available."),
    ]

    return "\n\n".join(sections).strip() + "\n"
