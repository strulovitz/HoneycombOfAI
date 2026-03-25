# Briefing for All Claude Code Instances

**From:** Laptop Claude Code (Opus 4.6, nir-laptop, Debian 13)
**Date:** 2026-03-24
**Priority:** Important — affects user experience on Linux

---

## Who Should Read This

This briefing is for:
- **Desktop Windows Claude Code** (nir-desktop) — the Desktop computer running Windows
- **Laptop Windows Claude Code** (nir-laptop, Windows side) — the Laptop when booted into Windows
- **Any future Claude Code instance** working on this project

---

## Correction: LM Studio Requires Manual Server Start on ALL Platforms

### What Happened

On 2026-03-24, we incorrectly documented that LM Studio auto-starts its API server on Windows but not on Linux. **This was wrong.** LM Studio requires you to manually start the server on **all platforms** — Windows, Linux, and macOS. The original report was based on a mistaken recollection.

### The Correct Information

**LM Studio on ALL platforms:** Does NOT auto-start the API server. The user must go to the Developer tab (or Local Server tab) and click "Start Server" before port 1234 becomes active and HoneycombOfAI can detect it. This is the same on Windows, Linux, and macOS.

### What This Means for You

1. **The HoneycombOfAI code is correct and platform-agnostic.** The detection logic in `backend_detector.py` works the same everywhere — it tries `http://localhost:1234/v1/models` with a 2-second timeout. No code changes are needed.

2. **When helping users set up LM Studio on ANY platform**, always tell them to manually start the server in the Developer tab.

3. **Do NOT modify the detection code.** The code is correct. The manual server start is expected LM Studio behavior on all platforms.

### Action Items for Each Claude Code Instance

**All instances:**
- When writing docs or helping users with LM Studio, always mention the manual server start requirement
- This applies equally to Windows, Linux, and macOS — there is NO platform difference
- The exact steps: Open LM Studio > Load a model > Developer tab > Start Server > Verify port 1234
- If you previously documented a Windows/Linux difference for LM Studio, correct it

---

## The Three Repos — Reminder

All three repos are connected and should stay in sync:

1. **HoneycombOfAI** — The software (desktop client): https://github.com/strulovitz/HoneycombOfAI
2. **BeehiveOfAI** — The website (hub/marketplace): https://github.com/strulovitz/BeehiveOfAI
3. **TheDistributedAIRevolution** — The book: https://github.com/strulovitz/TheDistributedAIRevolution

When making findings or decisions that affect the project, update ALL relevant repos — not just the one you're working in. This briefing exists because important information needs to reach all Claude Code instances, regardless of which repo they happen to be working in.

---

---

## Phase 6 Backend Status (updated 2026-03-24 night)

| Backend | Windows | Debian | Status |
|---------|---------|--------|--------|
| Ollama | PASS | PASS | Done |
| LM Studio | PASS | PASS | Done (all platforms need manual server start) |
| llama.cpp server | PASS | Not tested | Done (Windows) |
| llama.cpp Python | PASS (CPU) | Not tested | Done (Windows) |
| vLLM | N/A | **NOT DONE** | **Next task** |

### vLLM — The Last Remaining Task

vLLM is Linux-only and is the 5th and final backend for Phase 6. It needs to be installed and tested on Debian 13 (Laptop).

**Plan:**
1. Install inside `~/honeycomb-venv` (isolated, safe)
2. `pip install vllm`
3. Start vLLM server with a model on port 8000
4. Run backend detector to confirm detection
5. Run `demo_real.py` with `backend: vllm` to test full pipeline
6. Commit and push results

**Critical warning:** The RTX 5090 (Blackwell architecture) has a fragile CUDA setup on Debian. If vLLM installation wants to touch system CUDA packages or install incompatible PyTorch versions, STOP and investigate. Everything must stay inside the venv. Never touch system-level NVIDIA/CUDA packages.

---

Thank you! Let's keep the communication between all instances strong. The project works best when we all have the full picture.
