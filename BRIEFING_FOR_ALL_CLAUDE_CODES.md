# Briefing for All Claude Code Instances

**From:** Laptop Claude Code (Opus 4.6, nir-laptop, Debian 13)
**Date:** 2026-03-25
**Priority:** MAJOR UPDATE — Phase 6 is now COMPLETE on all platforms

---

## Who Should Read This

This briefing is for:
- **Desktop Windows Claude Code** (nir-desktop) — the Desktop computer running Windows
- **Desktop Linux Mint Claude Code** (nir-desktop, Linux side) — the Desktop when booted into Linux Mint 22.2
- **Laptop Windows Claude Code** (nir-laptop, Windows side) — the Laptop when booted into Windows
- **Any future Claude Code instance** working on this project

---

## MAJOR MILESTONE: Phase 6 Is COMPLETE — All 5 Backends Working

As of 2026-03-25, all 5 AI backends have been tested and are working on both Windows and Debian/Linux. Phase 6 (multi-backend AI support) is feature-complete.

### Full Backend Status

| Backend | Windows | Debian/Linux | Config Key | Port | Notes |
|---------|---------|-------------|------------|------|-------|
| **Ollama** | PASS | PASS | `ollama` | 11434 | Recommended default |
| **LM Studio** | PASS | PASS | `lmstudio` | 1234 | All platforms need manual server start |
| **llama.cpp server** | PASS | PASS | `llamacpp-server` | 8080 | Built from source with CUDA on Debian |
| **llama.cpp Python** | PASS (CPU) | PASS (GPU) | `llamacpp-python` | N/A | In-process, much faster with GPU on Linux |
| **vLLM** | N/A | PASS | `vllm` | 8000 | Linux only |

### Demo Performance (Debian 13, RTX 5090, same task, 3 parallel workers)

| Backend | Time | Notes |
|---------|------|-------|
| llama.cpp server | 14.5s | Fastest on Debian |
| llama.cpp Python | 22.8s | GPU-accelerated (vs 75s CPU-only on Windows) |
| vLLM | 27.0s | Pre-allocates all VRAM |

---

## Correction: LM Studio Requires Manual Server Start on ALL Platforms

On 2026-03-24, we incorrectly documented that LM Studio auto-starts its API server on Windows but not on Linux. **This was wrong.** LM Studio requires you to manually start the server on **all platforms** — Windows, Linux, and macOS. The original report was based on a mistaken recollection.

**LM Studio on ALL platforms:** Does NOT auto-start the API server. The user must go to the Developer tab (or Local Server tab) and click "Start Server" before port 1234 becomes active and HoneycombOfAI can detect it. This is the same on Windows, Linux, and macOS.

**All instances:**
- When writing docs or helping users with LM Studio, always mention the manual server start requirement
- This applies equally to Windows, Linux, and macOS — there is NO platform difference
- The exact steps: Open LM Studio > Load a model > Developer tab > Start Server > Verify port 1234
- If you previously documented a Windows/Linux difference for LM Studio, correct it
- **Do NOT modify the detection code.** The code is correct. The manual server start is expected LM Studio behavior on all platforms.

---

## What Was Set Up on the Laptop Debian 13 (2026-03-24 to 2026-03-25)

### Software Installed
- Claude Code (via npm/nvm)
- Python 3.13 with venv at `~/honeycomb-venv`
- Ollama (running on port 11434)
- LM Studio (running, requires manual server start)
- vLLM 0.18.0 (in venv, uses HuggingFace models)
- llama.cpp (built from source at `~/llama.cpp` with CUDA, binary at `~/llama.cpp/build/bin/llama-server`)
- llama-cpp-python 0.3.18 (in venv, built with CUDA)
- GGUF model: `~/models/qwen2.5-3b-instruct-q4_k_m.gguf`
- HuggingFace model: `Qwen/Qwen2.5-3B-Instruct` (for vLLM, auto-cached)

### How to Start Each Backend on Debian

**Ollama:** Already running as a service. Nothing to do.

**LM Studio:** Open LM Studio > Developer tab > Start Server > Port 1234.

**llama.cpp server:**
```bash
~/llama.cpp/build/bin/llama-server \
  --model ~/models/qwen2.5-3b-instruct-q4_k_m.gguf \
  --port 8080 --n-gpu-layers 99 --ctx-size 4096
```

**llama.cpp Python:** No server needed — just set `backend: llamacpp-python` and `model_path: /home/nir/models/qwen2.5-3b-instruct-q4_k_m.gguf` in config.yaml.

**vLLM:**
```bash
source ~/honeycomb-venv/bin/activate
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-3B-Instruct --port 8000
```

---

## CRITICAL WARNING: GPU/CUDA Setup Is Fragile

This applies to **any Linux machine with an NVIDIA GPU** in this project:

1. **NEVER** run `sudo apt upgrade` or `sudo apt dist-upgrade`
2. **NEVER** update NVIDIA drivers, CUDA, or cuDNN packages
3. Before any `apt install`, run with `--dry-run` first — if it touches CUDA/NVIDIA, STOP
4. Always use Python venvs to isolate packages
5. Pin Python package versions with `pip install package==x.y.z`
6. Run `nvidia-smi` AFTER every installation to verify GPU stack
7. Prefer nvm for Node.js instead of apt

The RTX 5090 (Blackwell) on Debian and any NVIDIA GPU on Linux Mint have bleeding-edge driver requirements. Treat the GPU stack as read-only unless absolutely necessary.

---

## The Three Repos — Reminder

1. **HoneycombOfAI** — The software (desktop client): https://github.com/strulovitz/HoneycombOfAI
2. **BeehiveOfAI** — The website (hub/marketplace): https://github.com/strulovitz/BeehiveOfAI
3. **TheDistributedAIRevolution** — The book: https://github.com/strulovitz/TheDistributedAIRevolution

---

## Next Steps

1. **Desktop Linux Mint Setup** — Set up the Desktop's Linux Mint 22.2 with Claude Code, the project, and all backends (see `DESKTOP_LINUX_MINT_SETUP.md`)
2. **Cross-machine Linux test** — Run a real Queen-Worker test between Laptop Debian and Desktop Linux Mint, just like we did on Windows
3. **GUI development** — The GUI will modify only `config.yaml` to switch backends (single source of truth)

---

## Config.yaml Is the Single Source of Truth

When the future GUI needs to switch backends, it should modify ONLY `config.yaml`. The fields to change are:
- `model.backend` — one of: `ollama`, `lmstudio`, `llamacpp-server`, `llamacpp-python`, `vllm`
- `model.base_url` — the matching URL (or empty for llamacpp-python)
- `model.model_path` — only needed for `llamacpp-python` (path to GGUF file)
- `model.worker_model` and `model.queen_model` — the model name for the chosen backend

No command-line flags, no environment variables — the GUI modifies config.yaml and the software reads it.

---

Thank you! Phase 6 is a major milestone. All 5 backends work on all supported platforms. The architecture is proven and ready for the next phase.
