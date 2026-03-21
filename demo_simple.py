#!/usr/bin/env python3
"""
demo_simple.py — Beehive Of AI end-to-end simulation (no AI model or network required).

Simulates: Beekeeper → QueenBee → 3 WorkerBees → combined Honey → Beekeeper.
"""

import time

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text


# Minimal stubs so the simulation runs without a real AI backend
class BeekeeperModule:
    def __init__(self, config): pass
    def start(self): pass

class QueenBeeModule:
    def __init__(self, config): pass
    def start(self): pass

class WorkerBeeModule:
    def __init__(self, config): pass
    def start(self): pass

console = Console()

# ── Minimal demo config (no real server or model needed) ──────────────────────
DEMO_CONFIG = {
    "server": {"url": "http://localhost:5000"},
    "model": {"backend": "demo", "name": "demo-model"},
    "worker": {"max_concurrent_tasks": 1},
    "queen": {"min_workers": 2},
    "beekeeper": {"max_budget_per_job": 1.00},
}

# ── Hard-coded demo answers for each sub-task ─────────────────────────────────
DEMO_ANSWERS = {
    0: (
        "From an [bold green]environmental[/bold green] perspective, solar energy "
        "dramatically reduces carbon emissions, produces no air or water pollution "
        "during operation, and decreases our dependence on finite fossil fuels. "
        "Wide adoption could cut global CO₂ emissions by up to 4 gigatons per year."
    ),
    1: (
        "From an [bold yellow]economic[/bold yellow] perspective, solar panel costs "
        "have fallen over 90% in the last decade. Homeowners see average energy bill "
        "savings of $1,000–$1,500 per year. Solar jobs are now among the fastest-growing "
        "occupations, creating local employment that cannot be outsourced."
    ),
    2: (
        "From a [bold cyan]technological[/bold cyan] perspective, advances in "
        "perovskite cells and bifacial panels are pushing efficiency above 30%. "
        "Paired with modern battery storage, solar can now provide reliable 24/7 "
        "power. Smart-grid integration allows homes to sell excess power back "
        "automatically."
    ),
}


def pause(seconds: float = 0.5) -> None:
    time.sleep(seconds)


def main() -> None:
    console.print()
    console.print(Panel(
        Text("🐝  Beehive Of AI — Demo Simulation", style="bold yellow", justify="center"),
        border_style="yellow",
        padding=(1, 4),
    ))
    console.print()

    # ── Step 1: Create participants ────────────────────────────────────────────
    console.print(Rule("[bold]Setting up participants[/bold]", style="dim"))
    pause()

    beekeeper = BeekeeperModule(DEMO_CONFIG)
    console.print("[bold blue]🏢 Beekeeper[/bold blue] created.")
    pause(0.3)

    queen = QueenBeeModule(DEMO_CONFIG)
    console.print("[bold magenta]👑 QueenBee[/bold magenta] created.")
    pause(0.3)

    workers = [WorkerBeeModule(DEMO_CONFIG) for _ in range(3)]
    for i, _ in enumerate(workers):
        console.print(f"[bold yellow]💻 WorkerBee #{i + 1}[/bold yellow] created.")
        pause(0.2)

    console.print()

    # ── Step 2: Beekeeper submits the Nectar ──────────────────────────────────
    console.print(Rule("[bold]Step 1 — Beekeeper submits Nectar[/bold]", style="dim"))
    pause()

    nectar = (
        "Summarize the benefits of solar energy from three perspectives: "
        "environmental, economic, and technological."
    )
    console.print(f"[bold blue]🏢 Beekeeper[/bold blue] submitting Nectar:")
    console.print(Panel(f"[italic]{nectar}[/italic]", border_style="blue", padding=(0, 2)))
    pause()

    # ── Step 3: QueenBee splits into sub-tasks ────────────────────────────────
    console.print()
    console.print(Rule("[bold]Step 2 — QueenBee splits Nectar into sub-tasks[/bold]", style="dim"))
    pause()

    subtasks = [
        "Summarize environmental benefits of solar energy",
        "Summarize economic benefits of solar energy",
        "Summarize technological benefits of solar energy",
    ]
    console.print(f"[bold magenta]👑 QueenBee[/bold magenta] split the task into [bold]{len(subtasks)}[/bold] sub-tasks:")
    for i, st in enumerate(subtasks):
        pause(0.3)
        console.print(f"  [dim]{i + 1}.[/dim] {st}")
    pause()

    # ── Step 4: Each WorkerBee processes one sub-task ─────────────────────────
    console.print()
    console.print(Rule("[bold]Step 3 — Worker Bees process sub-tasks[/bold]", style="dim"))
    pause()

    results = []
    for i, (worker, subtask) in enumerate(zip(workers, subtasks)):
        console.print(f"\n[bold yellow]💻 WorkerBee #{i + 1}[/bold yellow] received: [italic]{subtask}[/italic]")
        pause(0.4)
        console.print(f"[dim]   Processing...[/dim]")
        pause(0.5)
        answer = DEMO_ANSWERS[i]
        results.append(answer)
        console.print(f"[bold yellow]💻 WorkerBee #{i + 1}[/bold yellow] result: {answer}")
        pause(0.3)

    # ── Step 5: QueenBee combines results ─────────────────────────────────────
    console.print()
    console.print(Rule("[bold]Step 4 — QueenBee combines all results into Honey[/bold]", style="dim"))
    pause()

    honey_sections = [
        ("🌿 Environmental Benefits", DEMO_ANSWERS[0]),
        ("💰 Economic Benefits",      DEMO_ANSWERS[1]),
        ("⚙️  Technological Benefits", DEMO_ANSWERS[2]),
    ]

    honey_lines = []
    for heading, body in honey_sections:
        honey_lines.append(f"[bold]{heading}[/bold]")
        honey_lines.append(body)
        honey_lines.append("")

    honey_text = "\n".join(honey_lines).strip()
    pause(0.5)
    console.print(f"[bold magenta]👑 QueenBee[/bold magenta] combined all answers into Honey.")
    pause()

    # ── Step 6: Beekeeper receives the Honey ──────────────────────────────────
    console.print()
    console.print(Rule("[bold]Step 5 — Beekeeper receives Honey[/bold]", style="dim"))
    pause()

    console.print(f"[bold blue]🏢 Beekeeper[/bold blue] received the final Honey:\n")
    console.print(Panel(honey_text, title="🍯 Honey — Final Answer", border_style="yellow", padding=(1, 2)))

    # ── Done ──────────────────────────────────────────────────────────────────
    console.print()
    console.print(Panel(
        Text("🍯  Demo Complete!", style="bold green", justify="center"),
        border_style="green",
        padding=(1, 4),
    ))
    console.print()


if __name__ == "__main__":
    main()
