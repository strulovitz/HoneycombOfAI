# Briefing: PyQt6 GUI Complete — 2026-03-25

**From:** Desktop Claude Code (Opus 4.6, Windows 11)
**To:** ALL Claude Code instances (Laptop Debian, Laptop Windows, Desktop Linux Mint, any future instance)
**Date:** 2026-03-25 (evening)
**Priority:** MAJOR MILESTONE — HoneycombOfAI now has a native desktop GUI

---

## What Was Built

HoneycombOfAI now has a full native desktop GUI built with **PyQt6**. All three roles (Worker Bee, Queen Bee, Beekeeper) have dedicated dashboards. The GUI was tested end-to-end on Desktop Windows 11 — all three roles PASS.

### Launch Command

```bash
# Windows
python gui_main.py

# Linux (Debian 13 or Linux Mint 22.2)
source ~/honeycomb-venv/bin/activate
pip install PyQt6
cd ~/HoneycombOfAI
python gui_main.py
```

The GUI is **cross-platform** — same Python code on Windows, Debian, and Linux Mint. PyQt6 handles the native look. Fonts fall back from "Segoe UI" (Windows) to "Ubuntu"/"Cantarell" (Linux) automatically.

---

## New Files in HoneycombOfAI

| File | Purpose |
|------|---------|
| `gui_main.py` | Main window, mode selector (card-based), app entry point |
| `gui_worker.py` | Worker Bee dashboard: status indicator, stat cards, activity log |
| `gui_queen.py` | Queen Bee console: job board, subtask progress bars, activity log |
| `gui_beekeeper.py` | Beekeeper portal: task submission, live status polling, results, rating |
| `gui_settings.py` | Settings dialog: 4 tabs (General, AI Model, Auth, Backends), auto-detection |
| `gui_threads.py` | QThread wrappers for Worker/Queen polling (thread-safe signals/slots) |
| `gui_styles.py` | Bee-themed dark/amber stylesheet |
| `honeycomb_gui.log` | Runtime log file (errors, connection attempts, key actions) |

### Dependency Added
- `PyQt6==6.9.0` added to `requirements.txt`

---

## New API Endpoints in BeehiveOfAI

Two new endpoints were added to `app.py` to support the GUI:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/hive/<hive_id>/jobs` | POST | Submit a job (Beekeeper GUI) |
| `/api/job/<job_id>` | GET | Poll job status (Beekeeper GUI) |

Both use the same `@api_auth_required` Bearer token authentication as existing endpoints.

---

## Config.yaml Changes

A new `beekeeper` section now includes credentials:

```yaml
beekeeper:
  email: "company1@test.com"
  password: "test123"
  hive_id: 1
  max_budget_per_job: 1.0
```

The GUI Settings dialog (File > Settings > Authentication tab) has fields for all three roles: Worker, Queen, and Beekeeper credentials.

**Config.yaml remains the single source of truth** — the GUI reads and writes it via the Settings dialog, exactly as specified in Chapter 7 of the book.

---

## Architecture Notes for Future Claude Codes

### Threading Model
- GUI runs on the main thread (PyQt6 event loop)
- Worker Bee polling runs in `WorkerThread(QThread)`
- Queen Bee polling runs in `QueenThread(QThread)`
- All GUI updates happen via Qt signals/slots (thread-safe, never call GUI directly from threads)

### Error Handling
- All errors logged to `honeycomb_gui.log` (FileHandler + StreamHandler)
- GUI shows **user-friendly** error messages, never raw exceptions
- Connection errors → "website not running" or "check URL in Settings"
- Auth errors → "go to Settings > Authentication tab"
- Global exception handler catches unhandled errors and logs them

### Beekeeper Lazy Connection
- The Beekeeper portal does NOT connect on startup
- Connection happens lazily when the user clicks "Submit Task"
- If credentials change in Settings, the connection is reset automatically

### Terminal CLI Still Works
- `python honeycomb.py` continues to work exactly as before
- GUI and CLI coexist — the GUI is an alternative interface, not a replacement

---

## Test Results (Desktop Windows 11, 2026-03-25 evening)

| Role | Test | Result |
|------|------|--------|
| Beekeeper | Submit task via GUI, receive result, rate | PASS |
| Worker Bee | Start worker in GUI, process subtasks, live dashboard | PASS |
| Queen Bee | Start queen in GUI, split/track/combine, job board | PASS |

For each test, the other two roles ran in separate terminal windows using `python honeycomb.py --mode <role>`.

---

## What's Next

1. **Test GUI on Linux** — Should work identically on Debian 13 and Linux Mint 22.2
2. **GUI polish** — Icons/emojis for role cards, system tray icon, notifications
3. **Installers** — Windows (.exe via PyInstaller), Linux (.deb), macOS (.app)
4. **Chapter 9** — Document the GUI development in the book

---

## CRITICAL WARNINGS (unchanged)

1. **NEVER** run `sudo apt upgrade` on Linux machines with NVIDIA GPU
2. Config.yaml credentials are plaintext — `.gitignore` should exclude it in production
3. The `honeycomb_gui.log` file grows over time — consider rotation for long-running instances
4. GUI requires a display — won't work on headless servers (use CLI for those)
