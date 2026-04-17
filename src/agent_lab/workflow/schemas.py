from __future__ import annotations

from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field


class SourceRef(BaseModel):
    source_id: str
    source_type: Literal[
        "market_api",
        "macro_api",
        "sector_rotation_api",
        "momentum_api",
        "signals_api",
        "python_analysis",
        "web",
    ]
    title: str
    url: str | None = None
    timestamp_utc: str | None = None
    summary: str | None = None


class SourceSummary(BaseModel):
    source_id: str
    title: str
    source_type: str
    summary: str
    url: str | None = None


class SignalObservation(BaseModel):
    ticker: str
    signal_name: str
    category: str = "general"
    value: float | None = None
    direction: Literal["bullish", "bearish", "neutral"] = "neutral"
    horizon: str | None = None
    confidence: float | None = None
    notes: str | None = None


class SignalSummary(BaseModel):
    bullish_signals: list[SignalObservation] = Field(default_factory=list)
    bearish_signals: list[SignalObservation] = Field(default_factory=list)
    neutral_signals: list[SignalObservation] = Field(default_factory=list)
    signal_table: list[dict[str, Any]] = Field(default_factory=list)
    support_for_momentum: list[str] = Field(default_factory=list)
    contradictions_to_momentum: list[str] = Field(default_factory=list)
    interpretation: str = ""
    data_gaps: list[str] = Field(default_factory=list)


class WebContextItem(BaseModel):
    headline: str
    summary: str
    url: str | None = None
    source_id: str | None = None


class WebContextSummary(BaseModel):
    weekend_context: list[WebContextItem] = Field(default_factory=list)
    watchlist: list[WebContextItem] = Field(default_factory=list)
    overview: str = ""
    data_gaps: list[str] = Field(default_factory=list)


class MomentumObservation(BaseModel):
    ticker: str
    momentum_type: Literal[
        "time_series",
        "price",
        "low_volatility",
        "multi_factor",
        "residual",
    ]
    score: float
    direction: Literal["positive", "negative", "neutral"]
    rank: int | None = None
    total_count: int | None = None
    rank_pct: float | None = None
    horizon_days: int | None = None
    confidence: float | None = None
    notes: str | None = None
    price: float | None = None
    volatility: float | None = None
    volume: int | None = None
    stock_data_id: str | None = None


class MomentumSummary(BaseModel):
    leaders: list[MomentumObservation] = Field(default_factory=list)
    laggards: list[MomentumObservation] = Field(default_factory=list)
    cross_signal_agreements: list[str] = Field(default_factory=list)
    cross_signal_conflicts: list[str] = Field(default_factory=list)
    interpretation: str = ""
    data_gaps: list[str] = Field(default_factory=list)


class ResearchPacket(BaseModel):
    week_label: str
    run_metadata: dict[str, Any] = Field(default_factory=dict)
    market_summary: dict[str, Any]
    macro_summary: dict[str, Any]
    sector_rotation_summary: dict[str, Any]
    momentum_summary: dict[str, Any]
    signal_summary: dict[str, Any]
    web_context_summary: dict[str, Any]
    computed_analysis: dict[str, Any]
    sources: list[SourceRef]
    source_summaries: list[SourceSummary] = Field(default_factory=list)
    data_gaps: list[str]


class ResearchState(TypedDict, total=False):
    week_label: str
    run_metadata: dict[str, Any]
    market_raw: dict[str, Any]
    macro_raw: dict[str, Any]
    sector_rotation_raw: dict[str, Any]
    normalized_sector_rotation: list[dict[str, Any]]
    momentum_raw: dict[str, Any]
    normalized_momentum: list[dict[str, Any]]
    signals_raw: dict[str, Any]
    normalized_signals: list[dict[str, Any]]
    web_search_raw: dict[str, Any]
    market_summary: dict[str, Any]
    macro_summary: dict[str, Any]
    sector_rotation_summary: dict[str, Any]
    momentum_summary: dict[str, Any]
    signal_summary: dict[str, Any]
    web_context_summary: dict[str, Any]
    computed_analysis: dict[str, Any]
    sources: list[dict[str, Any]]
    source_summaries: list[dict[str, Any]]
    data_gaps: list[str]
    final_packet: dict[str, Any]
    weekly_report: str
