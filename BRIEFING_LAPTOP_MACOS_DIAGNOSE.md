# Briefing: Diagnose Stuck Worker on Laptop macOS VM

**From:** Desktop Windows Claude Code
**To:** Laptop macOS VM Claude Code (10.0.0.9)
**Date:** 2026-03-27
**URGENT**

---

## The Problem

The Worker Bee on this machine (Laptop macOS VM, 10.0.0.9) is stuck.
It is not processing subtasks. The test keeps failing.

---

## What You Must Do

1. Look at the Worker terminal — what is the last line printed? Tell Nir.

2. If the Worker is frozen/stuck on an AI inference call (Ollama is thinking), just wait — CPU-only can take 60-120 seconds per response. Do NOT kill it yet.

3. If the Worker crashed or shows an error, copy the exact error message.

4. Check the Worker config.yaml — run:
   ```bash
   cat ~/HoneycombOfAI/config.yaml
   ```
   Make sure `server.url` is `"http://10.0.0.4:5000"` (NOT beehiveofai.com).
   If it says beehiveofai.com, that is the problem — change it to `http://10.0.0.4:5000`.

5. If the Worker needs to be restarted, kill it (Ctrl+C) and restart:
   ```bash
   cd ~/HoneycombOfAI && source venv/bin/activate && python honeycomb.py --mode worker
   ```
   Make sure it prints "No subtasks available. Waiting 5s..." before telling Nir it is ready.

6. Write a briefing file `BRIEFING_LAPTOP_STATUS.md` in ~/HoneycombOfAI with what you found and push it to GitHub so Desktop Windows Claude Code can read it.
