"""
HoneycombOfAI — Main GUI Application
Native desktop application with Worker Bee, Queen Bee, and Beekeeper modes.
Launch with: python gui_main.py
"""

import sys
import os
import logging
import traceback
import yaml
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame, QMessageBox,
    QStatusBar, QSizePolicy,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon, QAction

from gui_styles import STYLESHEET, COLORS
from gui_worker import WorkerDashboard
from gui_queen import QueenConsole
from gui_beekeeper import BeekeeperPortal
from gui_settings import SettingsDialog
from gui_threads import WorkerThread, QueenThread


APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(APP_DIR, "config.yaml")
LOG_PATH = os.path.join(APP_DIR, "honeycomb_gui.log")

# Set up file logging — all errors go to honeycomb_gui.log
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stderr),
    ],
)
logger = logging.getLogger("HoneycombGUI")


def load_config():
    try:
        with open(CONFIG_PATH, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {
            "mode": "worker",
            "server": {"url": "http://localhost:5000"},
            "model": {
                "backend": "ollama",
                "base_url": "http://localhost:11434",
                "model_path": "",
                "worker_model": "llama3.2:3b",
                "queen_model": "llama3.2:3b",
                "temperature": 0.7,
            },
            "worker": {
                "worker_id": "worker-001",
                "hive_id": 1,
                "poll_interval": 5,
                "email": "",
                "password": "",
            },
            "queen": {"min_workers": 2, "max_workers": 10},
            "beekeeper": {"max_budget_per_job": 1.00},
            "auth": {"email": "", "password": "", "hive_id": 1},
        }


class ModeSelector(QWidget):
    """First screen — choose your role."""

    def __init__(self, on_mode_selected, parent=None):
        super().__init__(parent)
        self._on_mode_selected = on_mode_selected
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        # Logo / Title
        title = QLabel("HoneycombOfAI")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 36, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['honey']};")
        layout.addWidget(title)

        subtitle = QLabel("Personal Computers Working Together as One Powerful AI")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setFont(QFont("Segoe UI", 14))
        subtitle.setStyleSheet(f"color: {COLORS['text_dim']};")
        layout.addWidget(subtitle)

        layout.addSpacing(30)

        prompt = QLabel("Choose Your Role")
        prompt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        prompt.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        prompt.setStyleSheet(f"color: {COLORS['text']};")
        layout.addWidget(prompt)

        layout.addSpacing(10)

        # Role cards
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(20)
        cards_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        cards_layout.addWidget(self._make_role_card(
            "Worker Bee",
            "Contribute your computer's\nAI power to a Hive.\n\nEarn credits by processing\ntasks for others.",
            "worker",
        ))

        cards_layout.addWidget(self._make_role_card(
            "Queen Bee",
            "Manage a Hive of Workers.\n\nSplit tasks, coordinate work,\nand deliver results.",
            "queen",
        ))

        cards_layout.addWidget(self._make_role_card(
            "Beekeeper",
            "Submit tasks to a Hive\nand receive AI-powered results.\n\nThe client experience.",
            "beekeeper",
        ))

        layout.addLayout(cards_layout)
        layout.addStretch()

    def _make_role_card(self, title, description, mode):
        card = QFrame()
        card.setFixedSize(220, 260)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 2px solid {COLORS['border']};
                border-radius: 12px;
            }}
            QFrame:hover {{
                border-color: {COLORS['honey']};
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 20, 16, 16)

        icon_map = {"worker": "W", "queen": "Q", "beekeeper": "B"}
        icon_label = QLabel(icon_map.get(mode, "?"))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
        icon_label.setStyleSheet(f"""
            color: {COLORS['bg_dark']};
            background-color: {COLORS['honey']};
            border-radius: 25px;
            min-width: 50px;
            max-width: 50px;
            min-height: 50px;
            max-height: 50px;
        """)
        layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignCenter)

        name = QLabel(title)
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        name.setStyleSheet(f"color: {COLORS['honey']}; background: transparent;")
        layout.addWidget(name)

        desc = QLabel(description)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setFont(QFont("Segoe UI", 11))
        desc.setStyleSheet(f"color: {COLORS['text_dim']}; background: transparent;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        btn = QPushButton(f"Start as {title}")
        btn.clicked.connect(lambda: self._on_mode_selected(mode))
        layout.addWidget(btn)

        return card


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.config = load_config()
        self._worker_thread = None
        self._queen_thread = None
        self._api = None

        self.setWindowTitle("HoneycombOfAI")
        self.setMinimumSize(900, 650)
        self.resize(1050, 720)

        self._build_ui()
        self._build_menu()

        # Start with mode selector or go directly to configured mode
        self._show_mode_selector()

    def _build_ui(self):
        # Central stacked widget
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # Mode selector (index 0)
        self.mode_selector = ModeSelector(self._on_mode_selected)
        self.stack.addWidget(self.mode_selector)

        # Worker dashboard (index 1)
        self.worker_dashboard = WorkerDashboard()
        self.worker_dashboard.btn_start.clicked.connect(self._start_worker)
        self.worker_dashboard.btn_stop.clicked.connect(self._stop_worker)
        self.stack.addWidget(self.worker_dashboard)

        # Queen console (index 2)
        self.queen_console = QueenConsole()
        self.queen_console.btn_start.clicked.connect(self._start_queen)
        self.queen_console.btn_stop.clicked.connect(self._stop_queen)
        self.stack.addWidget(self.queen_console)

        # Beekeeper portal (index 3)
        self.beekeeper_portal = BeekeeperPortal()
        self.stack.addWidget(self.beekeeper_portal)

        # Status bar
        self.statusBar().showMessage("Ready")

    def _build_menu(self):
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("File")

        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self._open_settings)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()

        switch_mode_action = QAction("Switch Mode", self)
        switch_mode_action.triggered.connect(self._show_mode_selector)
        file_menu.addAction(switch_mode_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Help menu
        help_menu = menu_bar.addMenu("Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _show_mode_selector(self):
        self._stop_all_threads()
        self.stack.setCurrentIndex(0)
        self.statusBar().showMessage("Choose your role")

    def _on_mode_selected(self, mode):
        self.config["mode"] = mode

        if mode == "worker":
            self._setup_worker_view()
            self.stack.setCurrentIndex(1)
            self.statusBar().showMessage("Worker Bee — Ready to start")

        elif mode == "queen":
            self._setup_queen_view()
            self.stack.setCurrentIndex(2)
            self.statusBar().showMessage("Queen Bee — Ready to start")

        elif mode == "beekeeper":
            self._setup_beekeeper_view()
            self.stack.setCurrentIndex(3)
            self.statusBar().showMessage("Beekeeper Portal — Ready")

    def _setup_worker_view(self):
        model_config = self.config.get("model", {})
        backend_name = model_config.get("backend", "ollama")
        worker_model = model_config.get("worker_model", "unknown")
        self.worker_dashboard.set_backend_info(backend_name, worker_model)

    def _setup_queen_view(self):
        model_config = self.config.get("model", {})
        backend_name = model_config.get("backend", "ollama")
        queen_model = model_config.get("queen_model", "unknown")
        self.queen_console.set_backend_info(backend_name, queen_model)

    def _setup_beekeeper_view(self):
        # Don't auto-connect — just show the UI.
        # Connection happens when the user clicks Submit.
        self.beekeeper_portal.set_config(self.config)
        self.beekeeper_portal.set_connected(False)
        server_url = self.config.get("server", {}).get("url", "")
        if server_url:
            self.statusBar().showMessage(
                f"Beekeeper Portal — Server: {server_url} (click Submit to connect)"
            )

    # === Worker Controls ===

    def _start_worker(self):
        try:
            from backend_factory import create_backend
            from worker_bee import WorkerBee
            from api_client import BeehiveAPIClient

            ai = create_backend(self.config)
            model_config = self.config.get("model", {})
            worker_config = self.config.get("worker", {})

            worker = WorkerBee(
                worker_id=worker_config.get("worker_id", "worker-001"),
                ai_backend=ai,
                model_name=model_config.get("worker_model", "llama3.2:3b"),
                temperature=model_config.get("temperature", 0.7),
            )

            api = self._get_or_create_api()
            if not api:
                return

            self._login_api(api, "worker")

            hive_id = worker_config.get("hive_id", 1)
            poll_interval = worker_config.get("poll_interval", 5)

            self._worker_thread = WorkerThread(worker, api, hive_id, poll_interval)
            self.worker_dashboard.set_thread(self._worker_thread)
            self.worker_dashboard.on_started()

            self._worker_thread.finished.connect(self.worker_dashboard.on_stopped)
            self._worker_thread.start()

            self.statusBar().showMessage("Worker Bee running...")

        except Exception as e:
            logger.error(f"Could not start Worker Bee: {e}\n{traceback.format_exc()}")
            QMessageBox.critical(self, "Start Error", f"Could not start Worker Bee:\n{e}")

    def _stop_worker(self):
        if self._worker_thread and self._worker_thread.isRunning():
            self._worker_thread.stop()
            self._worker_thread.wait(5000)
            self._worker_thread = None
        self.worker_dashboard.on_stopped()
        self.statusBar().showMessage("Worker Bee stopped")

    # === Queen Controls ===

    def _start_queen(self):
        try:
            from backend_factory import create_backend
            from queen_bee import QueenBee
            from api_client import BeehiveAPIClient

            ai = create_backend(self.config)
            model_config = self.config.get("model", {})
            auth_config = self.config.get("auth", {})

            queen = QueenBee(
                ai_backend=ai,
                model_name=model_config.get("queen_model", "llama3.2:3b"),
                temperature=model_config.get("temperature", 0.7),
            )

            api = self._get_or_create_api()
            if not api:
                return

            self._login_api(api, "queen")

            hive_id = auth_config.get("hive_id", 1)

            self._queen_thread = QueenThread(queen, api, hive_id, poll_interval=10)
            self.queen_console.set_thread(self._queen_thread)
            self.queen_console.on_started()

            self._queen_thread.finished.connect(self.queen_console.on_stopped)
            self._queen_thread.start()

            self.statusBar().showMessage("Queen Bee running...")

        except Exception as e:
            logger.error(f"Could not start Queen Bee: {e}\n{traceback.format_exc()}")
            QMessageBox.critical(self, "Start Error", f"Could not start Queen Bee:\n{e}")

    def _stop_queen(self):
        if self._queen_thread and self._queen_thread.isRunning():
            self._queen_thread.stop()
            self._queen_thread.wait(5000)
            self._queen_thread = None
        self.queen_console.on_stopped()
        self.statusBar().showMessage("Queen Bee stopped")

    # === API Helpers ===

    def _friendly_connection_error(self, server_url, error):
        """Turn a raw connection error into a helpful message for the user."""
        err_str = str(error)
        if "Connection refused" in err_str or "Max retries" in err_str or "NewConnectionError" in err_str:
            return (
                f"Could not connect to: {server_url}\n\n"
                "This usually means one of two things:\n\n"
                "1. The BeehiveOfAI website is not running.\n"
                "   Start it first (python run_production.py or python app.py)\n\n"
                "2. The server URL is wrong.\n"
                "   Go to File > Settings > General tab to check the Website URL.\n"
                f"   Currently set to: {server_url}\n\n"
                "   Common URLs:\n"
                "   - Same computer:  http://localhost:5000\n"
                "   - LAN (other PC): http://10.0.0.4:5000\n"
                "   - Internet:       https://beehiveofai.com"
            )
        return f"Connection error with {server_url}:\n{error}"

    def _get_or_create_api(self):
        from api_client import BeehiveAPIClient
        server_url = self.config.get("server", {}).get("url", "")
        if not server_url:
            QMessageBox.warning(self, "No Server URL",
                                "No server URL is configured.\n\n"
                                "Please go to File > Settings > General tab\n"
                                "and enter the BeehiveOfAI website URL.\n\n"
                                "Common URLs:\n"
                                "- Same computer:  http://localhost:5000\n"
                                "- LAN (other PC): http://10.0.0.4:5000\n"
                                "- Internet:       https://beehiveofai.com")
            return None
        self._api = BeehiveAPIClient(server_url)
        return self._api

    def _login_api(self, api, role):
        """Log in to the API using credentials from config."""
        server_url = self.config.get("server", {}).get("url", "")
        try:
            if role == "worker":
                worker_cfg = self.config.get("worker", {})
                email = worker_cfg.get("email", "")
                password = worker_cfg.get("password", "")
            else:
                auth_cfg = self.config.get("auth", {})
                email = auth_cfg.get("email", "")
                password = auth_cfg.get("password", "")

            if not email or not password:
                QMessageBox.warning(self, "No Credentials",
                                    f"No {role} login credentials are configured.\n\n"
                                    "Please go to File > Settings > Authentication tab\n"
                                    f"and enter the email and password for the {role} account.")
                return

            api.login(email, password)
        except Exception as e:
            logger.error(f"Login failed as {role}: {e}")
            friendly = self._friendly_connection_error(server_url, e)
            QMessageBox.warning(self, "Connection Problem", friendly)

    # === Settings ===

    def _open_settings(self):
        dialog = SettingsDialog(self.config.copy(), CONFIG_PATH, self)
        if dialog.exec():
            self.config = dialog.get_config()
            # Reset connections so they use the new credentials on next attempt
            self.beekeeper_portal.set_config(self.config)
            self.beekeeper_portal.reset_connection()
            self._api = None
            self.statusBar().showMessage("Settings saved — credentials updated")

    # === Cleanup ===

    def _stop_all_threads(self):
        if self._worker_thread and self._worker_thread.isRunning():
            self._worker_thread.stop()
            self._worker_thread.wait(3000)
            self._worker_thread = None

        if self._queen_thread and self._queen_thread.isRunning():
            self._queen_thread.stop()
            self._queen_thread.wait(3000)
            self._queen_thread = None

    def closeEvent(self, event):
        self._stop_all_threads()
        event.accept()

    def _show_about(self):
        QMessageBox.about(
            self,
            "About HoneycombOfAI",
            "<h2 style='color: #f4a900;'>HoneycombOfAI</h2>"
            "<p><b>Personal Computers Working Together as One Powerful AI</b></p>"
            "<p>Turn many weak AIs into one powerful AI by distributing tasks "
            "across multiple computers in a coordinated hive.</p>"
            "<p>Part of the <b>BeehiveOfAI</b> ecosystem.</p>"
            "<p><a href='https://github.com/strulovitz/HoneycombOfAI'>GitHub</a></p>"
        )


def handle_exception(exc_type, exc_value, exc_tb):
    """Global exception handler — logs to file so user can copy-paste from honeycomb_gui.log."""
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logger.critical(f"Unhandled exception:\n{error_msg}")
    # Still show it in stderr for terminal users
    sys.__excepthook__(exc_type, exc_value, exc_tb)


def main():
    sys.excepthook = handle_exception

    app = QApplication(sys.argv)
    app.setApplicationName("HoneycombOfAI")
    app.setStyleSheet(STYLESHEET)

    logger.info("HoneycombOfAI GUI starting...")

    window = MainWindow()
    window.show()

    logger.info("GUI window shown. Ready.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
