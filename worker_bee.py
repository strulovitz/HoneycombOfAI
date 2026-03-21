"""
WorkerBeeModule — Run Approved AI Sub-Tasks and Receive Money
=============================================================
The Worker Bee receives a sub-task from the Queen Bee, processes it
using a local AI model (via Ollama), and returns the result.
"""

from ollama_client import OllamaClient
from rich.console import Console
from rich.panel import Panel

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

        This is the core function of the Worker Bee. It receives a sub-task
        (a specific question or instruction) and uses the AI model to generate
        a response.

        Args:
            subtask_text: The sub-task to process (a text prompt)

        Returns:
            The AI model's response as a string
        """
        prompt = f"""Please complete the following task thoroughly and concisely.
Give a clear, well-organized answer.

Task: {subtask_text}

Your answer:"""

        console.print(f"  🐝 [{self.worker_id}] Processing: [italic]{subtask_text[:80]}...[/]")

        result = self.ai.ask(
            prompt=prompt,
            model=self.model_name,
            temperature=self.temperature
        )

        self.tasks_completed += 1
        console.print(f"  ✅ [{self.worker_id}] Done! ({len(result)} chars)")

        return result
