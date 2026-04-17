from __future__ import annotations

from rich.console import Console
from rich.panel import Panel

from agent_lab.agent import build_agent
from agent_lab.config import Settings

console = Console()


def main() -> None:
    settings = Settings.load()
    agent = build_agent(settings)

    console.print(Panel.fit("Portfolio Research Agent - tools v1"))
    console.print(f"[yellow]SIGNALS_API_BASE_URL = {settings.signals_api_base_url}[/yellow]")

    while True:
        user_input = console.input("\n[bold cyan]Prompt[/bold cyan] (eller 'exit'): ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break

        result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": user_input,
                    }
                ]
            }
        )

        structured = result.get("structured_response")
        if structured is not None:
            console.print("\n[bold green]Strukturerat svar:[/bold green]")
            console.print(structured.model_dump_json(indent=2))
        else:
            console.print("\n[bold yellow]Rått svar:[/bold yellow]")
            console.print(result)


if __name__ == "__main__":
    main()