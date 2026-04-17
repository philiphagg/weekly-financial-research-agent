# Weekly Stock Market Science Agent

CLI-based Python research workflow for generating a weekly stock market report.

The project is built around a deterministic LangGraph pipeline that:

- ingests market, macro, sector rotation, momentum, signal, and web context inputs
- normalizes momentum, sector rotation, and signals in Python
- builds a traceable research packet
- renders a weekly Markdown report
- persists debug outputs for inspection and regression testing

## Run

From the repo root:

```bash
PYTHONPATH=src python -m agent_lab.research_main
```

The canonical CLI module now lives at:

```bash
PYTHONPATH=src python -m agent_lab.cli.weekly_report
```

## Test

```bash
PYTHONPATH=src python -m pytest tests -q
```

## Main Outputs

Each run writes:

- `debug_output/full_state.json`
- `debug_output/final_packet.json`
- `debug_output/weekly_report.md`
- `debug_output/sources.json`
- `debug_output/source_summaries.json`
- `debug_output/run_metadata.json`
- `debug_output/vix_chart.svg`
- `debug_output/sector_rotation_scatter.svg`
- `debug_output/sector_rotation_grid.svg`

## Package Structure

The live weekly-report code is organized as:

- `src/agent_lab/cli/`
  CLI entrypoints
- `src/agent_lab/core/`
  runtime settings and shared core configuration
- `src/agent_lab/clients/`
  HTTP/API clients for market, macro, momentum, signals, sector rotation, regime, and web search
- `src/agent_lab/normalizers/`
  Python normalization logic for momentum, sector rotation, and signals
- `src/agent_lab/workflow/`
  LangGraph workflow and packet schemas
- `src/agent_lab/rendering/`
  report rendering and chart generation
- `src/agent_lab/output/`
  debug-output writing

`src/agent_lab/research_main.py` is kept as a compatibility wrapper around the CLI module.

## Removed Legacy Files

The following older prototype files were removed because they were not part of the working weekly-report path:

- root `main.py`
- `test_httpx.py`
- `src/agent_lab/main.py`
- `src/agent_lab/agent.py`
- `src/agent_lab/llm.py`
- `src/agent_lab/tools/python_exec.py`

## Current Behavior

- The app tolerates missing upstream APIs by surfacing explicit data gaps.
- `market-snapshot` and `macro-snapshot` may fail in the current environment; when macro fails, the app attempts fallback reads from `service-richness` endpoints such as `/api/external-data`.
- The report separates `Facts` from `Interpretation`.
- The report includes `What would change my mind` and a `Sources` section.

## Current Limits

- Report quality is usable but still needs refinement.
- Source references are section-level, not fully claim-level.
- Some external inputs are optional fallbacks rather than guaranteed dependencies.
