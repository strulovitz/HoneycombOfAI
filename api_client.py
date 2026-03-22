"""
api_client.py — HTTP Client for BeehiveOfAI Website API
========================================================
Handles all communication between HoneycombOfAI software and the website.
"""

import base64
import requests


class BeehiveAPIClient:
    """Communicates with the BeehiveOfAI website API."""

    def __init__(self, server_url: str):
        self.server_url = server_url.rstrip('/')
        self.token = None

    def login(self, email: str, password: str) -> dict:
        """Authenticate and store token. Returns user info dict."""
        r = requests.post(f"{self.server_url}/api/auth/login", json={
            "email": email, "password": password
        })
        r.raise_for_status()
        data = r.json()
        self.token = data['token']
        return data

    def _headers(self) -> dict:
        """Auth headers for API calls."""
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def get_pending_jobs(self, hive_id: int) -> list:
        """Get pending jobs for a hive."""
        r = requests.get(f"{self.server_url}/api/hive/{hive_id}/jobs/pending", headers=self._headers())
        r.raise_for_status()
        return r.json().get('jobs', [])

    def claim_job(self, job_id: int) -> dict:
        """Claim a pending job (sets status to splitting)."""
        r = requests.post(f"{self.server_url}/api/job/{job_id}/claim", headers=self._headers())
        r.raise_for_status()
        return r.json()

    def update_job_status(self, job_id: int, status: str) -> dict:
        """Update job status (processing, combining, etc.)."""
        r = requests.put(f"{self.server_url}/api/job/{job_id}/status",
                         headers=self._headers(), json={"status": status})
        r.raise_for_status()
        return r.json()

    def create_subtasks(self, job_id: int, subtask_texts: list) -> list:
        """Create subtasks for a job on the website."""
        r = requests.post(f"{self.server_url}/api/job/{job_id}/subtasks",
                          headers=self._headers(), json={"subtasks": subtask_texts})
        r.raise_for_status()
        return r.json().get('subtasks', [])

    def submit_subtask_result(self, subtask_id: int, result: str) -> dict:
        """Submit a completed subtask result."""
        r = requests.put(f"{self.server_url}/api/subtask/{subtask_id}/result",
                         headers=self._headers(), json={"result": result})
        r.raise_for_status()
        return r.json()

    def complete_job(self, job_id: int, honey: str) -> dict:
        """Submit honey and mark job as completed."""
        r = requests.post(f"{self.server_url}/api/job/{job_id}/complete",
                          headers=self._headers(), json={"honey": honey})
        r.raise_for_status()
        return r.json()

    def get_available_subtasks(self, hive_id: int) -> list:
        """Worker polls this to find pending subtasks in a hive."""
        r = requests.get(f"{self.server_url}/api/hive/{hive_id}/subtasks/available",
                         headers=self._headers())
        r.raise_for_status()
        return r.json().get('subtasks', [])

    def claim_subtask(self, subtask_id: int) -> dict:
        """Worker claims a specific subtask (marks it as assigned to this worker)."""
        r = requests.put(f"{self.server_url}/api/subtask/{subtask_id}/claim",
                         headers=self._headers())
        r.raise_for_status()
        return r.json()

    def get_job_subtasks(self, job_id: int) -> list:
        """Get all subtasks for a job with their statuses and results."""
        r = requests.get(f"{self.server_url}/api/job/{job_id}/subtasks",
                         headers=self._headers())
        r.raise_for_status()
        return r.json().get('subtasks', [])

    def heartbeat(self) -> dict:
        """Worker sends a heartbeat to show it is online."""
        r = requests.post(f"{self.server_url}/api/worker/heartbeat",
                          headers=self._headers())
        r.raise_for_status()
        return r.json()

    def check_connection(self) -> bool:
        """Check if the website is reachable."""
        try:
            r = requests.get(f"{self.server_url}/api/status", timeout=5)
            return r.status_code == 200
        except Exception:
            return False
