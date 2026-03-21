"""
honeycomb.py — Main Entry Point for HoneycombOfAI
==================================================
Beehive Of AI — Personal Computers Working Together as One Powerful AI

This is the main script that starts the HoneycombOfAI software.
It reads the config file and starts the appropriate module:
  - Worker Bee mode: processes AI sub-tasks
  - Queen Bee mode: manages a Hive of workers
  - Beekeeper mode: submits tasks and receives results

Usage:
  python honeycomb.py                  (uses mode from config.yaml)
  python honeycomb.py --mode worker    (override: start as Worker Bee)
  python honeycomb.py --mode queen     (override: start as Queen Bee)
  python honeycomb.py --mode beekeeper (override: start as Beekeeper)
"""

import argparse
import yaml
import sys
from rich.console import Console
from rich.panel import Panel

from ollama_client import OllamaClient
from worker_bee import WorkerBee
from queen_bee import QueenBee
from beekeeper import Beekeeper

console = Console()


def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        console.print(f"[red]❌ Config file not found: {config_path}[/]")
        console.print("Please make sure config.yaml exists in the current directory.")
        sys.exit(1)


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="HoneycombOfAI — The Distributed AI Software"
    )
    parser.add_argument(
        "--mode",
        choices=["worker", "queen", "beekeeper"],
        help="Which mode to run (overrides config.yaml)"
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config file (default: config.yaml)"
    )
    args = parser.parse_args()

    # Load config
    config = load_config(args.config)

    # Determine mode
    mode = args.mode or config.get("mode", "worker")

    # Show startup banner
    console.print(Panel(
        "[bold yellow]🍯 HoneycombOfAI[/]\n"
        "[italic]The Distributed AI Software[/]\n\n"
        f"Mode: [bold]{mode.upper()}[/]\n"
        f"Server: {config['server']['url']}",
        title="Honeycomb Of AI",
        border_style="yellow"
    ))

    # Check Ollama connection
    ai = OllamaClient(config["model"]["base_url"])
    if not ai.is_available():
        console.print("[bold red]❌ Cannot connect to Ollama![/]")
        console.print("Make sure Ollama is running: http://localhost:11434")
        sys.exit(1)
    console.print("[green]✅ Connected to Ollama[/]")

    # Start the appropriate module
    if mode == "worker":
        worker = WorkerBee(
            worker_id=config["worker"]["worker_id"],
            model_name=config["model"]["worker_model"],
            ollama_url=config["model"]["base_url"],
            temperature=config["model"]["temperature"]
        )
        worker.start()
        console.print("\n[yellow]Worker Bee is waiting for tasks...[/]")
        console.print("[dim]In the full system, tasks would arrive from the Queen Bee over the network.[/]")
        console.print("[dim]Press Ctrl+C to stop.[/]")
        try:
            while True:
                pass
        except KeyboardInterrupt:
            console.print("\n[yellow]Worker Bee stopped.[/]")

    elif mode == "queen":
        queen = QueenBee(
            model_name=config["model"]["queen_model"],
            ollama_url=config["model"]["base_url"],
            temperature=config["model"]["temperature"]
        )
        queen.start()
        console.print("\n[magenta]Queen Bee is waiting for Nectar...[/]")
        console.print("[dim]Press Ctrl+C to stop.[/]")
        try:
            while True:
                pass
        except KeyboardInterrupt:
            console.print("\n[magenta]Queen Bee stopped.[/]")

    elif mode == "beekeeper":
        bk = Beekeeper(company_name="My Company")
        bk.start()
        console.print("\n[blue]Beekeeper module ready.[/]")
        console.print("[dim]In the full system, you would submit tasks through the website.[/]")


if __name__ == "__main__":
    main()
