"""
HoneycombOfAI — Background Threads for GUI
QThread wrappers for Worker Bee and Queen Bee polling loops.
All communication with the GUI is via Qt signals (thread-safe).
"""

import time
import traceback
from PyQt6.QtCore import QThread, pyqtSignal


class WorkerThread(QThread):
    """Background thread for Worker Bee polling loop."""

    # Signals emitted to update the GUI
    status_changed = pyqtSignal(str)       # "idle", "polling", "processing", "submitting", "error"
    log_message = pyqtSignal(str)          # Activity log entry
    task_completed = pyqtSignal(dict)      # {"subtask_id": int, "chars": int, "time": float}
    stats_updated = pyqtSignal(dict)       # {"tasks_completed": int, "total_chars": int}
    error_occurred = pyqtSignal(str)       # Error message
    connected = pyqtSignal(bool)           # Connection status

    def __init__(self, worker_bee, api_client, hive_id, poll_interval=5):
        super().__init__()
        self.worker_bee = worker_bee
        self.api = api_client
        self.hive_id = hive_id
        self.poll_interval = poll_interval
        self._running = False
        self._tasks_completed = 0
        self._total_chars = 0

    def run(self):
        self._running = True
        self.log_message.emit("Worker Bee started. Connecting to hive...")

        try:
            if not self.api.check_connection():
                self.error_occurred.emit("Cannot connect to BeehiveOfAI website")
                self.connected.emit(False)
                return

            self.connected.emit(True)
            self.log_message.emit(f"Connected to {self.api.server_url}")
            self.log_message.emit(f"Polling every {self.poll_interval}s for subtasks in Hive #{self.hive_id}")
        except Exception as e:
            self.error_occurred.emit(f"Connection failed: {e}")
            self.connected.emit(False)
            return

        while self._running:
            try:
                self.status_changed.emit("polling")

                # Send heartbeat (non-critical)
                try:
                    self.api.heartbeat()
                except Exception:
                    pass

                # Poll for available subtasks
                subtasks = self.api.get_available_subtasks(self.hive_id)

                if subtasks:
                    subtask = subtasks[0]
                    subtask_id = subtask["id"]
                    subtask_text = subtask.get("subtask_text", subtask.get("text", ""))

                    self.log_message.emit(f"Found subtask #{subtask_id}. Claiming...")

                    # Claim it
                    claim_result = self.api.claim_subtask(subtask_id)
                    if not claim_result:
                        self.log_message.emit(f"Could not claim subtask #{subtask_id} (taken by another worker)")
                        continue

                    self.status_changed.emit("processing")
                    self.log_message.emit(f"Processing subtask #{subtask_id} with {self.worker_bee.ai.backend_name()}...")

                    # Process with local AI
                    start_time = time.time()
                    result = self.worker_bee.process_subtask(subtask_text)
                    elapsed = time.time() - start_time

                    # Submit result
                    self.status_changed.emit("submitting")
                    self.api.submit_subtask_result(subtask_id, result)

                    self._tasks_completed += 1
                    self._total_chars += len(result)

                    self.log_message.emit(
                        f"Subtask #{subtask_id} complete ({len(result)} chars, {elapsed:.1f}s)"
                    )
                    self.task_completed.emit({
                        "subtask_id": subtask_id,
                        "chars": len(result),
                        "time": elapsed,
                    })
                    self.stats_updated.emit({
                        "tasks_completed": self._tasks_completed,
                        "total_chars": self._total_chars,
                    })
                    self.status_changed.emit("idle")
                else:
                    self.status_changed.emit("idle")

            except Exception as e:
                self.status_changed.emit("error")
                self.error_occurred.emit(f"Error: {e}")
                self.log_message.emit(f"Error: {e}")
                traceback.print_exc()

            # Wait before next poll
            for _ in range(self.poll_interval * 10):
                if not self._running:
                    break
                time.sleep(0.1)

        self.log_message.emit("Worker Bee stopped.")
        self.status_changed.emit("idle")

    def stop(self):
        self._running = False


