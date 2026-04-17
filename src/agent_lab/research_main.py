from __future__ import annotations

import json

from rich.console import Console
from rich.panel import Panel

from agent_lab.config import Settings
from agent_lab.debug_io import write_debug_outputs
from agent_lab.research_graph import build_research_graph, initial_state

console = Console()


def main() -> None:
    settings = Settings.load()

    console.print(Panel.fit("Weekly Stock Market Science Agent"))
    console.print(f"[yellow]MARKET_API_BASE_URL = {settings.market_api_base_url}[/yellow]")
    console.print(f"[yellow]MACRO_API_BASE_URL = {settings.macro_api_base_url}[/yellow]")
    console.print(f"[yellow]SECTOR_ROTATION_API_BASE_URL = {settings.sector_rotation_api_base_url}[/yellow]")
    console.print(f"[yellow]MOMENTUM_API_BASE_URL = {settings.momentum_api_base_url}[/yellow]")
    console.print(f"[yellow]SIGNALS_API_BASE_URL = {settings.signals_api_base_url}[/yellow]")

    graph = build_research_graph(settings)
    result = graph.invoke(initial_state())
    debug_paths = write_debug_outputs(result)

    final_packet = result.get("final_packet", {})
    weekly_report = result.get("weekly_report", "")

    console.print("\n[bold green]Weekly Report:[/bold green]")
    console.print(weekly_report)

    console.print("\n[bold green]Research Packet:[/bold green]")
    console.print(json.dumps(final_packet, ensure_ascii=False, indent=2))

    console.print("\n[bold cyan]Debug output files:[/bold cyan]")
    for label, path in debug_paths.items():
        console.print(f"- {label}: {path}")


if __name__ == "__main__":
    main()
