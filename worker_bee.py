"""
WorkerBeeModule — Run Approved AI Sub-Tasks and Receive Money
=============================================================
The Worker Bee receives a sub-task from the Queen Bee, processes it
using a local AI model (via Ollama), and returns the result.
"""

import time
from typing import TYPE_CHECKING

from ollama_client import OllamaClient
from rich.console import Console
from rich.panel import Panel

if TYPE_CHECKING:
    from api_client import BeehiveAPIClient

console = Console()


class WorkerBee:
    """
    A Worker Bee in the Beehive Of AI network.

    Each Worker Bee runs on one person's home computer.
    It receives small, independent sub-tasks from the Queen Bee,
    processes them using a local AI model, and returns the results.
    """

    def __init__(self, worker_id: str, model_name: str = "llama3.2:3b",
                 ollama_url: str = "http://localhost:11434", temperature: float = 0.7):
        self.worker_id = worker_id
        self.model_name = model_name
        self.temperature = temperature
        self.ai = OllamaClient(base_url=ollama_url)
        self.tasks_completed = 0

    def start(self):
        """Start the Worker Bee and verify AI connection."""
        console.print(Panel(
            f"[bold yellow]🐝 Worker Bee [{self.worker_id}] started![/]\n"
            f"Model: {self.model_name}\n"
            f"Tasks completed: {self.tasks_completed}",
            title="Worker Bee",
            border_style="yellow"
        ))

        if self.ai.is_available():
            console.print(f"  ✅ Connected to Ollama")
        else:
            console.print(f"  ❌ [red]Cannot connect to Ollama! Is it running?[/]")
            return False
        return True

    def process_subtask(self, subtask_text: str) -> str:
        """
        Process a single sub-task using the local AI model.

        Args:
            subtask_text: The sub-task to process (a text prompt)

        Returns:
            The AI model's response as a string
        """
        prompt = f"""Please complete the following task thoroughly and concisely.
Give a clear, well-organized answer.

Task: {subtask_text}

Your answer:"""

        console.print(f"  🐝 [{self.worker_id}] Processing: [italic]{subtask_text[:80]}{'...' if len(subtask_text) > 80 else ''}[/]")

        result = self.ai.ask(
            prompt=prompt,
            model=self.model_name,
            temperature=self.temperature
        )

        self.tasks_completed += 1
        console.print(f"  ✅ [{self.worker_id}] Done! ({len(result)} chars)")

        return result

    def run_from_website(self, api: 'BeehiveAPIClient', hive_id: int, poll_interval: int = 5):
        """
        Connect to the BeehiveOfAI website and poll for subtasks to process.

        This is the main loop for distributed Phase 5 operation.
        The worker continuously checks the website for new subtasks,
        claims one, processes it with local Ollama, and submits the result.

        Args:
            api: The BeehiveAPIClient (already logged in)
            hive_id: Which hive to poll for subtasks
            poll_interval: Seconds to wait between polls when no work found
        """
        console.print(Panel(
            f"[bold yellow]🐝 Worker Bee [{self.worker_id}] connected to website![/]\n"
            f"Hive: #{hive_id}\n"
            f"Polling every {poll_interval} seconds for subtasks.\n"
            f"Press Ctrl+C to stop.",
            title="Worker Bee — Network Mode",
            border_style="yellow"
        ))

        while True:
            try:
                # Send heartbeat
                try:
                    api.heartbeat()
                except Exception:
                    pass  # Heartbeat failure is non-critical

                # Poll for available subtasks
                subtasks = api.get_available_subtasks(hive_id)

                if not subtasks:
                    console.print(f"[dim]🐝 [{self.worker_id}] No subtasks available. Waiting {poll_interval}s...[/dim]")
                    time.sleep(poll_interval)
                    continue

                # Take the first available subtask
                subtask_data = subtasks[0]
                subtask_id = subtask_data['id']
                subtask_text = subtask_data['subtask_text']
                job_id = subtask_data['job_id']

                console.print(f"\n[bold green]🐝 [{self.worker_id}] Found subtask #{subtask_id} for job #{job_id}![/bold green]")

                # Claim it (mark it as ours before another worker takes it)
                try:
                    api.claim_subtask(subtask_id)
                    console.print(f"  ✅ Claimed subtask #{subtask_id}")
                except Exception as e:
                    # Another worker claimed it first — just move on
                    console.print(f"  [yellow]⚠️  Could not claim subtask #{subtask_id} (already taken): {e}[/yellow]")
                    continue

                # Process with local Ollama
                result = self.process_subtask(subtask_text)

                # Submit result back to website
                try:
                    api.submit_subtask_result(subtask_id, result)
                    console.print(f"  ✅ Result submitted for subtask #{subtask_id}")
                except Exception as e:
                    console.print(f"  [red]❌ Failed to submit result for subtask #{subtask_id}: {e}[/red]")

            except KeyboardInterrupt:
                console.print(f"\n[bold yellow]🐝 Worker Bee [{self.worker_id}] shutting down.[/bold yellow]")
                break
            except Exception as e:
                console.print(f"[red]Error: {e}. Retrying in {poll_interval}s...[/red]")
                time.sleep(poll_interval)
