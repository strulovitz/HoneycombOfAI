"""
HoneycombOfAI — Settings Dialog
GUI form for editing config.yaml with dropdowns, validation, and backend detection.
"""

import yaml
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QPushButton, QGroupBox, QMessageBox, QTabWidget, QWidget,
    QTableWidget, QTableWidgetItem, QHeaderView,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon

from gui_styles import COLORS


class BackendDetectorThread(QThread):
    """Run backend detection in background to avoid freezing the dialog."""
    finished = pyqtSignal(list)

    def run(self):
        try:
            from backend_detector import detect_backends
            results = detect_backends()
            self.finished.emit(results)
        except Exception:
            self.finished.emit([])


class SettingsDialog(QDialog):
    """Settings dialog for editing HoneycombOfAI config.yaml."""

    def __init__(self, config: dict, config_path: str = "config.yaml", parent=None):
        super().__init__(parent)
        self.config = config
        self.config_path = config_path
        self._detected_backends = []

        self.setWindowTitle("HoneycombOfAI Settings")
        self.setMinimumWidth(550)
        self.setMinimumHeight(520)

        self._build_ui()
        self._load_values()
        self._detect_backends()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Tabs
        tabs = QTabWidget()
        tabs.addTab(self._build_general_tab(), "General")
        tabs.addTab(self._build_model_tab(), "AI Model")
        tabs.addTab(self._build_auth_tab(), "Authentication")
        tabs.addTab(self._build_backends_tab(), "Backends")
        layout.addWidget(tabs)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setProperty("class", "secondary")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Save Settings")
        self.btn_save.clicked.connect(self._save)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

    def _build_general_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Mode
        mode_group = QGroupBox("Mode")
        mode_layout = QFormLayout(mode_group)
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["worker", "queen", "beekeeper"])
        mode_layout.addRow("Role:", self.combo_mode)
        layout.addWidget(mode_group)

        # Server
        server_group = QGroupBox("Server Connection")
        server_layout = QFormLayout(server_group)
        self.edit_server_url = QLineEdit()
        self.edit_server_url.setPlaceholderText("http://localhost:5000")
        server_layout.addRow("Website URL:", self.edit_server_url)

        self.btn_test_connection = QPushButton("Test Connection")
        self.btn_test_connection.setProperty("class", "secondary")
        self.btn_test_connection.clicked.connect(self._test_connection)
        server_layout.addRow("", self.btn_test_connection)
        layout.addWidget(server_group)

        # Worker
        worker_group = QGroupBox("Worker Bee Settings")
        worker_layout = QFormLayout(worker_group)

        self.edit_worker_id = QLineEdit()
        self.edit_worker_id.setPlaceholderText("worker-001")
        worker_layout.addRow("Worker ID:", self.edit_worker_id)

        self.spin_hive_id = QSpinBox()
        self.spin_hive_id.setMinimum(1)
        self.spin_hive_id.setMaximum(9999)
        worker_layout.addRow("Hive ID:", self.spin_hive_id)

        self.spin_poll_interval = QSpinBox()
        self.spin_poll_interval.setMinimum(1)
        self.spin_poll_interval.setMaximum(120)
        self.spin_poll_interval.setSuffix(" seconds")
        worker_layout.addRow("Poll Interval:", self.spin_poll_interval)

        layout.addWidget(worker_group)

        # Queen
        queen_group = QGroupBox("Queen Bee Settings")
        queen_layout = QFormLayout(queen_group)

        self.spin_min_workers = QSpinBox()
        self.spin_min_workers.setMinimum(1)
        self.spin_min_workers.setMaximum(100)
        queen_layout.addRow("Min Workers:", self.spin_min_workers)

        self.spin_max_workers = QSpinBox()
        self.spin_max_workers.setMinimum(1)
        self.spin_max_workers.setMaximum(100)
        queen_layout.addRow("Max Workers:", self.spin_max_workers)

        layout.addWidget(queen_group)
        layout.addStretch()
        return widget

    def _build_model_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Backend selection
        backend_group = QGroupBox("AI Backend")
        backend_layout = QFormLayout(backend_group)

        self.combo_backend = QComboBox()
        self.combo_backend.addItems([
            "ollama", "lmstudio", "llamacpp-server", "llamacpp-python", "vllm"
        ])
        self.combo_backend.currentTextChanged.connect(self._on_backend_changed)
        backend_layout.addRow("Backend:", self.combo_backend)

        self.edit_base_url = QLineEdit()
        self.edit_base_url.setPlaceholderText("Auto-detected from backend")
        backend_layout.addRow("Base URL:", self.edit_base_url)

        self.edit_model_path = QLineEdit()
        self.edit_model_path.setPlaceholderText("Path to .gguf file (llamacpp-python only)")
        backend_layout.addRow("Model Path:", self.edit_model_path)

        layout.addWidget(backend_group)

        # Model names
        model_group = QGroupBox("Model Names")
        model_layout = QFormLayout(model_group)

        self.edit_worker_model = QLineEdit()
        self.edit_worker_model.setPlaceholderText("llama3.2:3b")
        model_layout.addRow("Worker Model:", self.edit_worker_model)

        self.edit_queen_model = QLineEdit()
        self.edit_queen_model.setPlaceholderText("llama3.2:3b")
        model_layout.addRow("Queen Model:", self.edit_queen_model)

        layout.addWidget(model_group)

        # Temperature
        temp_group = QGroupBox("Generation Settings")
        temp_layout = QFormLayout(temp_group)

        temp_row = QHBoxLayout()
        self.spin_temperature = QDoubleSpinBox()
        self.spin_temperature.setMinimum(0.0)
        self.spin_temperature.setMaximum(2.0)
        self.spin_temperature.setSingleStep(0.1)
        self.spin_temperature.setDecimals(1)
        temp_row.addWidget(self.spin_temperature)

        self.lbl_temp_hint = QLabel("0.7 = balanced")
        self.lbl_temp_hint.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 11px;")
        temp_row.addWidget(self.lbl_temp_hint)
        temp_row.addStretch()

        temp_layout.addRow("Temperature:", temp_row)
        layout.addWidget(temp_group)

        layout.addStretch()
        return widget

    def _build_auth_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Worker auth
        worker_auth_group = QGroupBox("Worker Bee Credentials")
        worker_auth_layout = QFormLayout(worker_auth_group)

        self.edit_worker_email = QLineEdit()
        self.edit_worker_email.setPlaceholderText("worker1@test.com")
        worker_auth_layout.addRow("Email:", self.edit_worker_email)

        self.edit_worker_password = QLineEdit()
        self.edit_worker_password.setEchoMode(QLineEdit.EchoMode.Password)
        worker_auth_layout.addRow("Password:", self.edit_worker_password)

        layout.addWidget(worker_auth_group)

        # Queen/auth
        queen_auth_group = QGroupBox("Queen Bee Credentials")
        queen_auth_layout = QFormLayout(queen_auth_group)

        self.edit_auth_email = QLineEdit()
        self.edit_auth_email.setPlaceholderText("queen1@test.com")
        queen_auth_layout.addRow("Email:", self.edit_auth_email)

        self.edit_auth_password = QLineEdit()
        self.edit_auth_password.setEchoMode(QLineEdit.EchoMode.Password)
        queen_auth_layout.addRow("Password:", self.edit_auth_password)

        self.spin_auth_hive_id = QSpinBox()
        self.spin_auth_hive_id.setMinimum(1)
        self.spin_auth_hive_id.setMaximum(9999)
        queen_auth_layout.addRow("Hive ID:", self.spin_auth_hive_id)

        layout.addWidget(queen_auth_group)

        # Beekeeper
        bk_group = QGroupBox("Beekeeper Credentials")
        bk_layout = QFormLayout(bk_group)

        self.edit_bk_email = QLineEdit()
        self.edit_bk_email.setPlaceholderText("company1@test.com")
        bk_layout.addRow("Email:", self.edit_bk_email)

        self.edit_bk_password = QLineEdit()
        self.edit_bk_password.setEchoMode(QLineEdit.EchoMode.Password)
        bk_layout.addRow("Password:", self.edit_bk_password)

        self.spin_bk_hive_id = QSpinBox()
        self.spin_bk_hive_id.setMinimum(1)
        self.spin_bk_hive_id.setMaximum(9999)
        bk_layout.addRow("Hive ID:", self.spin_bk_hive_id)

        self.spin_max_budget = QDoubleSpinBox()
        self.spin_max_budget.setMinimum(0.01)
        self.spin_max_budget.setMaximum(9999.99)
        self.spin_max_budget.setDecimals(2)
        self.spin_max_budget.setPrefix("$")
        bk_layout.addRow("Max Budget/Job:", self.spin_max_budget)

        layout.addWidget(bk_group)

        layout.addStretch()
        return widget

    def _build_backends_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        lbl = QLabel("Detected AI Backends")
        lbl.setProperty("class", "title")
        lbl.setStyleSheet(f"font-size: 16px; color: {COLORS['honey']}; margin-bottom: 8px;")
        layout.addWidget(lbl)

        self.backends_table = QTableWidget()
        self.backends_table.setColumnCount(4)
        self.backends_table.setHorizontalHeaderLabels(["Backend", "Status", "URL", "Models"])
        self.backends_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.backends_table.setAlternatingRowColors(True)
        self.backends_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.backends_table)

        btn_row = QHBoxLayout()
        self.btn_refresh_backends = QPushButton("Refresh Detection")
        self.btn_refresh_backends.setProperty("class", "secondary")
        self.btn_refresh_backends.clicked.connect(self._detect_backends)
        btn_row.addWidget(self.btn_refresh_backends)

        self.btn_use_selected = QPushButton("Use Selected Backend")
        self.btn_use_selected.clicked.connect(self._use_selected_backend)
        btn_row.addWidget(self.btn_use_selected)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addStretch()
        return widget

    def _load_values(self):
        """Load current config values into form fields."""
        c = self.config

        # General
        mode = c.get("mode", "worker")
        idx = self.combo_mode.findText(mode)
        if idx >= 0:
            self.combo_mode.setCurrentIndex(idx)

        self.edit_server_url.setText(c.get("server", {}).get("url", ""))

        worker = c.get("worker", {})
        self.edit_worker_id.setText(worker.get("worker_id", ""))
        self.spin_hive_id.setValue(worker.get("hive_id", 1))
        self.spin_poll_interval.setValue(worker.get("poll_interval", 5))

        queen = c.get("queen", {})
        self.spin_min_workers.setValue(queen.get("min_workers", 2))
        self.spin_max_workers.setValue(queen.get("max_workers", 10))

        # Model
        model = c.get("model", {})
        backend = model.get("backend", "ollama")
        idx = self.combo_backend.findText(backend)
        if idx >= 0:
            self.combo_backend.setCurrentIndex(idx)

        self.edit_base_url.setText(model.get("base_url", ""))
        self.edit_model_path.setText(model.get("model_path", ""))
        self.edit_worker_model.setText(model.get("worker_model", ""))
        self.edit_queen_model.setText(model.get("queen_model", ""))
        self.spin_temperature.setValue(model.get("temperature", 0.7))

        # Auth
        self.edit_worker_email.setText(worker.get("email", ""))
        self.edit_worker_password.setText(worker.get("password", ""))

        auth = c.get("auth", {})
        self.edit_auth_email.setText(auth.get("email", ""))
        self.edit_auth_password.setText(auth.get("password", ""))
        self.spin_auth_hive_id.setValue(auth.get("hive_id", 1))

        # Beekeeper
        bk = c.get("beekeeper", {})
        self.edit_bk_email.setText(bk.get("email", ""))
        self.edit_bk_password.setText(bk.get("password", ""))
        self.spin_bk_hive_id.setValue(bk.get("hive_id", 1))
        self.spin_max_budget.setValue(bk.get("max_budget_per_job", 1.00))

        self._on_backend_changed(backend)

    def _on_backend_changed(self, backend):
        """Update URL placeholder and model_path visibility based on backend."""
        url_defaults = {
            "ollama": "http://localhost:11434",
            "lmstudio": "http://localhost:1234",
            "llamacpp-server": "http://localhost:8080",
            "llamacpp-python": "(not needed)",
            "vllm": "http://localhost:8000",
        }
        self.edit_base_url.setPlaceholderText(url_defaults.get(backend, ""))
        self.edit_model_path.setEnabled(backend == "llamacpp-python")

        # Update temperature hint
        temp = self.spin_temperature.value()
        if temp < 0.3:
            hint = "Very focused/deterministic"
        elif temp < 0.6:
            hint = "Focused"
        elif temp < 0.9:
            hint = "Balanced"
        elif temp < 1.3:
            hint = "Creative"
        else:
            hint = "Very creative/random"
        self.lbl_temp_hint.setText(f"{temp:.1f} = {hint}")

    def _detect_backends(self):
        """Run backend detection in a background thread."""
        self.btn_refresh_backends.setEnabled(False)
        self.btn_refresh_backends.setText("Detecting...")

        self._detector_thread = BackendDetectorThread()
        self._detector_thread.finished.connect(self._on_backends_detected)
        self._detector_thread.start()

    def _on_backends_detected(self, results):
        self._detected_backends = results
        self.backends_table.setRowCount(len(results))

        for i, b in enumerate(results):
            name_item = QTableWidgetItem(b.get("name", "Unknown"))
            status = "Available" if b.get("available") else "Not Running"
            status_item = QTableWidgetItem(status)
            if b.get("available"):
                status_item.setForeground(Qt.GlobalColor.green)
            else:
                status_item.setForeground(Qt.GlobalColor.red)

            url_item = QTableWidgetItem(b.get("url", ""))
            models = b.get("models", [])
            models_text = ", ".join(models[:3])
            if len(models) > 3:
                models_text += f" (+{len(models) - 3} more)"
            models_item = QTableWidgetItem(models_text)

            self.backends_table.setItem(i, 0, name_item)
            self.backends_table.setItem(i, 1, status_item)
            self.backends_table.setItem(i, 2, url_item)
            self.backends_table.setItem(i, 3, models_item)

        self.btn_refresh_backends.setEnabled(True)
        self.btn_refresh_backends.setText("Refresh Detection")

    def _use_selected_backend(self):
        """Set the backend combo to the selected row's backend."""
        row = self.backends_table.currentRow()
        if row < 0 or row >= len(self._detected_backends):
            return

        b = self._detected_backends[row]
        if not b.get("available"):
            QMessageBox.warning(self, "Backend Not Available",
                                f"{b['name']} is not currently running.")
            return

        backend_key = b.get("backend_key", "")
        idx = self.combo_backend.findText(backend_key)
        if idx >= 0:
            self.combo_backend.setCurrentIndex(idx)
            self.edit_base_url.setText(b.get("url", ""))

    def _test_connection(self):
        """Test connection to the BeehiveOfAI website."""
        url = self.edit_server_url.text().strip()
        if not url:
            QMessageBox.warning(self, "No URL", "Please enter a server URL first.")
            return

        self.btn_test_connection.setEnabled(False)
        self.btn_test_connection.setText("Testing...")

        try:
            from api_client import BeehiveAPIClient
            api = BeehiveAPIClient(url)
            if api.check_connection():
                QMessageBox.information(self, "Connection OK",
                                        f"Successfully connected to {url}")
            else:
                QMessageBox.warning(self, "Connection Failed",
                                    f"Could not connect to {url}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Connection error: {e}")
        finally:
            self.btn_test_connection.setEnabled(True)
            self.btn_test_connection.setText("Test Connection")

    def _save(self):
        """Save all form values back to config dict and write config.yaml."""
        c = self.config

        c["mode"] = self.combo_mode.currentText()

        if "server" not in c:
            c["server"] = {}
        c["server"]["url"] = self.edit_server_url.text().strip()

        if "model" not in c:
            c["model"] = {}
        c["model"]["backend"] = self.combo_backend.currentText()
        c["model"]["base_url"] = self.edit_base_url.text().strip()
        c["model"]["model_path"] = self.edit_model_path.text().strip()
        c["model"]["worker_model"] = self.edit_worker_model.text().strip()
        c["model"]["queen_model"] = self.edit_queen_model.text().strip()
        c["model"]["temperature"] = self.spin_temperature.value()

        if "worker" not in c:
            c["worker"] = {}
        c["worker"]["worker_id"] = self.edit_worker_id.text().strip()
        c["worker"]["hive_id"] = self.spin_hive_id.value()
        c["worker"]["poll_interval"] = self.spin_poll_interval.value()
        c["worker"]["email"] = self.edit_worker_email.text().strip()
        c["worker"]["password"] = self.edit_worker_password.text().strip()

        if "queen" not in c:
            c["queen"] = {}
        c["queen"]["min_workers"] = self.spin_min_workers.value()
        c["queen"]["max_workers"] = self.spin_max_workers.value()

        if "beekeeper" not in c:
            c["beekeeper"] = {}
        c["beekeeper"]["email"] = self.edit_bk_email.text().strip()
        c["beekeeper"]["password"] = self.edit_bk_password.text().strip()
        c["beekeeper"]["hive_id"] = self.spin_bk_hive_id.value()
        c["beekeeper"]["max_budget_per_job"] = self.spin_max_budget.value()

        if "auth" not in c:
            c["auth"] = {}
        c["auth"]["email"] = self.edit_auth_email.text().strip()
        c["auth"]["password"] = self.edit_auth_password.text().strip()
        c["auth"]["hive_id"] = self.spin_auth_hive_id.value()

        # Write to file
        try:
            with open(self.config_path, "w") as f:
                yaml.dump(c, f, default_flow_style=False, sort_keys=False)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save config: {e}")

    def get_config(self):
        return self.config
