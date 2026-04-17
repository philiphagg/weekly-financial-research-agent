from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SectorRotationObservation(BaseModel):
    instrument_id: str
    name: str
    symbol: str | None = None
    date: str | None = None
    week_anchor_return: float | None = None
    one_week_return: float | None = None
    two_week_return: float | None = None
    rotation_score: float | None = None
    direction: str = "neutral"
    quadrant: str = "unclassified"


class SectorRotationSummary(BaseModel):
    leading_sectors: list[str] = Field(default_factory=list)
    lagging_sectors: list[str] = Field(default_factory=list)
    leading_observations: list[dict[str, Any]] = Field(default_factory=list)
    lagging_observations: list[dict[str, Any]] = Field(default_factory=list)
    improving_observations: list[dict[str, Any]] = Field(default_factory=list)
    weakening_observations: list[dict[str, Any]] = Field(default_factory=list)
    all_observations: list[dict[str, Any]] = Field(default_factory=list)
    rotation_table: list[dict[str, Any]] = Field(default_factory=list)
    positioning_comment: str = ""
    data_gaps: list[str] = Field(default_factory=list)


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _latest_valid_snapshot(daily_snapshots: list[dict[str, Any]]) -> dict[str, Any] | None:
    valid = []
    for snap in daily_snapshots:
        wa = _safe_float(snap.get("weekAnchorReturn"))
        ow = _safe_float(snap.get("oneWeekReturn"))
        tw = _safe_float(snap.get("twoWeekReturn"))
        if wa is not None or ow is not None or tw is not None:
            valid.append(snap)

    if not valid:
        return None

    # antar att listan redan är i datumordning, tar senaste
    return valid[-1]


def _rotation_score(snapshot: dict[str, Any]) -> float | None:
    wa = _safe_float(snapshot.get("weekAnchorReturn"))
    ow = _safe_float(snapshot.get("oneWeekReturn"))
    tw = _safe_float(snapshot.get("twoWeekReturn"))

    if wa is None and ow is None and tw is None:
        return None

    wa = 0.0 if wa is None else wa
    ow = 0.0 if ow is None else ow
    tw = 0.0 if tw is None else tw

    return 0.5 * wa + 0.3 * ow + 0.2 * tw


def _quadrant(week_anchor_return: float | None, one_week_return: float | None) -> str:
    if week_anchor_return is None or one_week_return is None:
        return "unclassified"
    if week_anchor_return >= 0 and one_week_return >= 0:
        return "leading"
    if week_anchor_return >= 0 and one_week_return < 0:
        return "weakening"
    if week_anchor_return < 0 and one_week_return >= 0:
        return "improving"
    return "lagging"


def normalize_sector_rotation(raw: dict[str, Any]) -> list[SectorRotationObservation]:
    instruments = raw.get("instruments", [])
    normalized: list[SectorRotationObservation] = []

    for inst in instruments:
        latest = _latest_valid_snapshot(inst.get("dailySnapshots", []))
        if latest is None:
            continue

        score = _rotation_score(latest)
        if score is None:
            continue

        if score > 0:
            direction = "leading"
        elif score < 0:
            direction = "lagging"
        else:
            direction = "neutral"

        week_anchor_return = _safe_float(latest.get("weekAnchorReturn"))
        one_week_return = _safe_float(latest.get("oneWeekReturn"))
        two_week_return = _safe_float(latest.get("twoWeekReturn"))

        normalized.append(
            SectorRotationObservation(
                instrument_id=str(inst.get("id")),
                name=str(inst.get("name", "UNKNOWN")),
                symbol=inst.get("symbol"),
                date=latest.get("date"),
                week_anchor_return=week_anchor_return,
                one_week_return=one_week_return,
                two_week_return=two_week_return,
                rotation_score=score,
                direction=direction,
                quadrant=_quadrant(week_anchor_return, one_week_return),
            )
        )

    return normalized


def summarize_sector_rotation(observations: list[SectorRotationObservation]) -> SectorRotationSummary:
    if not observations:
        return SectorRotationSummary(
            positioning_comment="No usable sector rotation data could be normalized.",
            data_gaps=["No sector rotation observations available."],
        )

    sorted_obs = sorted(
        [o for o in observations if o.rotation_score is not None],
        key=lambda x: x.rotation_score if x.rotation_score is not None else 0.0,
        reverse=True,
    )

    leaders = sorted_obs[:8]
    laggards = sorted_obs[-8:]
    improving = [
        o for o in sorted_obs
        if o.quadrant == "improving"
    ][:8]
    weakening = [
        o for o in sorted_obs
        if o.quadrant == "weakening"
    ][:8]

    leading_names = [o.name for o in leaders]
    lagging_names = [o.name for o in laggards]

    rotation_table = [
        {
            "name": observation.name,
            "quadrant": observation.quadrant,
            "week_anchor_return": observation.week_anchor_return,
            "one_week_return": observation.one_week_return,
            "two_week_return": observation.two_week_return,
            "rotation_score": observation.rotation_score,
        }
        for observation in sorted_obs[:24]
    ]

    positioning_comment = (
        "Favor areas showing strong relative weekly leadership and positive short-term trend, "
        "and stay cautious with themes or instruments showing negative week-anchor returns and weak 1-2 week follow-through."
    )

    return SectorRotationSummary(
        leading_sectors=leading_names,
        lagging_sectors=lagging_names,
        leading_observations=[o.model_dump() for o in leaders],
        lagging_observations=[o.model_dump() for o in laggards],
        improving_observations=[o.model_dump() for o in improving],
        weakening_observations=[o.model_dump() for o in weakening],
        all_observations=[o.model_dump() for o in sorted_obs],
        rotation_table=rotation_table,
        positioning_comment=positioning_comment,
        data_gaps=[],
    )
