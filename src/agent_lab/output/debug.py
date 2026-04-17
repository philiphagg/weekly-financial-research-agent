from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_lab.rendering.charts import (
    write_line_chart_svg,
    write_sector_rotation_grid_svg,
    write_sector_rotation_scatter_svg,
)


def write_debug_outputs(
    state: dict[str, Any],
    debug_dir: str = "debug_output",
) -> dict[str, str]:
    output_dir = Path(debug_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    full_state_path = output_dir / "full_state.json"
    final_packet_path = output_dir / "final_packet.json"
    weekly_report_path = output_dir / "weekly_report.md"
    sources_path = output_dir / "sources.json"
    source_summaries_path = output_dir / "source_summaries.json"
    run_metadata_path = output_dir / "run_metadata.json"
    vix_chart_path = output_dir / "vix_chart.svg"
    sector_rotation_scatter_path = output_dir / "sector_rotation_scatter.svg"
    sector_rotation_grid_path = output_dir / "sector_rotation_grid.svg"

    full_state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    final_packet_path.write_text(
        json.dumps(state.get("final_packet", {}), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    weekly_report_path.write_text(state.get("weekly_report", ""), encoding="utf-8")
    sources_path.write_text(
        json.dumps(state.get("sources", []), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    source_summaries_path.write_text(
        json.dumps(state.get("source_summaries", []), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    run_metadata_path.write_text(
        json.dumps(state.get("run_metadata", {}), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    macro_raw = state.get("macro_raw", {})
    external_series = macro_raw.get("external_series", {}) if isinstance(macro_raw, dict) else {}
    vix_chart_written = write_line_chart_svg(
        external_series.get("VIX", []),
        str(vix_chart_path),
        title="VIX - recent fallback series",
        line_color="#b91c1c",
    )
    sector_observations = state.get("normalized_sector_rotation", [])
    sector_scatter_written = write_sector_rotation_scatter_svg(
        sector_observations,
        str(sector_rotation_scatter_path),
        title="Sector rotation scatter",
    )
    sector_grid_written = write_sector_rotation_grid_svg(
        sector_observations,
        str(sector_rotation_grid_path),
        title="Sector rotation category grid",
    )

    return {
        "full_state": str(full_state_path),
        "final_packet": str(final_packet_path),
        "weekly_report": str(weekly_report_path),
        "sources": str(sources_path),
        "source_summaries": str(source_summaries_path),
        "run_metadata": str(run_metadata_path),
        "vix_chart": vix_chart_written or str(vix_chart_path),
        "sector_rotation_scatter": sector_scatter_written or str(sector_rotation_scatter_path),
        "sector_rotation_grid": sector_grid_written or str(sector_rotation_grid_path),
    }
