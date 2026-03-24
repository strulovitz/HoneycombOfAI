"""
demo_website.py — Phase 4 Integration Demo
===========================================
This script connects the HoneycombOfAI desktop software to the
BeehiveOfAI website. Jobs submitted on the website get processed
automatically by real AI and the results appear on the website.

BEFORE RUNNING:
  1. Start your AI backend (Ollama, LM Studio, or llama.cpp)
  2. Set backend in config.yaml under model.backend
  3. Start website:  cd ../BeehiveOfAI && python app.py
  4. Run this:       python demo_website.py

THEN:
  - Open http://localhost:5000 in your browser
  - Login as company1@test.com / test123
  - Browse Hives → click DeepSeek Reasoning Hive
  - Click "Submit a Job"
  - Type any question or task
  - Watch this terminal process it in real time!
  - Refresh the job page on the website to see progress
"""

import sys
import time
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from backend_factory import create_backend
from backend_detector import detect_backends, display_detected_backends
from queen_bee import QueenBee
from worker_bee import WorkerBee
from api_client import BeehiveAPIClient

console = Console()

WEBSITE_URL = "http://localhost:5000"
QUEEN_EMAIL = "queen1@test.com"
QUEEN_PASSWORD = "test123"
HIVE_ID = 1
NUM_WORKERS = 2
POLL_INTERVAL = 8  # seconds between checking for new jobs


def check_website(api: BeehiveAPIClient) -> bool:
    """Verify the BeehiveOfAI website is running."""
    if not api.check_connection():
        console.print(f"[bold red]❌ Cannot connect to BeehiveOfAI at {WEBSITE_URL}[/]")
        console.print("   Start it with: [bold]cd ../BeehiveOfAI && python app.py[/]")
        return False
    console.print(f"[green]✅ BeehiveOfAI website is running at {WEBSITE_URL}[/]")
    return True


def main():
    console.print(Panel(
        "[bold yellow]🍯 HoneycombOfAI — Website Integration Demo[/]\n"
        "[italic]Phase 4: Connecting desktop software to the website[/]",
        border_style="yellow"
    ))

    # Load config
    try:
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        config = {"model": {"backend": "ollama", "worker_model": "llama3.2:3b",
                            "queen_model": "llama3.2:3b", "temperature": 0.7}}

    # Step 1: Check prerequisites
    console.print(Rule("[bold]Checking Prerequisites[/]"))
    api = BeehiveAPIClient(WEBSITE_URL)

    if not check_website(api):
        sys.exit(1)

    # Check AI backend
    console.print(Rule("[bold]Checking AI Backend[/]"))
    detected = detect_backends()
    display_detected_backends(detected, current_backend=config["model"].get("backend"))

    try:
        ai = create_backend(config)
    except ValueError as e:
        console.print(f"[bold red]❌ Error: {e}[/]")
        sys.exit(1)

    if not ai.is_available():
        console.print(f"[bold red]❌ Cannot connect to {ai.backend_name()}![/]")
        sys.exit(1)

    console.print(f"[green]✅ Connected to {ai.backend_name()}[/]")

    # Step 2: Login to the website
    console.print(Rule("[bold]Connecting to BeehiveOfAI[/]"))
    try:
        user_info = api.login(QUEEN_EMAIL, QUEEN_PASSWORD)
        console.print(f"[green]✅ Logged in as [bold]{user_info['username']}[/] (role: {user_info['role']})[/]")
    except Exception as e:
        console.print(f"[bold red]❌ Login failed: {e}[/]")
        sys.exit(1)

    # Step 3: Create the Queen Bee with Worker Bees
    console.print(Rule("[bold]Starting the Hive[/]"))
    model_name = config["model"]["queen_model"]
    temperature = config["model"].get("temperature", 0.5)

    queen = QueenBee(model_name=model_name, temperature=temperature, ai_backend=ai)

    for i in range(NUM_WORKERS):
        worker = WorkerBee(
            worker_id=f"worker-{i+1:03d}",
            model_name=config["model"]["worker_model"],
            temperature=config["model"].get("temperature", 0.7),
            ai_backend=ai,
        )
        queen.add_worker(worker)

    if not queen.start():
        console.print(f"[bold red]❌ Queen Bee could not start. Check {ai.backend_name()} connection.[/]")
        sys.exit(1)

    # Step 4: Instructions for the user
    console.print(Panel(
        f"[bold green]🐝 The Hive is running![/]\n\n"
        f"Now go to your browser and:\n"
        f"  1. Open [bold]{WEBSITE_URL}[/]\n"
        f"  2. Login as [bold]company1@test.com[/] / [bold]test123[/]\n"
        f"  3. Click [bold]Browse Hives[/]\n"
        f"  4. Click [bold]DeepSeek Reasoning Hive[/]\n"
        f"  5. Click [bold]Submit a Job[/]\n"
        f"  6. Type any task or question and submit\n\n"
        f"[italic]The Queen Bee will pick it up within {POLL_INTERVAL} seconds\n"
        f"and process it with {ai.backend_name()}. You can watch the progress\n"
        f"on the job status page (refresh the page to update).[/]\n\n"
        f"Press [bold]Ctrl+C[/] to stop.",
        title="Instructions",
        border_style="green"
    ))

    # Step 5: Start polling
    queen.process_from_website(api, HIVE_ID, poll_interval=POLL_INTERVAL)


if __name__ == "__main__":
    main()
