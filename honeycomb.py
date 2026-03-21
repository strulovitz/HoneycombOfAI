#!/usr/bin/env python3
"""HoneycombOfAI — main entry point. Reads config.yaml and starts the chosen module."""

import argparse
import sys

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from beekeeper import BeekeeperModule
from queen_bee import QueenBeeModule
from worker_bee import WorkerBeeModule

console = Console()


def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def start_worker(config: dict) -> None:
    url = config["server"]["url"]
    model = config["model"]["name"]
    backend = config["model"]["backend"]

    console.print(Panel(
        Text("🐝  WorkerBee Module", style="bold yellow", justify="center"),
        border_style="yellow",
    ))
    console.print(f"[green]✔[/green]  WorkerBee Module started! Ready to process sub-tasks.")
    console.print(f"[cyan]→[/cyan]  Connecting to server at [bold]{url}[/bold]...")
    console.print(f"[cyan]→[/cyan]  Using AI model: [bold]{model}[/bold] via [bold]{backend}[/bold]")
    console.print(f"[yellow]⏳[/yellow] Waiting for tasks...")

    module = WorkerBeeModule(config)
    module.start()


def start_queen(config: dict) -> None:
    url = config["server"]["url"]
    model = config["model"]["name"]
    backend = config["model"]["backend"]

    console.print(Panel(
        Text("👑  QueenBee Module", style="bold magenta", justify="center"),
        border_style="magenta",
    ))
    console.print(f"[green]✔[/green]  QueenBee Module started! Ready to manage a Hive.")
    console.print(f"[cyan]→[/cyan]  Connecting to server at [bold]{url}[/bold]...")
    console.print(f"[cyan]→[/cyan]  Using AI model: [bold]{model}[/bold] via [bold]{backend}[/bold]")
    console.print(f"[yellow]⏳[/yellow] Waiting for Worker Bees to join the Hive...")

    module = QueenBeeModule(config)
    module.start()


def start_beekeeper(config: dict) -> None:
    url = config["server"]["url"]
    model = config["model"]["name"]
    backend = config["model"]["backend"]

    console.print(Panel(
        Text("🏢  Beekeeper Module", style="bold blue", justify="center"),
        border_style="blue",
    ))
    console.print(f"[green]✔[/green]  Beekeeper Module started! Ready to submit tasks.")
    console.print(f"[cyan]→[/cyan]  Connecting to server at [bold]{url}[/bold]...")
    console.print(f"[cyan]→[/cyan]  Using AI model: [bold]{model}[/bold] via [bold]{backend}[/bold]")
    console.print(f"[yellow]⏳[/yellow] Ready — use submit_task() to send your first Nectar.")

    module = BeekeeperModule(config)
    module.start()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="HoneycombOfAI — Distributed AI Computing Software"
    )
    parser.add_argument(
        "--mode",
        choices=["worker", "queen", "beekeeper"],
        help="Override the mode set in config.yaml",
    )
    args = parser.parse_args()

    config = load_config()
    mode = args.mode if args.mode else config.get("mode", "worker")

    console.print()
    console.print(f"[bold]🍯 HoneycombOfAI[/bold] — starting in [bold yellow]{mode}[/bold yellow] mode")
    console.print()

    if mode == "worker":
        start_worker(config)
    elif mode == "queen":
        start_queen(config)
    elif mode == "beekeeper":
        start_beekeeper(config)
    else:
        console.print(f"[red]Unknown mode: {mode}. Choose: worker, queen, beekeeper[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
