# HoneycombOfAI — Platform Notes & Troubleshooting

> Important information for users running HoneycombOfAI on different operating systems.
> This document is part of the project's user guide and should be included in any future documentation or book.

---

## LM Studio on Linux: Manual Server Start Required

### The Issue

When running HoneycombOfAI on Linux (e.g., Debian, Ubuntu), the backend detector may show LM Studio as **"not detected"** even though LM Studio is installed, running, and has a model loaded.

### Why This Happens

LM Studio behaves differently on Windows and Linux:

| Platform | Behavior |
|----------|----------|
| **Windows** | LM Studio **automatically** starts its local API server on port 1234 as soon as you load a model. No extra steps needed. HoneycombOfAI detects it instantly. |
| **Linux** | LM Studio does **NOT** auto-start the server. You must manually enable it. |

This is a LM Studio behavior difference — **not** a HoneycombOfAI bug. The detection code in `backend_detector.py` is identical and correct on all platforms. It simply tries to reach `http://localhost:1234/v1/models`, and on Linux, nothing is listening on that port until you start the server yourself.

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

### Permanent Tip

Every time you restart LM Studio on Linux, you will need to start the server again. It does not remember this setting between sessions (as of the current LM Studio version). On Windows, this is not necessary — it just works.

---

## Other Backends

### Ollama
- Works identically on Windows, Linux, and macOS
- Automatically serves on port 11434 when the Ollama service is running
- No platform-specific issues known

### llama.cpp Server
- Works identically on all platforms
- You must manually start the server on all platforms (this is expected — it's a command-line server)
- Default port: 8080

### vLLM
- **Linux only** — vLLM does not support Windows or macOS
- Requires CUDA-compatible GPU
- Default port: 8000

### llama.cpp Python (llama-cpp-python)
- Works on all platforms
- No server needed — runs in-process
- On Linux with NVIDIA GPU, install with CUDA support for GPU acceleration:
  ```bash
  CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python
  ```
