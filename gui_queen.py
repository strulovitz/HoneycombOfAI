"""
HoneycombOfAI — Queen Bee Console Widget
Job board, subtask progress, worker activity, and hive statistics.
"""

from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QGroupBox, QFrame,
    QGridLayout, QSplitter, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QTextCursor, QColor

from gui_styles import COLORS


class QueenConsole(QWidget):
    """Queen Bee console — command centre for managing the hive."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = None
        self._start_time = None
        self._jobs = {}  # job_id -> {nectar, status, subtasks_total, subtasks_done, honey, time}
        self._uptime_timer = QTimer()
        self._uptime_timer.timeout.connect(self._update_uptime)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # === Header ===
        header = QHBoxLayout()

        title_col = QVBoxLayout()
        title = QLabel("Queen Bee")
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['honey']};")
        title_col.addWidget(title)

        self.lbl_backend = QLabel("Backend: —")
        self.lbl_backend.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 12px;")
        title_col.addWidget(self.lbl_backend)

        header.addLayout(title_col)
        header.addStretch()

        # Status indicator
        self.status_frame = QFrame()
        self.status_frame.setFixedSize(200, 60)
        self.status_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 2px solid {COLORS['border']};
                border-radius: 10px;
            }}
        """)
        status_inner = QVBoxLayout(self.status_frame)
        status_inner.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_status = QLabel("IDLE")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.lbl_status.setStyleSheet(f"color: {COLORS['text_dim']}; background: transparent;")
        status_inner.addWidget(self.lbl_status)

        self.lbl_status_detail = QLabel("Not started")
        self.lbl_status_detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status_detail.setFont(QFont("Segoe UI", 10))
        self.lbl_status_detail.setStyleSheet(f"color: {COLORS['text_dim']}; background: transparent;")
        status_inner.addWidget(self.lbl_status_detail)

        header.addWidget(self.status_frame)
        layout.addLayout(header)

        # === Stats Row ===
        stats_layout = QGridLayout()
        stats_layout.setSpacing(12)

        self.stat_jobs = self._make_stat("0", "JOBS COMPLETED")
        self.stat_current = self._make_stat("—", "CURRENT JOB")
        self.stat_subtasks = self._make_stat("—", "SUBTASK PROGRESS")
        self.stat_uptime = self._make_stat("00:00", "UPTIME")

        stats_layout.addWidget(self.stat_jobs, 0, 0)
        stats_layout.addWidget(self.stat_current, 0, 1)
        stats_layout.addWidget(self.stat_subtasks, 0, 2)
        stats_layout.addWidget(self.stat_uptime, 0, 3)

        layout.addLayout(stats_layout)

        # === Main Content: Splitter with Job Board + Log ===
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Job board
        job_widget = QWidget()
        job_layout = QVBoxLayout(job_widget)
        job_layout.setContentsMargins(0, 0, 0, 0)

        job_header = QHBoxLayout()
        job_title = QLabel("Job Board")
        job_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        job_title.setStyleSheet(f"color: {COLORS['honey']};")
        job_header.addWidget(job_title)
        job_header.addStretch()
        job_layout.addLayout(job_header)

        self.job_table = QTableWidget()
        self.job_table.setColumnCount(5)
        self.job_table.setHorizontalHeaderLabels(["Job ID", "Task (Nectar)", "Status", "Progress", "Time"])
        self.job_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.job_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.job_table.setColumnWidth(0, 70)
        self.job_table.setColumnWidth(3, 160)
        self.job_table.setColumnWidth(4, 80)
        self.job_table.setAlternatingRowColors(True)
        self.job_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.job_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        job_layout.addWidget(self.job_table)

        splitter.addWidget(job_widget)

        # Activity log
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        log_layout.setContentsMargins(0, 0, 0, 0)

        log_title = QLabel("Activity Log")
        log_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        log_title.setStyleSheet(f"color: {COLORS['honey']};")
        log_layout.addWidget(log_title)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Cascadia Code", 11))
        self.log_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['bg_input']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
            }}
        """)
        log_layout.addWidget(self.log_text)

        splitter.addWidget(log_widget)
        splitter.setSizes([300, 200])

        layout.addWidget(splitter, stretch=1)

        # === Control Bar ===
        control_bar = QHBoxLayout()

        self.lbl_connection = QLabel("Disconnected")
        self.lbl_connection.setStyleSheet(f"color: {COLORS['text_dim']};")
        control_bar.addWidget(self.lbl_connection)

        control_bar.addStretch()

        self.btn_start = QPushButton("Start Queen")
        self.btn_start.setFixedWidth(160)
        self.btn_start.setFixedHeight(40)
        self.btn_start.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        control_bar.addWidget(self.btn_start)

        self.btn_stop = QPushButton("Stop Queen")
        self.btn_stop.setFixedWidth(140)
        self.btn_stop.setFixedHeight(40)
        self.btn_stop.setProperty("class", "danger")
        self.btn_stop.setEnabled(False)
        control_bar.addWidget(self.btn_stop)

        layout.addLayout(control_bar)

    def _make_stat(self, value, label):
        """Create a stat card frame."""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px;
            }}
        """)
        layout = QVBoxLayout(frame)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(2)

        val = QLabel(value)
        val.setObjectName("stat_value")
        val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        val.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        val.setStyleSheet(f"color: {COLORS['honey']}; background: transparent;")
        layout.addWidget(val)

        lbl = QLabel(label)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setFont(QFont("Segoe UI", 9))
        lbl.setStyleSheet(f"color: {COLORS['text_dim']}; background: transparent;")
        layout.addWidget(lbl)

        return frame

    def _get_stat_value_label(self, frame) -> QLabel:
        return frame.findChild(QLabel, "stat_value")

    # === Public API ===

    def set_backend_info(self, name: str, model: str):
        self.lbl_backend.setText(f"Backend: {name}  |  Model: {model}")

    def set_thread(self, thread):
        """Connect a QueenThread to this console."""
        self._thread = thread
        thread.status_changed.connect(self._on_status_changed)
        thread.log_message.connect(self._on_log_message)
        thread.job_started.connect(self._on_job_started)
        thread.job_completed.connect(self._on_job_completed)
        thread.subtasks_created.connect(self._on_subtasks_created)
        thread.subtask_progress.connect(self._on_subtask_progress)
        thread.stats_updated.connect(self._on_stats_updated)
        thread.error_occurred.connect(self._on_error)
        thread.connected.connect(self._on_connected)

    def on_started(self):
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self._start_time = datetime.now()
        self._uptime_timer.start(1000)
        self._set_status("STARTING", "Connecting...", COLORS['warning'])

    def on_stopped(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._uptime_timer.stop()
        self._set_status("STOPPED", "Not running", COLORS['text_dim'])

    # === Slots ===

    def _on_status_changed(self, status):
        status_map = {
            "idle": ("WATCHING", "Polling for jobs...", COLORS['success']),
            "polling": ("POLLING", "Checking for work...", COLORS['success']),
            "splitting": ("SPLITTING", "AI splitting task...", COLORS['amber']),
            "waiting": ("WAITING", "Workers processing...", COLORS['honey']),
            "combining": ("COMBINING", "AI merging results...", COLORS['amber']),
            "error": ("ERROR", "See log for details", COLORS['error']),
        }
        label, detail, color = status_map.get(status, ("UNKNOWN", "", COLORS['text_dim']))
        self._set_status(label, detail, color)

    def _on_log_message(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {msg}")
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)

    def _on_job_started(self, info):
        job_id = info["job_id"]
        nectar = info["nectar"]
        self._jobs[job_id] = {
            "nectar": nectar,
            "status": "Splitting",
            "subtasks_total": 0,
            "subtasks_done": 0,
            "time": "...",
        }
        self._update_job_table()
        lbl = self._get_stat_value_label(self.stat_current)
        if lbl:
            lbl.setText(f"#{job_id}")

    def _on_subtasks_created(self, info):
        job_id = info["job_id"]
        if job_id in self._jobs:
            self._jobs[job_id]["status"] = "Processing"
            self._jobs[job_id]["subtasks_total"] = info["count"]
            self._jobs[job_id]["subtasks_done"] = 0
        self._update_job_table()
        lbl = self._get_stat_value_label(self.stat_subtasks)
        if lbl:
            lbl.setText(f"0/{info['count']}")

    def _on_subtask_progress(self, info):
        job_id = info["job_id"]
        if job_id in self._jobs:
            self._jobs[job_id]["subtasks_done"] = info["completed"]
        self._update_job_table()
        lbl = self._get_stat_value_label(self.stat_subtasks)
        if lbl:
            lbl.setText(f"{info['completed']}/{info['total']}")

    def _on_job_completed(self, info):
        job_id = info["job_id"]
        if job_id in self._jobs:
            self._jobs[job_id]["status"] = "Complete"
            self._jobs[job_id]["time"] = f"{info['time']:.0f}s"
        self._update_job_table()
        lbl = self._get_stat_value_label(self.stat_current)
        if lbl:
            lbl.setText("—")
        lbl2 = self._get_stat_value_label(self.stat_subtasks)
        if lbl2:
            lbl2.setText("—")

    def _on_stats_updated(self, stats):
        lbl = self._get_stat_value_label(self.stat_jobs)
        if lbl:
            lbl.setText(str(stats["jobs_completed"]))

    def _on_error(self, msg):
        self._on_log_message(f"ERROR: {msg}")

    def _on_connected(self, ok):
        if ok:
            self.lbl_connection.setText("Connected")
            self.lbl_connection.setStyleSheet(f"color: {COLORS['success']};")
        else:
            self.lbl_connection.setText("Disconnected")
            self.lbl_connection.setStyleSheet(f"color: {COLORS['error']};")

    def _update_uptime(self):
        if self._start_time:
            delta = datetime.now() - self._start_time
            hours, remainder = divmod(int(delta.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            lbl = self._get_stat_value_label(self.stat_uptime)
            if lbl:
                if hours > 0:
                    lbl.setText(f"{hours}:{minutes:02d}:{seconds:02d}")
                else:
                    lbl.setText(f"{minutes:02d}:{seconds:02d}")

    def _set_status(self, label, detail, color):
        self.lbl_status.setText(label)
        self.lbl_status.setStyleSheet(f"color: {color}; background: transparent;")
        self.lbl_status_detail.setText(detail)
        self.status_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 2px solid {color};
                border-radius: 10px;
            }}
        """)

    def _update_job_table(self):
        """Refresh the job board table from internal state."""
        self.job_table.setRowCount(len(self._jobs))

        for row, (job_id, info) in enumerate(sorted(self._jobs.items(), reverse=True)):
            # Job ID
            id_item = QTableWidgetItem(f"#{job_id}")
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.job_table.setItem(row, 0, id_item)

            # Nectar (truncated)
            nectar_text = info["nectar"][:80]
            self.job_table.setItem(row, 1, QTableWidgetItem(nectar_text))

            # Status
            status = info["status"]
            status_item = QTableWidgetItem(status)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if status == "Complete":
                status_item.setForeground(QColor(COLORS['success']))
            elif status == "Processing":
                status_item.setForeground(QColor(COLORS['amber']))
            elif status == "Splitting":
                status_item.setForeground(QColor(COLORS['warning']))
            self.job_table.setItem(row, 2, status_item)

            # Progress bar
            total = info["subtasks_total"]
            done = info["subtasks_done"]
            if total > 0:
                progress = QProgressBar()
                progress.setMaximum(total)
                progress.setValue(done)
                progress.setFormat(f"{done}/{total}")
                self.job_table.setCellWidget(row, 3, progress)
            else:
                self.job_table.setItem(row, 3, QTableWidgetItem("—"))

            # Time
            time_item = QTableWidgetItem(info.get("time", "..."))
            time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.job_table.setItem(row, 4, time_item)
