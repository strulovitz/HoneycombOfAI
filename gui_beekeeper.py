"""
HoneycombOfAI — Beekeeper Portal Widget
Task submission, job status tracking, and results display.
"""

import logging
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QGroupBox, QFrame,
    QGridLayout, QComboBox, QMessageBox, QSplitter,
    QProgressBar,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QTextCursor

from gui_styles import COLORS

logger = logging.getLogger("HoneycombGUI")


class SubmitJobThread(QThread):
    """Submit a job to the BeehiveOfAI website in the background."""
    success = pyqtSignal(dict)   # job info
    error = pyqtSignal(str)

    def __init__(self, api, nectar, hive_id):
        super().__init__()
        self.api = api
        self.nectar = nectar
        self.hive_id = hive_id

    def run(self):
        try:
            import requests
            url = f"{self.api.server_url}/api/hive/{self.hive_id}/jobs"
            headers = self.api._headers()
            logger.info(f"Submitting job to {url}")
            resp = requests.post(url, json={"nectar": self.nectar}, headers=headers, timeout=15)
            if resp.status_code in (200, 201):
                logger.info(f"Job submitted successfully: {resp.json()}")
                self.success.emit(resp.json())
            else:
                error_msg = f"Server returned {resp.status_code}: {resp.text}"
                logger.error(f"Job submit failed: {error_msg}")
                self.error.emit(error_msg)
        except Exception as e:
            logger.error(f"Job submit exception: {e}")
            self.error.emit(str(e))


class JobPollThread(QThread):
    """Poll for job status updates."""
    status_updated = pyqtSignal(dict)  # {job_id, status, honey, ...}

    def __init__(self, api, job_id):
        super().__init__()
        self.api = api
        self.job_id = job_id
        self._running = True

    def run(self):
        while self._running:
            try:
                import requests
                url = f"{self.api.server_url}/api/job/{self.job_id}"
                headers = self.api._headers()
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    self.status_updated.emit(data)
                    if data.get("status") in ("completed", "failed"):
                        return
            except Exception:
                pass

            for _ in range(30):  # 3 second poll interval
                if not self._running:
                    return
                import time
                time.sleep(0.1)

    def stop(self):
        self._running = False


