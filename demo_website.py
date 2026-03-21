"""
demo_website.py — Phase 4 Integration Demo
===========================================
This script connects the HoneycombOfAI desktop software to the
BeehiveOfAI website. Jobs submitted on the website get processed
automatically by real AI (via Ollama) and the results appear on
the website.

BEFORE RUNNING:
  1. Start Ollama:   ollama serve
  2. Start website:  cd ../BeehiveOfAI && python app.py
  3. Run this:       python demo_website.py

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
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from ollama_client import OllamaClient
from queen_bee import QueenBee
from worker_bee import WorkerBee
from api_client import BeehiveAPIClient

console = Console()

WEBSITE_URL = "http://localhost:5000"
QUEEN_EMAIL = "queen1@test.com"
QUEEN_PASSWORD = "test123"
HIVE_ID = 1
MODEL = "llama3.2:3b"
NUM_WORKERS = 2
POLL_INTERVAL = 8  # seconds between checking for new jobs


def check_ollama() -> bool:
    """Verify Ollama is running and has the required model."""
    ai = OllamaClient()
    if not ai.is_available():
        console.print("[bold red]❌ Ollama is not running![/]")
        console.print("   Start it with: [bold]ollama serve[/]")
        return False

    models = ai.list_models()
    if MODEL not in models:
        console.print(f"[yellow]⚠️  Model '{MODEL}' not found. Available models: {models}[/]")
        console.print(f"   Install it with: [bold]ollama pull {MODEL}[/]")
        if not models:
            return False
        console.print(f"[yellow]   Will try with: {models[0]}[/]")
        return True  # Let it try with whatever is available

    console.print(f"[green]✅ Ollama running with model: {MODEL}[/]")
    return True


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

    # Step 1: Check prerequisites
    console.print(Rule("[bold]Checking Prerequisites[/]"))
    api = BeehiveAPIClient(WEBSITE_URL)

    if not check_website(api):
        sys.exit(1)

    if not check_ollama():
        sys.exit(1)

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
    queen = QueenBee(model_name=MODEL, temperature=0.5)

    for i in range(NUM_WORKERS):
        worker = WorkerBee(
            worker_id=f"worker-{i+1:03d}",
            model_name=MODEL,
            temperature=0.7
        )
        queen.add_worker(worker)

    if not queen.start():
        console.print("[bold red]❌ Queen Bee could not start. Check Ollama connection.[/]")
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
        f"and process it with real AI. You can watch the progress\n"
        f"on the job status page (refresh the page to update).[/]\n\n"
        f"Press [bold]Ctrl+C[/] to stop.",
        title="Instructions",
        border_style="green"
    ))

    # Step 5: Start polling
    queen.process_from_website(api, HIVE_ID, poll_interval=POLL_INTERVAL)


if __name__ == "__main__":
    main()
