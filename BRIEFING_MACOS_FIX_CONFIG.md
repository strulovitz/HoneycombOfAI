# Briefing: Fix macOS Queen Config — subtask_timeout Missing

**From:** Desktop Windows Claude Code
**To:** Desktop macOS VM Claude Code (10.0.0.7)
**Date:** 2026-03-27
**URGENT — Read and act on this immediately**

---

## The Problem

The macOS distributed test just failed again with a 300-second timeout.

The `subtask_timeout: 900` setting is missing from the Desktop macOS Queen's `config.yaml`.
It was added to the repo in commit `bf0c345` but the macOS VM was never updated.

The macOS VMs run Ollama on CPU-only — each AI response takes ~9-12 seconds. Two subtasks = ~30-60s of AI time plus overhead. The default 300s timeout should be enough but apparently is not. Set it to 900.

---

## What You Must Do RIGHT NOW

**On the Desktop macOS VM (10.0.0.7), edit `~/HoneycombOfAI/config.yaml`.**

Find the `queen:` section (it currently looks like this):
```yaml
queen:
  min_workers: 2
  max_workers: 10
```

Change it to:
```yaml
queen:
  min_workers: 2
  max_workers: 10
  subtask_timeout: 900
```

Also make sure `server.url` is set to `"http://10.0.0.4:5000"` (NOT beehiveofai.com).

The full correct config.yaml for the Desktop macOS Queen should be:
```yaml
mode: queen
server:
  url: "http://10.0.0.4:5000"
model:
  backend: ollama
  base_url: "http://localhost:11434"
  model_path: ""
  worker_model: "llama3.2:3b"
  queen_model: "llama3.2:3b"
  temperature: 0.7
worker:
  worker_id: "worker-desktop-macos-007"
  hive_id: 1
  poll_interval: 5
  email: "worker1@test.com"
  password: "test123"
queen:
  min_workers: 2
  max_workers: 10
  subtask_timeout: 900
beekeeper:
  email: "company1@test.com"
  password: "test123"
  hive_id: 1
  max_budget_per_job: 1.00
auth:
  email: "queen1@test.com"
  password: "test123"
  hive_id: 1
```

---

## After Fixing the Config

1. Stop the Queen if it's still running (Ctrl+C)
2. Start it again: `cd ~/HoneycombOfAI && source venv/bin/activate && python honeycomb.py --mode queen`
3. Tell Nir on Desktop Windows that the Queen is running again with 900s timeout
4. Desktop Windows Claude Code will resubmit the job

---

## Also Check: Laptop macOS Worker config

Ask Nir to verify the Laptop macOS VM (10.0.0.9) Worker is still polling.
If not, restart it: `cd ~/HoneycombOfAI && source venv/bin/activate && python honeycomb.py --mode worker`
