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

## Current Behavior

- The app tolerates missing upstream APIs by surfacing explicit data gaps.
- `market-snapshot` and `macro-snapshot` may fail in the current environment; when macro fails, the app attempts fallback reads from `service-richness` endpoints such as `/api/external-data`.
- The report separates `Facts` from `Interpretation`.
- The report includes `What would change my mind` and a `Sources` section.

## Current Limits

- Report quality is usable but still needs refinement.
- Source references are section-level, not fully claim-level.
- Some external inputs are optional fallbacks rather than guaranteed dependencies.
