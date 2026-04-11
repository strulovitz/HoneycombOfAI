"""
QueenBeeModule — Split Big AI Jobs Into Small Tasks and Combine Results
=======================================================================
The Queen Bee is the brain of each Hive. She receives the full task (Nectar)
from the Beekeeper, splits it into independent sub-tasks, assigns them to
Worker Bees, collects their results, and combines them into the final
answer (Honey).
"""

from ai_backend import AIBackend
from worker_bee import WorkerBee
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import concurrent.futures
import time
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from api_client import BeehiveAPIClient

console = Console()


class QueenBee:
    """
    The Queen Bee manages a Hive of Worker Bees.

    She is responsible for:
    1. Splitting a big task (Nectar) into small independent sub-tasks
    2. Assigning sub-tasks to Worker Bees
    3. Collecting results from all Worker Bees
    4. Combining results into one final answer (Honey)
    """

    def __init__(self, model_name: str = "llama3.2:3b",
                 ollama_url: str = "http://localhost:11434", temperature: float = 0.5,
                 ai_backend: AIBackend = None, subtask_timeout: int = 300):
        self.model_name = model_name
        self.temperature = temperature
        self.subtask_timeout = subtask_timeout
        self.workers: list[WorkerBee] = []

        if ai_backend is not None:
            self.ai = ai_backend
        else:
            from ollama_client import OllamaClient
            self.ai = OllamaClient(base_url=ollama_url)

    def start(self):
        """Start the Queen Bee and verify AI connection."""
        console.print(Panel(
            f"[bold magenta]👑 Queen Bee started![/]\n"
            f"Model: {self.model_name}\n"
            f"Workers in Hive: {len(self.workers)}",
            title="Queen Bee",
            border_style="magenta"
        ))

        if self.ai.is_available():
            console.print(f"  ✅ Connected to {self.ai.backend_name()}")
        else:
            console.print(f"  ❌ [red]Cannot connect to {self.ai.backend_name()}! Is it running?[/]")
            return False
        return True

    def add_worker(self, worker: WorkerBee):
        """Add a Worker Bee to this Hive."""
        self.workers.append(worker)
        console.print(f"  🐝 Worker [{worker.worker_id}] joined the Hive (total: {len(self.workers)})")

    # =====================================================================
    # FUTURE FEATURE: Byzantine Generals Worker Trust Verification
    # =====================================================================
    # The Queen sends the SAME small test task to 3 workers and compares
    # results. If one worker disagrees with the other two, the naive
    # approach (majority vote) would kick the outlier out.
    #
    # But disagreement has multiple possible CAUSES:
    #   Cause A: Worker is broken or malicious → exclude it
    #   Cause B: Worker has a newer/better model → it might be the BEST one
    #   Cause C: Worker interpreted the question differently → not broken
    #
    # A smart system should determine WHY the worker disagrees, not just
    # THAT it disagrees. This is a causal inference problem — understanding
    # the cause behind the observed effect (disagreement).
    #
    # See Chapter 5 of "The Distributed AI Revolution" book for full
    # discussion of this problem and the Byzantine Generals analogy.
    #
    # def verify_worker_trust(self, worker: WorkerBee, test_task: str,
    #                         reference_workers: list[WorkerBee]) -> dict:
    #     """
    #     Verify a worker's trustworthiness using Byzantine fault detection.
    #
    #     Sends the same test_task to the target worker and reference_workers,
    #     compares results, and attempts to determine the CAUSE of any
    #     disagreement rather than simply punishing the outlier.
    #
    #     Returns:
    #         dict with 'trusted' (bool), 'cause' (str), 'confidence' (float)
    #     """
    #     # Step 1: Send same task to all workers
    #     all_workers = [worker] + reference_workers
    #     results = {}
    #     for w in all_workers:
    #         results[w.worker_id] = w.process_subtask(test_task)
    #
    #     # Step 2: Compare results — does the target worker agree with majority?
    #     # TODO: Implement semantic similarity, not just string matching
    #
    #     # Step 3: If disagreement detected, determine CAUSE:
    #     # - Check if disagreement is factual (different claims about reality)
    #     # - Check if disagreement is stylistic (same meaning, different words)
    #     # - Check if outlier has MORE detail (possible newer/better model)
    #     # - Check if outlier response is nonsensical (broken/malicious)
    #     # TODO: This is where causal inference methods could be applied
    #
    #     # Step 4: Return trust assessment with cause explanation
    #     pass
    # =====================================================================

    def split_task(self, nectar: str, num_subtasks: int = None) -> list[str]:
        """
        Split a big task (Nectar) into small independent sub-tasks.

        Uses the AI model to intelligently decompose the task.

        Args:
            nectar: The full task/question from the Beekeeper
            num_subtasks: How many sub-tasks to create (default: number of workers)

        Returns:
            A list of sub-task strings
        """
        if num_subtasks is None:
            num_subtasks = len(self.workers) if self.workers else 3

        console.print(Panel(
            f"[bold]Splitting Nectar into {num_subtasks} sub-tasks...[/]\n"
            f"Nectar: [italic]{nectar}[/]",
            title="🌸 Task Splitting",
            border_style="cyan"
        ))

        prompt = f"""Split this task into exactly {num_subtasks} independent sub-tasks.
Each sub-task covers a different part. Together they fully cover the original task.

Task: {nectar}

Return ONLY a JSON array of {num_subtasks} strings.
Example: ["sub-task 1", "sub-task 2", "sub-task 3"]"""

        subtasks = self.ai.ask_for_json_list(
            prompt=prompt,
            model=self.model_name,
            temperature=0.3  # Low temperature for structured output
        )

        # Ensure we have the right number of subtasks
        if len(subtasks) < num_subtasks:
            # If AI returned fewer, pad with generic tasks
            for i in range(len(subtasks), num_subtasks):
                subtasks.append(f"Provide additional details about: {nectar} (aspect {i+1})")
        elif len(subtasks) > num_subtasks:
            subtasks = subtasks[:num_subtasks]

        # Display the sub-tasks
        table = Table(title="Sub-tasks Created", border_style="cyan")
        table.add_column("#", style="bold")
        table.add_column("Sub-task", style="italic")
        for i, task in enumerate(subtasks):
            table.add_row(str(i + 1), task[:100] + ("..." if len(task) > 100 else ""))
        console.print(table)

        return subtasks

    def assign_and_process(self, subtasks: list[str]) -> list[dict]:
        """
        Assign sub-tasks to Worker Bees and process them IN PARALLEL.

        This is where the magic happens — all workers process their
        sub-tasks at the same time, not one after another!

        Args:
            subtasks: List of sub-task strings

        Returns:
            List of dicts with 'worker_id', 'subtask', and 'result'
        """
        console.print(Panel(
            f"[bold]Assigning {len(subtasks)} sub-tasks to {len(self.workers)} workers...[/]",
            title="📋 Task Assignment",
            border_style="green"
        ))

        results = []
        start_time = time.time()

        # Process ALL sub-tasks in parallel using threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.workers)) as executor:
            # Create a mapping of future -> (worker, subtask)
            future_to_task = {}
            for i, subtask in enumerate(subtasks):
                worker = self.workers[i % len(self.workers)]
                future = executor.submit(worker.process_subtask, subtask)
                future_to_task[future] = (worker, subtask)

            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_task):
                worker, subtask = future_to_task[future]
                try:
                    result = future.result()
                    results.append({
                        "worker_id": worker.worker_id,
                        "subtask": subtask,
                        "result": result
                    })
                except Exception as e:
                    results.append({
                        "worker_id": worker.worker_id,
                        "subtask": subtask,
                        "result": f"[ERROR] {str(e)}"
                    })

        elapsed = time.time() - start_time
        console.print(f"  ⏱️  All {len(subtasks)} sub-tasks completed in {elapsed:.1f} seconds")

        return results

    def combine_results(self, nectar: str, results: list[dict]) -> str:
        """
        Combine all Worker Bee results into one final answer (Honey).

        Uses the AI model to intelligently merge and organize the results.

        Args:
            nectar: The original task/question
            results: List of worker results

        Returns:
            The final combined answer (Honey)
        """
        console.print(Panel(
            "[bold]Combining all results into Honey...[/]",
            title="🍯 Making Honey",
            border_style="yellow"
        ))

        # Format results for the prompt
        formatted = ""
        for i, r in enumerate(results):
            formatted += f"\n--- Result from Worker {r['worker_id']} ---\n"
            formatted += f"Sub-task: {r['subtask']}\n"
            formatted += f"Answer: {r['result']}\n"

        prompt = f"""Combine these results into one answer.

Original question: {nectar}

Results:
{formatted}

Combine into one coherent answer. Remove redundancy, keep all important details."""

        honey = self.ai.ask(
            prompt=prompt,
            model=self.model_name,
            temperature=self.temperature
        )

        return honey

    def wait_for_subtasks(self, api: 'BeehiveAPIClient', job_id: int,
                          subtask_ids: list, timeout: int = 300, check_interval: int = 5) -> list:
        """
        Wait for all subtasks to be completed by distributed workers.

        Polls the website until all subtasks have status='completed' or until
        the timeout is reached (default 5 minutes).

        Returns:
            List of dicts with 'subtask', 'result', 'worker_id' for each completed subtask.
        """
        console.print(f"  [yellow]⏳ Waiting for {len(subtask_ids)} subtask(s) to be completed by workers...[/yellow]")
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                console.print(f"  [red]❌ Timeout waiting for subtasks after {timeout}s[/red]")
                raise TimeoutError(f"Subtasks not completed within {timeout} seconds")

            subtasks = api.get_job_subtasks(job_id)
            # Only check the subtasks we created (by ID)
            relevant = [st for st in subtasks if st['id'] in subtask_ids]
            completed = [st for st in relevant if st['status'] == 'completed']
            pending = [st for st in relevant if st['status'] != 'completed']

            console.print(
                f"  [dim]Progress: {len(completed)}/{len(relevant)} subtasks done "
                f"({int(elapsed)}s elapsed)[/dim]"
            )

            if len(completed) == len(relevant):
                console.print(f"  [bold green]✅ All {len(relevant)} subtasks completed by workers![/bold green]")
                return [
                    {
                        "subtask": st['subtask_text'],
                        "result": st['result_text'] or '',
                        "worker_id": str(st.get('worker_id', 'unknown'))
                    }
                    for st in completed
                ]

            time.sleep(check_interval)

    def process_from_website(self, api: 'BeehiveAPIClient', hive_id: int, poll_interval: int = 10):
        """Poll the website for new jobs and coordinate distributed workers to process them."""
        console.print(f"\n[bold yellow]👑 Queen Bee connected to website — polling Hive #{hive_id}[/bold yellow]")
        console.print(f"[dim]Checking for new jobs every {poll_interval} seconds. Subtask timeout: {self.subtask_timeout}s. Press Ctrl+C to stop.[/dim]\n")

        while True:
            try:
                jobs = api.get_pending_jobs(hive_id)

                if not jobs:
                    console.print(f"[dim]No pending jobs. Waiting {poll_interval}s...[/dim]")
                    time.sleep(poll_interval)
                    continue

                for job_data in jobs:
                    job_id = job_data['id']
                    nectar = job_data['nectar']
                    console.print(f"\n[bold green]🍯 New job #{job_id} received![/bold green]")
                    console.print(f"[dim]Nectar: {nectar[:100]}{'...' if len(nectar) > 100 else ''}[/dim]")

                    try:
                        # Step 1: Claim the job
                        api.claim_job(job_id)
                        console.print(f"[yellow]  ✂️  Splitting task into subtasks...[/yellow]")

                        # Step 2: Split task into subtasks using AI
                        subtasks = self.split_task(nectar)
                        website_subtasks = api.create_subtasks(job_id, subtasks)
                        subtask_ids = [ws['id'] for ws in website_subtasks]
                        console.print(f"[yellow]  📋 Created {len(subtask_ids)} subtasks on website — workers will pick them up![/yellow]")

                        # Step 3: Update status to 'processing' so workers know to start
                        api.update_job_status(job_id, 'processing')

                        # Step 4: Wait for distributed workers to complete the subtasks
                        results = self.wait_for_subtasks(api, job_id, subtask_ids, timeout=self.subtask_timeout)

                        # Step 5: Combine results into Honey
                        api.update_job_status(job_id, 'combining')
                        console.print(f"[yellow]  🔗 Combining results from all workers...[/yellow]")
                        honey = self.combine_results(nectar, results)

                        # Step 6: Upload Honey and mark complete
                        api.complete_job(job_id, honey)
                        console.print(f"[bold green]  ✅ Job #{job_id} completed![/bold green]")

                    except Exception as e:
                        console.print(f"[bold red]  ❌ Job #{job_id} failed: {e}[/bold red]")
                        try:
                            api.update_job_status(job_id, 'failed')
                        except Exception:
                            pass

            except KeyboardInterrupt:
                console.print("\n[bold yellow]👑 Queen Bee shutting down.[/bold yellow]")
                break
            except Exception as e:
                console.print(f"[red]Error polling: {e}. Retrying in {poll_interval}s...[/red]")
                time.sleep(poll_interval)

    def process_nectar(self, nectar: str) -> str:
        """
        The complete pipeline: receive Nectar, produce Honey.

        This is the main method that runs the entire process:
        1. Split the Nectar into sub-tasks
        2. Assign sub-tasks to Worker Bees (in parallel)
        3. Combine results into Honey
        4. Return the Honey

        Args:
            nectar: The full task/question from the Beekeeper

        Returns:
            The final answer (Honey)
        """
        console.print(Panel(
            f"[bold green]🌸 New Nectar received![/]\n\n[italic]{nectar}[/]",
            title="Incoming Nectar",
            border_style="green"
        ))

        total_start = time.time()

        # Step 1: Split
        subtasks = self.split_task(nectar)

        # Step 2: Assign and process in parallel
        results = self.assign_and_process(subtasks)

        # Step 3: Combine into Honey
        honey = self.combine_results(nectar, results)

        total_elapsed = time.time() - total_start

        console.print(Panel(
            f"[bold yellow]🍯 Honey is ready![/]\n"
            f"Total time: {total_elapsed:.1f} seconds\n"
            f"Workers used: {len(self.workers)}\n"
            f"Sub-tasks processed: {len(results)}",
            title="🍯 Honey Delivered",
            border_style="yellow"
        ))

        return honey