class BeekeeperPortal(QWidget):
    """Beekeeper portal — submit tasks, track jobs, view results."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._api = None
        self._hive_id = 1
        self._current_job_id = None
        self._poll_thread = None
        self._jobs_history = []

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # === Header ===
        header = QHBoxLayout()

        title = QLabel("Beekeeper Portal")
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['honey']};")
        header.addWidget(title)

        header.addStretch()

        self.lbl_connection = QLabel("Disconnected")
        self.lbl_connection.setStyleSheet(f"color: {COLORS['text_dim']};")
        header.addWidget(self.lbl_connection)

        layout.addLayout(header)

        # === Main splitter ===
        splitter = QSplitter(Qt.Orientation.Vertical)

        # --- Top: Task Submission ---
        submit_widget = QWidget()
        submit_layout = QVBoxLayout(submit_widget)
        submit_layout.setContentsMargins(0, 0, 0, 0)

        submit_group = QGroupBox("Submit a Task (Nectar)")
        submit_inner = QVBoxLayout(submit_group)

        self.txt_nectar = QTextEdit()
        self.txt_nectar.setPlaceholderText(
            "Type your task here...\n\n"
            "Examples:\n"
            "  - Analyze the pros and cons of renewable energy sources\n"
            "  - Write a comprehensive report on AI in healthcare\n"
            "  - Compare Python, Rust, and Go for backend development"
        )
        self.txt_nectar.setFont(QFont("Segoe UI", 12))
        self.txt_nectar.setMinimumHeight(120)
        submit_inner.addWidget(self.txt_nectar)

        btn_row = QHBoxLayout()

        lbl_hive = QLabel("Hive:")
        lbl_hive.setStyleSheet(f"color: {COLORS['text_dim']};")
        btn_row.addWidget(lbl_hive)

        self.combo_hive = QComboBox()
        self.combo_hive.addItem("Hive #1 (Default)")
        self.combo_hive.setFixedWidth(200)
        btn_row.addWidget(self.combo_hive)

        btn_row.addStretch()

        self.btn_submit = QPushButton("Submit Task")
        self.btn_submit.setFixedWidth(160)
        self.btn_submit.setFixedHeight(40)
        self.btn_submit.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.btn_submit.clicked.connect(self._submit_task)
        btn_row.addWidget(self.btn_submit)

        submit_inner.addLayout(btn_row)
        submit_layout.addWidget(submit_group)

        splitter.addWidget(submit_widget)

        # --- Bottom: Status & Results ---
        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)
        results_layout.setContentsMargins(0, 0, 0, 0)

        # Status bar
        status_frame = QFrame()
        status_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        status_inner = QHBoxLayout(status_frame)

        self.lbl_job_status = QLabel("No active job")
        self.lbl_job_status.setFont(QFont("Segoe UI", 13))
        self.lbl_job_status.setStyleSheet(f"color: {COLORS['text_dim']}; background: transparent;")
        status_inner.addWidget(self.lbl_job_status)

        status_inner.addStretch()

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setVisible(False)
        status_inner.addWidget(self.progress_bar)

        self.lbl_status_icon = QLabel("")
        self.lbl_status_icon.setFont(QFont("Segoe UI", 16))
        self.lbl_status_icon.setStyleSheet("background: transparent;")
        status_inner.addWidget(self.lbl_status_icon)

        results_layout.addWidget(status_frame)

        # Results display
        results_group = QGroupBox("Result (Honey)")
        results_inner = QVBoxLayout(results_group)

        self.txt_honey = QTextEdit()
        self.txt_honey.setReadOnly(True)
        self.txt_honey.setFont(QFont("Segoe UI", 12))
        self.txt_honey.setPlaceholderText("Results will appear here when a job is completed...")
        results_inner.addWidget(self.txt_honey)

        # Rating row
        rate_row = QHBoxLayout()
        rate_row.addStretch()

        self.lbl_rate = QLabel("Rate this result:")
        self.lbl_rate.setStyleSheet(f"color: {COLORS['text_dim']};")
        self.lbl_rate.setVisible(False)
        rate_row.addWidget(self.lbl_rate)

        self.rating_buttons = []
        for i in range(1, 6):
            btn = QPushButton(f"{'*' * i}")
            btn.setFixedWidth(50 + i * 8)
            btn.setProperty("class", "secondary")
            btn.setVisible(False)
            btn.clicked.connect(lambda checked, rating=i: self._rate_job(rating))
            rate_row.addWidget(btn)
            self.rating_buttons.append(btn)

        results_inner.addLayout(rate_row)

        results_layout.addWidget(results_group)

        splitter.addWidget(results_widget)
        splitter.setSizes([250, 350])

        layout.addWidget(splitter, stretch=1)

    # === Public API ===

    def set_api(self, api):
        self._api = api

    def set_connected(self, connected: bool):
        if connected:
            self.lbl_connection.setText("Connected")
            self.lbl_connection.setStyleSheet(f"color: {COLORS['success']};")
        else:
            self.lbl_connection.setText("Not connected (will connect on submit)")
            self.lbl_connection.setStyleSheet(f"color: {COLORS['text_dim']};")
        # Always allow submit — we'll connect lazily
        self.btn_submit.setEnabled(True)

    def set_config(self, config):
        """Store config so we can connect lazily when submitting."""
        self._config = config
        # Use beekeeper hive_id if set, otherwise default to 1
        self._hive_id = config.get("beekeeper", {}).get("hive_id", 1)

    def reset_connection(self):
        """Force reconnect on next submit (e.g. after changing credentials in Settings)."""
        self._api = None
        self.set_connected(False)

    # === Actions ===

    def _submit_task(self):
        nectar = self.txt_nectar.toPlainText().strip()
        if not nectar:
            QMessageBox.warning(self, "Empty Task", "Please type a task before submitting.")
            return

        # Lazy connect — try to create API and login now if not already connected
        if not self._api:
            config = getattr(self, "_config", None)
            if not config:
                QMessageBox.warning(self, "Not Connected",
                                    "Please go to File > Settings and set a server URL first.")
                return

            server_url = config.get("server", {}).get("url", "")
            if not server_url:
                QMessageBox.warning(self, "No Server URL",
                                    "Please go to File > Settings and set a server URL first.")
                return

            try:
                from api_client import BeehiveAPIClient
                api = BeehiveAPIClient(server_url)
                # Use beekeeper credentials, fall back to auth (queen) credentials
                bk_cfg = config.get("beekeeper", {})
                email = bk_cfg.get("email", "")
                password = bk_cfg.get("password", "")
                if not email or not password:
                    auth_cfg = config.get("auth", {})
                    email = auth_cfg.get("email", "")
                    password = auth_cfg.get("password", "")
                if not email or not password:
                    QMessageBox.warning(self, "No Credentials",
                                        "No login credentials are configured.\n\n"
                                        "Please go to File > Settings > Authentication tab\n"
                                        "and enter the email and password for the Beekeeper account.\n\n"
                                        "If you don't have an account yet, register on the\n"
                                        "BeehiveOfAI website first.")
                    return
                api.login(email, password)
                self._api = api
                self.set_connected(True)
            except Exception as e:
                logger.error(f"Beekeeper connection failed: {e}")
                err_str = str(e)
                if "Connection refused" in err_str or "Max retries" in err_str or "NewConnectionError" in err_str:
                    QMessageBox.warning(self, "Connection Problem",
                                        f"Could not connect to: {server_url}\n\n"
                                        "This usually means one of two things:\n\n"
                                        "1. The BeehiveOfAI website is not running.\n"
                                        "   Start it first (python run_production.py or python app.py)\n\n"
                                        "2. The server URL is wrong.\n"
                                        "   Go to File > Settings > General tab to check the Website URL.\n\n"
                                        "   Common URLs:\n"
                                        "   - Same computer:  http://localhost:5000\n"
                                        "   - LAN (other PC): http://10.0.0.4:5000\n"
                                        "   - Internet:       https://beehiveofai.com")
                elif "401" in err_str or "Invalid credentials" in err_str:
                    QMessageBox.warning(self, "Login Failed",
                                        "The email or password is incorrect.\n\n"
                                        "Please go to File > Settings > Authentication tab\n"
                                        "and check your credentials.\n\n"
                                        "If you don't have an account yet, register on the\n"
                                        "BeehiveOfAI website first.")
                else:
                    QMessageBox.warning(self, "Connection Failed",
                                        f"Could not connect to {server_url}:\n{e}")
                return

        self.btn_submit.setEnabled(False)
        self.btn_submit.setText("Submitting...")
        self._set_job_status("Submitting...", COLORS['warning'])

        self._submit_thread = SubmitJobThread(self._api, nectar, self._hive_id)
        self._submit_thread.success.connect(self._on_job_submitted)
        self._submit_thread.error.connect(self._on_submit_error)
        self._submit_thread.start()

    def _on_job_submitted(self, info):
        job_id = info.get("id", info.get("job_id", "?"))
        self._current_job_id = job_id
        self.btn_submit.setEnabled(True)
        self.btn_submit.setText("Submit Task")

        self._set_job_status(f"Job #{job_id} — Pending", COLORS['warning'])
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate

        self.txt_honey.clear()
        self._hide_rating()

        # Start polling for status
        self._poll_thread = JobPollThread(self._api, job_id)
        self._poll_thread.status_updated.connect(self._on_job_status_update)
        self._poll_thread.start()

    def _on_submit_error(self, error):
        self.btn_submit.setEnabled(True)
        self.btn_submit.setText("Submit Task")
        self._set_job_status(f"Submit failed", COLORS['error'])

        # Friendly error messages
        if "402" in error or "Not enough Nectars" in error:
            QMessageBox.warning(self, "Not Enough Nectars",
                                "Your account doesn't have enough Nectar credits.\n\n"
                                "Please visit the BeehiveOfAI website to buy a Nectar package\n"
                                "before submitting tasks.")
        elif "403" in error or "Only beekeepers" in error:
            QMessageBox.warning(self, "Wrong Account Role",
                                "The account you're logged in with is not a Beekeeper.\n\n"
                                "Please go to File > Settings > Authentication tab\n"
                                "and use a Beekeeper account's email and password.")
        elif "Connection refused" in error or "Max retries" in error:
            server_url = ""
            if hasattr(self, "_config") and self._config:
                server_url = self._config.get("server", {}).get("url", "")
            QMessageBox.warning(self, "Connection Lost",
                                f"Lost connection to the BeehiveOfAI website.\n\n"
                                "Make sure the website is still running and try again.\n"
                                f"Server URL: {server_url}")
            self._api = None  # Force reconnect on next attempt
            self.set_connected(False)
        else:
            QMessageBox.warning(self, "Submit Failed",
                                f"Could not submit the task:\n{error}")

    def _on_job_status_update(self, data):
        job_id = data.get("id", self._current_job_id)
        status = data.get("status", "unknown")

        status_display = {
            "pending": ("Pending — Waiting for Queen...", COLORS['warning']),
            "splitting": ("Splitting — Queen analyzing task...", COLORS['amber']),
            "processing": ("Processing — Workers computing...", COLORS['honey']),
            "combining": ("Combining — Queen merging results...", COLORS['amber']),
            "completed": ("Completed!", COLORS['success']),
            "failed": ("Failed", COLORS['error']),
        }

        display_text, color = status_display.get(status, (status, COLORS['text_dim']))
        self._set_job_status(f"Job #{job_id} — {display_text}", color)

        if status == "completed":
            honey = data.get("honey", data.get("result", ""))
            self.txt_honey.setPlainText(honey)
            self.progress_bar.setVisible(False)
            self._show_rating()
            self.lbl_status_icon.setText("DONE")
            self.lbl_status_icon.setStyleSheet(f"color: {COLORS['success']}; background: transparent; font-weight: bold;")

        elif status == "failed":
            self.progress_bar.setVisible(False)
            self.lbl_status_icon.setText("FAIL")
            self.lbl_status_icon.setStyleSheet(f"color: {COLORS['error']}; background: transparent; font-weight: bold;")

    def _rate_job(self, rating):
        """Submit a rating for the completed job."""
        self._hide_rating()
        self._set_job_status(
            f"Job #{self._current_job_id} — Completed (rated {'*' * rating})",
            COLORS['success']
        )
        # In a real implementation, this would call the API to submit the rating
        # For now, just acknowledge it locally

    def _set_job_status(self, text, color):
        self.lbl_job_status.setText(text)
        self.lbl_job_status.setStyleSheet(f"color: {color}; background: transparent;")

    def _show_rating(self):
        self.lbl_rate.setVisible(True)
        for btn in self.rating_buttons:
            btn.setVisible(True)

    def _hide_rating(self):
        self.lbl_rate.setVisible(False)
        for btn in self.rating_buttons:
            btn.setVisible(False)
