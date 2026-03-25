"""
HoneycombOfAI — Worker Bee Dashboard Widget
Clean dashboard with status indicator, stats, activity log, and start/stop control.
"""

from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QGroupBox, QFrame,
    QGridLayout, QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QTextCursor

from gui_styles import COLORS


class StatCard(QFrame):
    """A single stat display card."""

    def __init__(self, label: str, initial_value: str = "0", parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 12px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(4)

        self.value_label = QLabel(initial_value)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        self.value_label.setStyleSheet(f"color: {COLORS['honey']}; background: transparent;")
        layout.addWidget(self.value_label)

        self.name_label = QLabel(label.upper())
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setFont(QFont("Segoe UI", 10))
        self.name_label.setStyleSheet(f"color: {COLORS['text_dim']}; background: transparent;")
        layout.addWidget(self.name_label)

    def set_value(self, value: str):
        self.value_label.setText(value)


class WorkerDashboard(QWidget):
    """Worker Bee dashboard — the main view when running as a Worker."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = None
        self._start_time = None
        self._uptime_timer = QTimer()
        self._uptime_timer.timeout.connect(self._update_uptime)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # === Header ===
        header = QHBoxLayout()

        title_col = QVBoxLayout()
        title = QLabel("Worker Bee")
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
        self.status_frame.setFixedSize(180, 60)
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

        self.stat_tasks = StatCard("Tasks Completed")
        self.stat_chars = StatCard("Characters Generated")
        self.stat_uptime = StatCard("Uptime", "00:00")
        self.stat_last_task = StatCard("Last Task Time", "—")

        stats_layout.addWidget(self.stat_tasks, 0, 0)
        stats_layout.addWidget(self.stat_chars, 0, 1)
        stats_layout.addWidget(self.stat_uptime, 0, 2)
        stats_layout.addWidget(self.stat_last_task, 0, 3)

        layout.addLayout(stats_layout)

        # === Activity Log ===
        log_group = QGroupBox("Activity Log")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Cascadia Code", 11))
        self.log_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['bg_input']};
                border: none;
                font-family: "Cascadia Code", "Consolas", "Ubuntu Mono", monospace;
            }}
        """)
        log_layout.addWidget(self.log_text)

        layout.addWidget(log_group, stretch=1)

        # === Control Bar ===
        control_bar = QHBoxLayout()

        self.lbl_connection = QLabel("Disconnected")
        self.lbl_connection.setStyleSheet(f"color: {COLORS['text_dim']};")
        control_bar.addWidget(self.lbl_connection)

        control_bar.addStretch()

        self.btn_start = QPushButton("Start Worker")
        self.btn_start.setFixedWidth(160)
        self.btn_start.setFixedHeight(40)
        self.btn_start.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        control_bar.addWidget(self.btn_start)

        self.btn_stop = QPushButton("Stop Worker")
        self.btn_stop.setFixedWidth(140)
        self.btn_stop.setFixedHeight(40)
        self.btn_stop.setProperty("class", "danger")
        self.btn_stop.setEnabled(False)
        control_bar.addWidget(self.btn_stop)

        layout.addLayout(control_bar)

    # === Public API ===

    def set_backend_info(self, name: str, model: str):
        self.lbl_backend.setText(f"Backend: {name}  |  Model: {model}")

    def set_thread(self, thread):
        """Connect a WorkerThread to this dashboard."""
        self._thread = thread
        thread.status_changed.connect(self._on_status_changed)
        thread.log_message.connect(self._on_log_message)
        thread.task_completed.connect(self._on_task_completed)
        thread.stats_updated.connect(self._on_stats_updated)
        thread.error_occurred.connect(self._on_error)
        thread.connected.connect(self._on_connected)

    def on_started(self):
        """Called when the worker thread starts."""
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self._start_time = datetime.now()
        self._uptime_timer.start(1000)
        self._set_status("STARTING", "Connecting...", COLORS['warning'])

    def on_stopped(self):
        """Called when the worker thread stops."""
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._uptime_timer.stop()
        self._set_status("STOPPED", "Not running", COLORS['text_dim'])

    # === Slots ===

    def _on_status_changed(self, status):
        status_map = {
            "idle": ("WAITING", "Polling for subtasks...", COLORS['success']),
            "polling": ("POLLING", "Checking for work...", COLORS['success']),
            "processing": ("PROCESSING", "AI is thinking...", COLORS['amber']),
            "submitting": ("SUBMITTING", "Sending result...", COLORS['honey']),
            "error": ("ERROR", "See log for details", COLORS['error']),
        }
        label, detail, color = status_map.get(status, ("UNKNOWN", "", COLORS['text_dim']))
        self._set_status(label, detail, color)

    def _on_log_message(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {msg}")
        # Auto-scroll to bottom
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)

    def _on_task_completed(self, info):
        self.stat_last_task.set_value(f"{info['time']:.1f}s")

    def _on_stats_updated(self, stats):
        self.stat_tasks.set_value(str(stats["tasks_completed"]))
        chars = stats["total_chars"]
        if chars > 1000:
            self.stat_chars.set_value(f"{chars / 1000:.1f}K")
        else:
            self.stat_chars.set_value(str(chars))

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
            if hours > 0:
                self.stat_uptime.set_value(f"{hours}:{minutes:02d}:{seconds:02d}")
            else:
                self.stat_uptime.set_value(f"{minutes:02d}:{seconds:02d}")

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
