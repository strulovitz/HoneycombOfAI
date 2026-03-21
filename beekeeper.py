"""
BeekeeperModule — Submit AI Tasks and Receive Results
=====================================================
The Beekeeper is the company/customer who sends tasks (Nectar)
to a Hive and receives the final answer (Honey).
"""

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()


class Beekeeper:
    """
    The Beekeeper submits tasks and receives results.

    In the full system, the Beekeeper connects to a Hive over the network.
    For now (Phase 2), everything runs locally for testing.
    """

    def __init__(self, company_name: str = "Test Company"):
        self.company_name = company_name
        self.jobs_submitted = 0

    def start(self):
        """Start the Beekeeper module."""
        console.print(Panel(
            f"[bold blue]🏢 Beekeeper [{self.company_name}] ready![/]\n"
            f"Jobs submitted: {self.jobs_submitted}",
            title="Beekeeper",
            border_style="blue"
        ))

    def submit_nectar(self, nectar: str) -> str:
        """
        Submit a task (Nectar) to the Hive.

        For now, this just returns the nectar text.
        In the future, this will send the task over the network
        to a specific Hive.
        """
        self.jobs_submitted += 1
        console.print(Panel(
            f"[bold]📤 Submitting Nectar #{self.jobs_submitted}[/]\n\n"
            f"[italic]{nectar}[/]",
            title=f"🏢 {self.company_name}",
            border_style="blue"
        ))
        return nectar

    def receive_honey(self, honey: str):
        """
        Receive the final answer (Honey) from the Hive.
        Display it beautifully.
        """
        console.print()
        console.print(Panel(
            Markdown(honey),
            title="🍯 HONEY — Final Answer Delivered",
            border_style="bold yellow",
            padding=(1, 2)
        ))
        console.print(f"\n  📊 Total jobs completed: {self.jobs_submitted}")
