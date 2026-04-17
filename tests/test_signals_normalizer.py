from agent_lab.signals_normalizer import normalize_signals, summarize_signals


def test_normalize_signals_from_service_richness_shape() -> None:
    payload = {
        "signals": [
            {
                "identifier": "NVDA",
                "signalType": "BREAKOUT",
                "side": "LONG",
                "reason": "Strong breakout with volume support",
                "convictionScore": 0.91,
                "snapshotType": "FiftyTwoWeekHighSnapshot",
            },
            {
                "identifier": "TSLA",
                "signalType": "MEAN_REVERSION",
                "side": "SHORT",
                "reason": "Weak follow-through",
                "convictionScore": 0.44,
                "snapshotType": "MeanReversionSnapshot",
            },
        ],
        "totalCount": 2,
    }

    observations = normalize_signals(payload)

    assert len(observations) == 2
    assert observations[0].ticker == "NVDA"
    assert observations[0].direction == "bullish"
    assert observations[1].ticker == "TSLA"
    assert observations[1].direction == "bearish"


def test_normalize_signals_prefers_name_over_numeric_identifier() -> None:
    payload = {
        "signals": [
            {
                "identifier": "5536",
                "name": "Lagercrantz Group AB ser B",
                "signalType": "HUNDRED_DAY_HIGH",
                "side": "BUY",
            }
        ]
    }

    observations = normalize_signals(payload)

    assert observations[0].ticker == "Lagercrantz Group AB ser B"


def test_signal_summary_detects_support_and_contradiction() -> None:
    payload = {
        "signals": [
            {"identifier": "NVDA", "signalType": "BREAKOUT", "side": "LONG"},
            {"identifier": "NVDA", "signalType": "TREND", "side": "LONG"},
            {"identifier": "TSLA", "signalType": "MEAN_REVERSION", "side": "LONG"},
            {"identifier": "TSLA", "signalType": "PULLBACK", "side": "LONG"},
        ]
    }
    observations = normalize_signals(payload)
    summary = summarize_signals(
        observations,
        momentum_summary={
            "leaders": [{"ticker": "NVDA"}],
            "laggards": [{"ticker": "TSLA"}],
        },
    )

    assert any("NVDA" in item for item in summary.support_for_momentum)
    assert any("TSLA" in item for item in summary.contradictions_to_momentum)
