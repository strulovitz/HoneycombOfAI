# Phase 6: Multi-Backend AI Support — Detailed Task for Laptop Claude Code

**From:** Desktop Claude Code (nir-desktop)
**To:** Laptop Claude Code (nir-laptop)
**Date:** 2026-03-24
**Project:** HoneycombOfAI

---

## Overview

The user (Nir) wants HoneycombOfAI to support **5 AI backend options** instead of just Ollama. This is a major feature that lets any user of the project pick whichever local AI engine they prefer. Development happens entirely on the Laptop.

---

## The 5 Backends to Support

| # | Backend | How to talk to it | Default Port | Platform | Notes |
|---|---------|-------------------|-------------|----------|-------|
| 1 | **Ollama** | `ollama` Python library | 11434 | Windows/Linux/Mac | Already implemented |
| 2 | **LM Studio** | OpenAI-compatible REST API | 1234 | Windows/Linux/Mac | GUI app with built-in API server |
| 3 | **llama.cpp (server)** | OpenAI-compatible REST API | 8080 | Windows/Linux/Mac | Fast C++ server (`llama-server`). This is the FAST option |
| 4 | **llama.cpp (Python)** | `llama-cpp-python` library | N/A (in-process) | Windows/Linux/Mac | Convenient (no separate server), but slower than C++ server |
| 5 | **vLLM** | OpenAI-compatible REST API | 8000 | **Linux only** | High-performance inference server |

### Important: LM Studio, llama.cpp server, and vLLM all speak the same OpenAI-compatible API format. So one shared client class can handle all three — just different URLs/ports.

---

## Installation Order (Option C)

**Step 1 — Windows:** Install and test LM Studio, llama.cpp (+ koboldcpp as a GUI to visually verify it works), and verify Ollama still works. The user already has Ollama on the Laptop.

**Step 2 — Debian 13:** Boot into Linux Debian 13 and install vLLM there. Test it there.

**Do Step 1 first (all Windows-compatible backends), then Step 2 (vLLM on Debian).**

---

## Architecture — What to Build

### 1. Abstract Base Class: `ai_backend.py`

Create an abstract base class `AIBackend` with this interface:
- `ask(prompt, model, temperature) -> str` — Send prompt, get text response
- `ask_for_json_list(prompt, model, temperature) -> list` — Send prompt, get JSON list (this can be a shared implementation in the base class — it calls `ask()` and parses the result. The current logic in `ollama_client.py` is good, move it to the base class)
- `is_available() -> bool` — Health check
- `list_models() -> list` — Get available models
- `backend_name() -> str` — Display name (e.g., "Ollama", "LM Studio")
- `benchmark(test_prompt) -> dict` — Run a quick benchmark and return capability info (response time, tokens/sec if available). This feeds into the Worker capability rating system.

### 2. Backend Implementations

**`ollama_backend.py`** — Refactor current `ollama_client.py` to extend `AIBackend`. Keep the `ollama` Python library.

**`openai_compat_backend.py`** — Single class that handles LM Studio, llama.cpp server, AND vLLM. They all use the same OpenAI-compatible API format:
- `POST /v1/chat/completions` — Chat
- `GET /v1/models` — List models
- Use the `requests` library (already a dependency). Do NOT add the `openai` package.
- Constructor takes: `base_url`, `backend_type` (one of "lmstudio", "llamacpp", "vllm"), and optional `api_key`
- Each backend type can have slightly different defaults and quirks

**`llamacpp_python_backend.py`** — Direct Python binding using `llama-cpp-python`. No server needed. The user must have a GGUF model file downloaded. This is the convenient-but-slower option.

### 3. Backend Factory: `backend_factory.py`

A factory function that reads the config and returns the right `AIBackend` instance:
```python
def create_backend(config: dict) -> AIBackend:
    backend = config["model"]["backend"]  # "ollama", "lmstudio", "llamacpp-server", "llamacpp-python", "vllm"
    ...
```

### 4. Auto-Detection: `backend_detector.py`

A module that scans common ports to find which backends are currently running:
- Try `http://localhost:11434` → Ollama
- Try `http://localhost:1234` → LM Studio
- Try `http://localhost:8080` → llama.cpp server
- Try `http://localhost:8000` → vLLM
- Check if `llama_cpp` Python module is importable → llama.cpp Python

This is used to **suggest** defaults to the user, NOT to auto-switch. Present findings like:
```
Detected AI backends:
  ✅ Ollama (localhost:11434) — 3 models available
  ✅ LM Studio (localhost:1234) — 1 model loaded
  ❌ llama.cpp server — not detected
  ❌ vLLM — not detected

Currently configured: Ollama
```

### 5. Worker Capability Rating System

This is important for the Queen Bee to assign appropriate tasks. Think about:

