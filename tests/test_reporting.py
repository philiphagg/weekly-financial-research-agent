from agent_lab.rendering.report import render_weekly_report


def test_weekly_report_contains_required_sections() -> None:
    packet = {
        "week_label": "2026-W16",
        "market_summary": {
            "market_regime": "Constructive but selective",
            "breadth_comment": "Breadth is mixed.",
            "price_action_comment": "Index trend remains intact.",
            "source_ids": ["market_snapshot"],
        },
        "macro_summary": {
            "macro_regime": "Macro is stable.",
            "credit_comment": "Credit remains orderly.",
            "risk_comment": "Macro data is incomplete.",
            "source_ids": ["macro_snapshot"],
        },
        "sector_rotation_summary": {
            "leading_sectors": ["Technology"],
            "lagging_sectors": ["Utilities"],
            "rotation_table": [
                {
                    "name": "Technology",
                    "quadrant": "leading",
                    "week_anchor_return": 0.04,
                    "one_week_return": 0.03,
                    "two_week_return": 0.06,
                    "rotation_score": 0.041,
                }
            ],
            "positioning_comment": "Lean toward relative strength.",
            "source_ids": ["sector_rotation"],
        },
        "momentum_summary": {
            "leaders": [{"ticker": "NVDA"}],
            "laggards": [{"ticker": "TLT"}],
            "interpretation": "Momentum leadership remains narrow.",
            "source_ids": ["momentum_price"],
        },
        "signal_summary": {
            "support_for_momentum": ["NVDA: signals support the momentum leadership"],
            "contradictions_to_momentum": [],
            "interpretation": "Signals are supportive.",
            "source_ids": ["signals_api"],
        },
        "web_context_summary": {
            "weekend_context": [{"headline": "Tariff headlines", "summary": "Macro noise remains elevated.", "source_id": "web_weekend_context_1"}],
            "watchlist": [{"headline": "Earnings week ahead", "summary": "Mega-cap earnings dominate.", "source_id": "web_what_to_watch_1"}],
            "source_ids": ["web_weekend_context_1", "web_what_to_watch_1"],
        },
        "computed_analysis": {
            "base_case": "Stay constructive but avoid broad chasing.",
            "key_risks": ["Credit spreads widen"],
            "what_would_change_my_mind": ["Breadth deteriorates materially"],
            "source_ids": ["market_snapshot", "signals_api"],
        },
        "sources": [{"source_id": "market_snapshot", "title": "Market snapshot", "source_type": "market_api", "summary": "Market API snapshot.", "url": "https://example.com"}],
        "data_gaps": ["Macro snapshot unavailable"],
    }

    report = render_weekly_report(packet)

    assert "## Executive summary" in report
    assert "## Facts" in report
    assert "## Interpretation" in report
    assert "## What would change my mind" in report
    assert "## Sources" in report
    assert "Sector rotation scatter" in report
    assert "Sector rotation category grid" in report
    assert "### Sector rotation table" in report


def test_weekly_report_surfaces_data_gaps() -> None:
    report = render_weekly_report(
        {
            "week_label": "2026-W16",
            "market_summary": {},
            "macro_summary": {},
            "sector_rotation_summary": {},
            "momentum_summary": {},
            "signal_summary": {},
            "web_context_summary": {},
            "computed_analysis": {"key_risks": [], "what_would_change_my_mind": []},
            "sources": [],
            "data_gaps": ["Macro snapshot unavailable: 404"],
        }
    )

    assert "Macro snapshot unavailable: 404" in report
