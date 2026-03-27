# HoneycombOfAI — Platform Notes & Troubleshooting

> Important information for users running HoneycombOfAI on different operating systems.
> This document is part of the project's user guide and should be included in any future documentation or book.

---

## Backend Support Matrix

| Backend | Windows | Linux (Debian/Ubuntu/Mint) | macOS | Config Key |
|---------|---------|---------------------------|-------|------------|
| **Ollama** | Yes | Yes | Yes | `ollama` |
| **LM Studio** | Yes (manual server start) | Yes (manual server start) | Yes (manual server start) | `lmstudio` |
| **llama.cpp server** | Yes | Yes (build from source with CUDA) | Yes | `llamacpp-server` |
| **llama.cpp Python** | Yes (CPU) | Yes (CPU or GPU) | Yes (CPU) | `llamacpp-python` |
| **vLLM** | No | Yes (requires CUDA GPU) | No | `vllm` |

---

## LM Studio: Manual Server Start Required (All Platforms)

### The Issue

The backend detector may show LM Studio as **"not detected"** even though LM Studio is installed, running, and has a model loaded.

### Why This Happens

LM Studio does **not** automatically start its local API server when you load a model. This is the same on **all platforms** (Windows, Linux, macOS). You must manually enable the server before HoneycombOfAI can detect it.

The detection code in `backend_detector.py` tries to reach `http://localhost:1234/v1/models`. Nothing is listening on that port until you start the server yourself in LM Studio.

### How to Fix It

1. Open **LM Studio**
2. Load a model (if you haven't already)
3. Go to the **Developer** tab (in some versions it's called **Local Server**)
4. Click **Start Server**
5. Verify it says it's listening on **port 1234**
6. Now run HoneycombOfAI — the backend detector will show LM Studio as available

### How to Verify

After starting the server in LM Studio, you can verify it's working by running:

```bash
curl http://localhost:1234/v1/models
```

You should see a JSON response listing your loaded model(s). If you get "Connection refused," the server is not running yet.

### Tip

Every time you restart LM Studio, you will need to start the server again. It does not remember this setting between sessions (as of the current LM Studio version). This applies to all platforms.

---

## Ollama
- Works identically on Windows, Linux, and macOS
- Automatically serves on port 11434 when the Ollama service is running
- No platform-specific issues known
- Install: https://ollama.ai

---

## llama.cpp Server

- Works identically on all platforms once built
- You must manually start the server on all platforms (this is expected — it's a command-line server)
- Default port: 8080

### Building from Source on Linux with CUDA (GPU acceleration)

```bash
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
cmake -B build -DGGML_CUDA=ON
cmake --build build --config Release -j$(nproc)
```

The binary will be at `build/bin/llama-server`.

### Starting the Server

```bash
./build/bin/llama-server \
  --model /path/to/model.gguf \
  --port 8080 \
  --n-gpu-layers 99 \
  --ctx-size 4096
```

### Getting a GGUF Model

Download from HuggingFace (example — Qwen 3B, no approval needed):
```bash
huggingface-cli download Qwen/Qwen2.5-3B-Instruct-GGUF \
  qwen2.5-3b-instruct-q4_k_m.gguf --local-dir ~/models
```

---

## llama.cpp Python (llama-cpp-python)

- Works on all platforms
- No server needed — runs in-process
- Requires a GGUF model file (set `model_path` in config.yaml)
- Thread-safe with a lock — parallel workers are serialized (one at a time)

### Installing with GPU Acceleration on Linux

```bash
CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python
```

### Installing on Windows (CPU-only)

```bash
pip install llama-cpp-python
```

Note: GPU-accelerated builds on Windows require Visual Studio and CUDA toolkit. CPU-only is much slower (~75s vs ~23s for the demo task) but works out of the box.

---

## vLLM

- **Linux only** — vLLM does not support Windows or macOS
- Requires CUDA-compatible GPU
- Default port: 8000
- Uses HuggingFace models (not GGUF)
- Pre-allocates most of GPU VRAM for KV cache

### Installing

```bash
pip install vllm
```

### Starting the Server

```bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-3B-Instruct --port 8000
```

The model downloads automatically on first run from HuggingFace.

### Model Recommendations

- **Qwen/Qwen2.5-3B-Instruct** — Fully open, no approval needed, ~6GB download
- Models requiring HuggingFace approval (e.g., Meta Llama) may take days to get access

---

## PyQt6 GUI on Linux — Required System Package

The GUI (`gui_main.py`) uses PyQt6, which requires the `libxcb-cursor0` system package on Linux. Without it, the GUI will crash on startup with:

```
qt.qpa.plugin: From 6.5.0, xcb-cursor0 or libxcb-cursor0 is needed to load the Qt xcb platform plugin.
This application failed to start because no Qt platform plugin could be initialized.
```

**Fix (run once):**
```bash
sudo apt install -y libxcb-cursor0
```

This applies to all Debian-based distributions: Debian, Ubuntu, Linux Mint, Pop!_OS, etc. The package is not installed by default on most Linux distributions.

After installing, the GUI launches normally with `python gui_main.py`.

---

## Windows Firewall Silently Blocks Worker/Queen Connections

**Symptom:** HoneycombOfAI (Worker Bee or Queen Bee) shows "Cannot connect to BeehiveOfAI" — but the website works fine in a browser on the same Windows machine. Ping also works.

**Cause:** Windows Defender Firewall blocks incoming TCP connections **per executable**. Even though Flask binds to `0.0.0.0:5000`, Windows silently drops incoming connections from other machines unless the specific Python executable is explicitly allowed. There is no popup, no warning, no log entry.

**Fix:** Open PowerShell **as Administrator** and run:
```powershell
New-NetFirewallRule -DisplayName "BeehiveOfAI Python" -Direction Inbound -Action Allow -Program "C:\full\path\to\your\python.exe" -Protocol TCP -Profile Any
```

To find your Python path, run:
```bash
python -c "import sys; print(sys.executable)"
```

**Important:** Each Python installation (miniconda, virtualenv, system Python) is a different executable and needs its own rule. No restart required — the rule takes effect immediately.

This only affects **Windows hosts**. Linux and macOS do not have this problem.

---

## GPU/CUDA Warning for Linux

If your Linux machine has an NVIDIA GPU with CUDA drivers already working:

1. **NEVER** run `sudo apt upgrade` without checking what it wants to update
2. **NEVER** update NVIDIA drivers or CUDA unless absolutely necessary
3. Before any `apt install`, run with `--dry-run` first
4. Always use Python venvs to isolate packages
5. Run `nvidia-smi` after every installation to verify GPU is still working

This is especially critical for newer GPUs (RTX 4090, RTX 5090) where Linux driver support is still maturing.
