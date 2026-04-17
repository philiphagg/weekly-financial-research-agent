from __future__ import annotations

from collections import defaultdict
from typing import Any

from agent_lab.research_schemas import MomentumObservation, MomentumSummary
from agent_lab.momentum_configs import DEFAULT_MOMENTUM_REQUESTS


STRATEGY_TYPE_TO_MOMENTUM_TYPE = {
    "time_series_momentum": "time_series",
    "low_volatility": "low_volatility",
    "multi_factor": "multi_factor",
    "residual_momentum": "residual",
    "price_momentum": "price",
}

MOMENTUM_STRATEGY_EXPLANATIONS = {
    "time_series": "Time-series momentum looks for stocks already trending higher over a longer window and assumes trend persistence can continue.",
    "price": "Price momentum ranks stocks on medium-term relative performance and looks for sustained winners versus the rest of the universe.",
    "low_volatility": "Low-volatility momentum favors names with strong trend behavior but less violent price movement, which can indicate steadier leadership.",
    "multi_factor": "Multi-factor momentum blends momentum with volatility-aware ranking so the result is not driven by a single return measure alone.",
    "residual": "Residual momentum tries to isolate stock-specific strength after removing broad market or beta effects.",
}


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


def normalize_single_momentum_response(payload: dict[str, Any]) -> list[MomentumObservation]:
    assets = payload.get("assets", [])
    strategy_type = payload.get("strategyType", "")
    momentum_type = STRATEGY_TYPE_TO_MOMENTUM_TYPE.get(strategy_type)

    if not momentum_type:
        return []

    total_count = len(assets)
    observations: list[MomentumObservation] = []

    for idx, asset in enumerate(assets, start=1):
        score = _safe_float(asset.get("score"))
        if score is None:
            continue

        if score > 0:
            direction = "positive"
        elif score < 0:
            direction = "negative"
        else:
            direction = "neutral"

        # 1.0 = bäst rankad, 0.0 = sämst rankad
        rank_pct = None
        if total_count > 1:
            rank_pct = 1.0 - ((idx - 1) / (total_count - 1))
        elif total_count == 1:
            rank_pct = 1.0

        obs = MomentumObservation(
            ticker=str(asset.get("name", "UNKNOWN")),
            momentum_type=momentum_type,  # type: ignore[arg-type]
            score=score,
            direction=direction,  # type: ignore[arg-type]
            rank=idx,
            total_count=total_count,
            rank_pct=rank_pct,
            price=_safe_float(asset.get("price")),
            volatility=_safe_float(asset.get("volatility")),
            volume=_safe_int(asset.get("volume")),
            stock_data_id=asset.get("stockDataId"),
        )
        observations.append(obs)

    return observations


def normalize_all_momentum(momentum_raw: dict[str, Any]) -> list[MomentumObservation]:
    normalized: list[MomentumObservation] = []

    for _, payload in momentum_raw.items():
        if isinstance(payload, dict):
            normalized.extend(normalize_single_momentum_response(payload))

    return normalized


def build_momentum_screener_tables(momentum_raw: dict[str, Any], limit: int = 20) -> list[dict[str, Any]]:
    tables: list[dict[str, Any]] = []

    for key, payload in momentum_raw.items():
        if not isinstance(payload, dict):
            continue

        observations = normalize_single_momentum_response(payload)
        if not observations:
            continue

        strategy_cfg = DEFAULT_MOMENTUM_REQUESTS.get(key, {})
        title = strategy_cfg.get("title", f"{key} screener")
        description = MOMENTUM_STRATEGY_EXPLANATIONS.get(
            observations[0].momentum_type,
            "This screener ranks stocks using a momentum-style approach.",
        )

        leaders = sorted(
            observations,
            key=lambda obs: ((obs.rank or 10**9), -(obs.score or 0.0)),
        )[:limit]
        laggards = sorted(
            observations,
            key=lambda obs: ((obs.rank or 0)),
        )[-limit:]

        tables.append(
            {
                "screener_key": key,
                "title": title,
                "description": description,
                "leaders": [obs.model_dump() for obs in leaders],
                "laggards": [obs.model_dump() for obs in laggards],
                "count": len(observations),
            }
        )

    return tables


def summarize_momentum(observations: list[MomentumObservation]) -> MomentumSummary:
    if not observations:
        return MomentumSummary(
            interpretation="No momentum observations could be normalized.",
            data_gaps=["No normalized momentum observations available."],
        )

    grouped: dict[str, list[MomentumObservation]] = defaultdict(list)
    for obs in observations:
        grouped[obs.ticker].append(obs)

    leader_candidates: list[tuple[str, float, list[MomentumObservation]]] = []
    laggard_candidates: list[tuple[str, float, list[MomentumObservation]]] = []
    agreements: list[str] = []
    conflicts: list[str] = []

    for ticker, obs_list in grouped.items():
        positive = [o for o in obs_list if o.direction == "positive"]
        negative = [o for o in obs_list if o.direction == "negative"]

        avg_positive_rank_pct = (
            sum((o.rank_pct or 0.0) for o in positive) / len(positive)
            if positive else 0.0
        )
        avg_negative_rank_pct = (
            sum((1.0 - (o.rank_pct or 0.0)) for o in negative) / len(negative)
            if negative else 0.0
        )

        if len(positive) >= 2:
            leader_candidates.append((ticker, len(positive) + avg_positive_rank_pct, positive))
            agreements.append(
                f"{ticker}: positive agreement across {len(positive)} momentum signals"
            )

        if len(negative) >= 2:
            laggard_candidates.append((ticker, len(negative) + avg_negative_rank_pct, negative))
            agreements.append(
                f"{ticker}: negative agreement across {len(negative)} momentum signals"
            )

        if positive and negative:
            conflicts.append(
                f"{ticker}: conflict across momentum signals ({len(positive)} positive, {len(negative)} negative)"
            )

    leader_candidates.sort(key=lambda x: x[1], reverse=True)
    laggard_candidates.sort(key=lambda x: x[1], reverse=True)

    leaders: list[MomentumObservation] = []
    for _, _, pos_list in leader_candidates[:10]:
        best = sorted(pos_list, key=lambda o: ((o.rank_pct or 0.0), o.score), reverse=True)[0]
        leaders.append(best)

    laggards: list[MomentumObservation] = []
    for _, _, neg_list in laggard_candidates[:10]:
        worst = sorted(neg_list, key=lambda o: ((o.rank_pct or 0.0), o.score))[0]
        laggards.append(worst)

    if leaders and not conflicts:
        interpretation = (
            "Momentum signals show several clear leaders with relatively strong agreement "
            "across models."
        )
    elif leaders and conflicts:
        interpretation = (
            "Momentum signals show strong leaders, but there are also conflicts across "
            "different momentum definitions that should temper conviction."
        )
    else:
        interpretation = (
            "The momentum picture is weak or fragmented; interpretation should stay cautious."
        )

    return MomentumSummary(
        leaders=leaders,
        laggards=laggards,
        cross_signal_agreements=agreements[:15],
        cross_signal_conflicts=conflicts[:15],
        interpretation=interpretation,
        data_gaps=[],
    )