class QueenThread(QThread):
    """Background thread for Queen Bee polling loop."""

    # Signals emitted to update the GUI
    status_changed = pyqtSignal(str)       # "idle", "polling", "splitting", "waiting", "combining", "error"
    log_message = pyqtSignal(str)          # Activity log entry
    job_started = pyqtSignal(dict)         # {"job_id": int, "nectar": str}
    job_completed = pyqtSignal(dict)       # {"job_id": int, "honey": str, "time": float}
    subtasks_created = pyqtSignal(dict)    # {"job_id": int, "count": int, "subtasks": list}
    subtask_progress = pyqtSignal(dict)    # {"job_id": int, "completed": int, "total": int}
    stats_updated = pyqtSignal(dict)       # {"jobs_completed": int}
    error_occurred = pyqtSignal(str)       # Error message
    connected = pyqtSignal(bool)           # Connection status

    def __init__(self, queen_bee, api_client, hive_id, poll_interval=10):
        super().__init__()
        self.queen_bee = queen_bee
        self.api = api_client
        self.hive_id = hive_id
        self.poll_interval = poll_interval
        self._running = False
        self._jobs_completed = 0

    def run(self):
        self._running = True
        self.log_message.emit("Queen Bee started. Connecting to hive...")

        try:
            if not self.api.check_connection():
                self.error_occurred.emit("Cannot connect to BeehiveOfAI website")
                self.connected.emit(False)
                return

            self.connected.emit(True)
            self.log_message.emit(f"Connected to {self.api.server_url}")
            self.log_message.emit(f"Polling every {self.poll_interval}s for jobs in Hive #{self.hive_id}")
        except Exception as e:
            self.error_occurred.emit(f"Connection failed: {e}")
            self.connected.emit(False)
            return

        while self._running:
            try:
                self.status_changed.emit("polling")

                # Poll for pending jobs
                jobs = self.api.get_pending_jobs(self.hive_id)

                if jobs:
                    job = jobs[0]
                    job_id = job["id"]
                    nectar = job.get("nectar", job.get("task_text", ""))

                    self.log_message.emit(f"Found job #{job_id}. Claiming...")
                    self.job_started.emit({"job_id": job_id, "nectar": nectar[:100] + "..."})

                    # Claim the job
                    self.api.claim_job(job_id)
                    self.log_message.emit(f"Job #{job_id} claimed. Splitting task with AI...")

                    # Split task
                    self.status_changed.emit("splitting")
                    start_time = time.time()
                    subtask_texts = self.queen_bee.split_task(nectar)
                    self.log_message.emit(f"Split into {len(subtask_texts)} subtasks")

                    # Create subtasks on website
                    subtask_results = self.api.create_subtasks(job_id, subtask_texts)
                    subtask_ids = [s["id"] for s in subtask_results]
                    self.api.update_job_status(job_id, "processing")

                    self.subtasks_created.emit({
                        "job_id": job_id,
                        "count": len(subtask_ids),
                        "subtasks": subtask_texts,
                    })
                    self.log_message.emit(f"Subtasks posted. Waiting for workers...")

                    # Wait for all subtasks to complete
                    self.status_changed.emit("waiting")
                    completed_subtasks = self._wait_for_subtasks(job_id, subtask_ids)

                    if completed_subtasks is None:
                        self.log_message.emit(f"Job #{job_id}: timed out waiting for workers")
                        continue

                    # Combine results
                    self.status_changed.emit("combining")
                    self.log_message.emit(f"All subtasks complete. Combining results with AI...")

                    results = []
                    for st in completed_subtasks:
                        results.append({
                            "worker_id": st.get("worker_id", "unknown"),
                            "subtask": st.get("subtask_text", ""),
                            "result": st.get("result_text", st.get("result", "")),
                        })

                    honey = self.queen_bee.combine_results(nectar, results)
                    elapsed = time.time() - start_time

                    # Complete job
                    self.api.complete_job(job_id, honey)

                    self._jobs_completed += 1
                    self.log_message.emit(
                        f"Job #{job_id} COMPLETE ({elapsed:.1f}s, {len(honey)} chars)"
                    )
                    self.job_completed.emit({
                        "job_id": job_id,
                        "honey": honey,
                        "time": elapsed,
                    })
                    self.stats_updated.emit({"jobs_completed": self._jobs_completed})
                    self.status_changed.emit("idle")
                else:
                    self.status_changed.emit("idle")

            except Exception as e:
                self.status_changed.emit("error")
                self.error_occurred.emit(f"Error: {e}")
                self.log_message.emit(f"Error: {e}")
                traceback.print_exc()

            # Wait before next poll
            for _ in range(self.poll_interval * 10):
                if not self._running:
                    break
                time.sleep(0.1)

        self.log_message.emit("Queen Bee stopped.")
        self.status_changed.emit("idle")

    def _wait_for_subtasks(self, job_id, subtask_ids, timeout=300, check_interval=5):
        """Poll website until all subtasks are completed or timeout."""
        elapsed = 0
        last_completed = 0

        while self._running and elapsed < timeout:
            try:
                subtasks = self.api.get_job_subtasks(job_id)
                completed = [s for s in subtasks if s.get("status") == "completed"]

                if len(completed) != last_completed:
                    self.subtask_progress.emit({
                        "job_id": job_id,
                        "completed": len(completed),
                        "total": len(subtask_ids),
                    })
                    self.log_message.emit(
                        f"Job #{job_id}: {len(completed)}/{len(subtask_ids)} subtasks done"
                    )
                    last_completed = len(completed)

                if len(completed) >= len(subtask_ids):
                    return completed

            except Exception as e:
                self.log_message.emit(f"Error checking subtasks: {e}")

            for _ in range(check_interval * 10):
                if not self._running:
                    return None
                time.sleep(0.1)
            elapsed += check_interval

        return None

    def stop(self):
        self._running = False
