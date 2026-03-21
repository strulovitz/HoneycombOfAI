"""
demo.py — Choose a Demo
========================
"""
from rich.console import Console
from rich.panel import Panel

console = Console()

console.print(Panel(
    "[bold]🐝 Beehive Of AI — Demos[/]\n\n"
    "Choose a demo to run:\n\n"
    "  [bold yellow]python demo_simple.py[/]  — Simple simulation (no AI needed)\n"
    "  [bold green]python demo_real.py[/]    — Real demo with AI (needs Ollama)\n",
    title="Available Demos",
    border_style="yellow"
))
