"""
demo_real.py — Real Demonstration of Beehive Of AI
===================================================
This demo shows the ACTUAL system working with a real AI model.
It creates one Queen Bee and three Worker Bees, all on the same machine,
and processes a real task through the complete pipeline.

Requirements:
- At least one AI backend must be running (Ollama, LM Studio, or llama.cpp)
- Set the backend in config.yaml under model.backend
"""

import sys
import time
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich import print as rprint

from backend_factory import create_backend
from backend_detector import detect_backends, display_detected_backends
from queen_bee import QueenBee
from worker_bee import WorkerBee
from beekeeper import Beekeeper

console = Console()


def check_ai_backend(config):
    """Verify the configured AI backend is available."""
    console.print(Rule("Checking AI Engine"))

    detected = detect_backends()
    display_detected_backends(detected, current_backend=config["model"].get("backend"))

    try:
        ai = create_backend(config)
    except ValueError as e:
        console.print(f"[bold red]❌ Error: {e}[/]")
        return None

    if not ai.is_available():
        console.print(f"[bold red]❌ Cannot connect to {ai.backend_name()}![/]")
        console.print(f"Make sure {ai.backend_name()} is running, then try again.")
        return None

    console.print(f"[green]✅ Connected to {ai.backend_name()}[/]")
    models = ai.list_models()
    if models:
        console.print(f"[green]✅ Available models: {', '.join(models[:5])}[/]")
    return ai


def run_demo():
    """Run the complete Beehive Of AI demonstration."""

    console.print(Panel(
        "[bold yellow]🐝 BEEHIVE OF AI — REAL DEMO[/]\n\n"
        "[italic]Personal Computers Working Together as One Powerful AI[/]\n\n"
        "This demo creates 1 Queen Bee + 3 Worker Bees on this machine.\n"
        "A Beekeeper (company) submits a task, and the Hive processes it\n"
        "using actual AI.",
        title="🐝 Welcome to the Hive",
        border_style="bold yellow",
        padding=(1, 2)
    ))

    time.sleep(1)

    # Load config
    try:
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        config = {"model": {"backend": "ollama", "worker_model": "llama3.2:3b",
                            "queen_model": "llama3.2:3b", "temperature": 0.7}}

    # Check AI backend
    ai = check_ai_backend(config)
    if ai is None:
        sys.exit(1)

    time.sleep(0.5)

    # === SETUP THE HIVE ===
    console.print(Rule("Setting Up the Hive"))

    # Create the Queen Bee (manager)
    queen = QueenBee(
        model_name=config["model"]["queen_model"],
        temperature=config["model"].get("temperature", 0.5),
        ai_backend=ai,
    )
    queen.start()

    time.sleep(0.5)

    # Create 3 Worker Bees
    for i in range(1, 4):
        worker = WorkerBee(
            worker_id=f"bee-{i:03d}",
            model_name=config["model"]["worker_model"],
            temperature=config["model"].get("temperature", 0.7),
            ai_backend=ai,
        )
        worker.start()
        queen.add_worker(worker)
        time.sleep(0.3)

    # Create the Beekeeper (company/customer)
    beekeeper = Beekeeper(company_name="Demo Corp")
    beekeeper.start()

    time.sleep(1)

    # === THE TASK ===
    console.print(Rule("The Task"))

    # This is the Nectar — the task that the Beekeeper wants done
    nectar = (
        "Write a comprehensive analysis of the benefits of renewable energy. "
        "Cover three aspects: environmental benefits, economic benefits, "
        "and technological advancements. For each aspect, provide specific "
        "examples and recent developments."
    )

    # Beekeeper submits the task
    beekeeper.submit_nectar(nectar)

    time.sleep(1)

    # === PROCESS THE TASK ===
    console.print(Rule("Processing — Watch the Bees Work!"))

    # Queen Bee handles everything: split → assign → process → combine
    honey = queen.process_nectar(nectar)

    # === DELIVER THE RESULT ===
    console.print(Rule("Delivery"))

    # Beekeeper receives the final answer
    beekeeper.receive_honey(honey)

    # === SUMMARY ===
    console.print()
    console.print(Panel(
        "[bold green]✅ Demo Complete![/]\n\n"
        "What just happened:\n"
        "1. 🏢 The Beekeeper submitted a Nectar (task)\n"
        "2. 👑 The Queen Bee split it into 3 Sub-tasks using AI\n"
        "3. 🐝 Three Worker Bees processed sub-tasks IN PARALLEL using AI\n"
        "4. 👑 The Queen Bee combined all results into Honey using AI\n"
        "5. 🍯 The Honey (final answer) was delivered to the Beekeeper\n\n"
        "[italic]In the full system, each Worker Bee would be on a different\n"
        "person's home computer, connected over the internet![/]",
        title="🐝 Demo Summary",
        border_style="bold green",
        padding=(1, 2)
    ))


if __name__ == "__main__":
    run_demo()