- **Benchmark on startup:** When a Worker Bee starts, it runs a quick benchmark:
  - Send a short standard prompt, measure response time
  - If the backend reports tokens/sec, capture that
  - Estimate max context length the worker can handle
  - Report GPU VRAM / model size if detectable

- **Capability report:** Each Worker sends its capability info to the Queen (via the website API — this may need a new API endpoint on BeehiveOfAI, which is fine to note but don't implement the website side)

- **Task assignment by Queen:** The Queen can use capability ratings to:
  - Assign harder/longer subtasks to stronger workers
  - Assign simpler subtasks to weaker workers
  - Reject workers that are too weak for a particular job
  - Balance load across workers of different capabilities

- **Honest capability verification:** The user noted that users might lie about their capabilities. The benchmark helps verify actual performance vs claimed performance.

### 6. Update Existing Files

**`config.yaml`** — Add the new backend options:
```yaml
model:
  backend: ollama  # Options: ollama, lmstudio, llamacpp-server, llamacpp-python, vllm
  base_url: "http://localhost:11434"  # Auto-set based on backend if not specified
  model_path: ""  # Only for llamacpp-python: path to GGUF model file
  worker_model: "llama3.2:3b"
  queen_model: "llama3.2:3b"
  temperature: 0.7
```

**`honeycomb.py`** — Replace direct `OllamaClient` usage with `create_backend()` factory. Show auto-detection results on startup.

**`worker_bee.py`** — Replace `OllamaClient` with `AIBackend`. Add capability benchmarking on startup.

**`queen_bee.py`** — Replace `OllamaClient` with `AIBackend`. Add capability-aware task assignment logic.

**`demo_real.py`** and **`demo_website.py`** — Update to use the factory instead of `OllamaClient` directly.

**`requirements.txt`** — Add `llama-cpp-python` (optional dependency). Do NOT add `openai` — use `requests` for OpenAI-compatible APIs.

**Keep `ollama_client.py`** — It still works, just refactored to extend `AIBackend`. Don't break existing imports.

---

## Testing Plan

For each backend, verify:
1. `is_available()` returns True when running, False when not
2. `list_models()` returns the correct models
3. `ask()` returns a real AI response
4. `ask_for_json_list()` parses correctly
5. `benchmark()` returns timing info
6. The full pipeline works: Queen splits → Workers process → Queen combines

### Test on Windows first:
1. Ollama (should still work as before)
2. LM Studio (install, load a model, start API server, test)
3. llama.cpp server (install, download a GGUF model, start server, test)
4. llama.cpp Python (pip install, load a GGUF model, test)

### Then test on Debian:
5. vLLM (install, start server, test)

---

## User Interaction Style

**VERY IMPORTANT:**
- **SUGGEST improvements, do NOT implement them automatically.** If you have ideas to make the project better, tell Nir clearly and wait for his approval before coding.
- **Discuss your approach BEFORE writing code.** Don't start coding based on assumptions.
- **The user wants to understand what's happening.** Explain things clearly.
- **The user is the boss.** He decides what gets implemented, you suggest and execute.

---

## What NOT to Do

- Do NOT add the `openai` Python package as a dependency — use `requests` for OpenAI-compatible APIs
- Do NOT implement auto-fallback between backends — the user controls which backend is active
- Do NOT force users to install GUI interfaces — they're optional for convenience
- Do NOT break the existing Ollama functionality — it must keep working exactly as before
- Do NOT make changes to the BeehiveOfAI website — that's a separate project

---

## Files You'll Create/Modify

### New files:
- `ai_backend.py` — Abstract base class
- `openai_compat_backend.py` — LM Studio / llama.cpp server / vLLM client
- `llamacpp_python_backend.py` — Direct llama-cpp-python binding
- `backend_factory.py` — Factory function
- `backend_detector.py` — Auto-detection of running backends

### Modified files:
- `ollama_client.py` — Refactor to extend AIBackend
- `config.yaml` — Add new backend options
- `honeycomb.py` — Use factory + auto-detection
- `worker_bee.py` — Use AIBackend + capability benchmarking
- `queen_bee.py` — Use AIBackend + capability-aware assignment
- `demo_real.py` — Use factory
- `demo_website.py` — Use factory
- `requirements.txt` — Add llama-cpp-python

---

## Order of Work Suggestion

1. First, discuss this plan with Nir and get his feedback
2. Create the abstract base class and factory
3. Refactor Ollama to use the new base class (verify nothing breaks)
4. Install LM Studio on Windows, implement OpenAI-compatible backend, test with LM Studio
5. Install llama.cpp, test with llama.cpp server
6. Implement llama.cpp Python backend, test
7. Implement auto-detection
8. Implement worker capability benchmarking
9. Update all entry points (honeycomb.py, demos)
10. Boot into Debian, install vLLM, test
11. Final integration test with full pipeline

**Remember: discuss with Nir before each major step. Suggest improvements. Be collaborative.**

Good luck, Laptop Claude! Let's make this project great together. 🐝
