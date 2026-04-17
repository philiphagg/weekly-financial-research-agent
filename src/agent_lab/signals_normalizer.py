from __future__ import annotations

from collections import defaultdict
from typing import Any

from agent_lab.research_schemas import SignalObservation, SignalSummary


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _infer_direction(raw: dict[str, Any], value: float | None) -> str:
    candidates = [
        raw.get("direction"),
        raw.get("signalDirection"),
        raw.get("stance"),
        raw.get("bias"),
        raw.get("sentiment"),
        raw.get("side"),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        lowered = str(candidate).strip().lower()
        if lowered in {"bullish", "positive", "buy", "long", "up"}:
            return "bullish"
        if lowered in {"bearish", "negative", "sell", "short", "down"}:
            return "bearish"
        if lowered in {"neutral", "flat", "mixed"}:
            return "neutral"

    if value is None:
        return "neutral"
    if value > 0:
        return "bullish"
    if value < 0:
        return "bearish"
    return "neutral"


def _extract_signal_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("signals", "items", "results", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def normalize_signals(payload: dict[str, Any]) -> list[SignalObservation]:
    items = _extract_signal_items(payload)
    observations: list[SignalObservation] = []

    for item in items:
        ticker = (
            item.get("ticker")
            or item.get("symbol")
            or item.get("name")
            or item.get("identifier")
            or item.get("assetSymbol")
            or item.get("assetTicker")
        )
        if not ticker:
            continue

        signal_name = (
            item.get("signalName")
            or item.get("signalType")
            or item.get("signal")
            or item.get("strategy")
            or item.get("name")
            or "unknown_signal"
        )
        value = _safe_float(item.get("score"))
        if value is None:
            value = _safe_float(item.get("value"))
        if value is None:
            value = _safe_float(item.get("signalValue"))

        direction = _infer_direction(item, value)
        confidence = _safe_float(item.get("confidence"))
        if confidence is None:
            confidence = _safe_float(item.get("strength"))
        if confidence is None:
            confidence = _safe_float(item.get("convictionScore"))

        observations.append(
            SignalObservation(
                ticker=str(ticker),
                signal_name=str(signal_name),
                category=str(item.get("category") or item.get("type") or item.get("snapshotType") or "general"),
                value=value,
                direction=direction,  # type: ignore[arg-type]
                horizon=item.get("horizon") or item.get("timeframe"),
                confidence=confidence,
                notes=item.get("notes") or item.get("description") or item.get("reason"),
            )
        )

    return observations


def summarize_signals(
    observations: list[SignalObservation],
    momentum_summary: dict[str, Any] | None = None,
) -> SignalSummary:
    if not observations:
        return SignalSummary(
            interpretation="No usable signal observations could be normalized.",
            data_gaps=["No normalized signals available."],
        )

    bullish = [obs for obs in observations if obs.direction == "bullish"]
    bearish = [obs for obs in observations if obs.direction == "bearish"]
    neutral = [obs for obs in observations if obs.direction == "neutral"]

    momentum_summary = momentum_summary or {}
    leader_tickers = {
        item.get("ticker")
        for item in momentum_summary.get("leaders", [])
        if isinstance(item, dict) and item.get("ticker")
    }
    laggard_tickers = {
        item.get("ticker")
        for item in momentum_summary.get("laggards", [])
        if isinstance(item, dict) and item.get("ticker")
    }

    by_ticker: dict[str, list[SignalObservation]] = defaultdict(list)
    for obs in observations:
        by_ticker[obs.ticker].append(obs)

    support_for_momentum: list[str] = []
    contradictions_to_momentum: list[str] = []
    standalone_signal_highlights: list[str] = []

    for ticker, items in by_ticker.items():
        bullish_count = len([obs for obs in items if obs.direction == "bullish"])
        bearish_count = len([obs for obs in items if obs.direction == "bearish"])

        if ticker in leader_tickers and bullish_count > bearish_count:
            support_for_momentum.append(
                f"{ticker}: signals support the momentum leadership ({bullish_count} bullish, {bearish_count} bearish)"
            )
        if ticker in laggard_tickers and bearish_count > bullish_count:
            support_for_momentum.append(
                f"{ticker}: signals confirm momentum weakness ({bearish_count} bearish, {bullish_count} bullish)"
            )
        if ticker in leader_tickers and bearish_count > bullish_count:
            contradictions_to_momentum.append(
                f"{ticker}: signals contradict the momentum leadership ({bearish_count} bearish, {bullish_count} bullish)"
            )
        if ticker in laggard_tickers and bullish_count > bearish_count:
            contradictions_to_momentum.append(
                f"{ticker}: signals contradict the momentum weakness ({bullish_count} bullish, {bearish_count} bearish)"
            )
        if ticker not in leader_tickers and ticker not in laggard_tickers:
            if bullish_count >= 2:
                standalone_signal_highlights.append(
                    f"{ticker}: multiple bullish signals are active ({bullish_count})"
                )
            elif bearish_count >= 2:
                standalone_signal_highlights.append(
                    f"{ticker}: multiple bearish signals are active ({bearish_count})"
                )

    if bullish and bearish:
        interpretation = (
            "The signal block shows both confirming and conflicting indications; use it as a counterweight to pure price strength."
        )
    elif bullish:
        interpretation = "The signal block leans bullish and supports risk-on positioning where momentum also holds together."
    elif bearish:
        interpretation = "The signal block leans bearish and argues for greater caution despite isolated momentum winners."
    else:
        interpretation = "The signal block is mostly neutral and should be used primarily as supporting context."

    signal_table: list[dict[str, Any]] = []
    seen_signal_rows: set[tuple[str, str, str]] = set()
    for obs in sorted(
        observations,
        key=lambda obs: (
            -(obs.confidence or 0.0),
            obs.ticker,
            obs.signal_name,
        ),
    ):
        row_key = (obs.ticker, obs.signal_name, obs.direction)
        if row_key in seen_signal_rows:
            continue
        seen_signal_rows.add(row_key)
        signal_table.append(
            {
                "ticker": obs.ticker,
                "signal_name": obs.signal_name,
                "category": obs.category,
                "direction": obs.direction,
                "value": obs.value,
                "confidence": obs.confidence,
                "horizon": obs.horizon,
                "notes": obs.notes,
            }
        )
        if len(signal_table) >= 25:
            break

    return SignalSummary(
        bullish_signals=bullish[:10],
        bearish_signals=bearish[:10],
        neutral_signals=neutral[:10],
        signal_table=signal_table,
        support_for_momentum=(support_for_momentum + standalone_signal_highlights)[:10],
        contradictions_to_momentum=contradictions_to_momentum[:10],
        interpretation=interpretation,
        data_gaps=[],
    )
