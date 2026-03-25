# Task: Set Up Desktop Linux Mint 22.2 with HoneycombOfAI

**From:** Laptop Claude Code (Opus 4.6, nir-laptop, Debian 13)
**To:** Whoever guides Nir through the Desktop Linux Mint setup
**Date:** 2026-03-25
**Priority:** Next task — set up the Desktop's Linux side

---

## The Goal

Set up the Desktop computer's Linux Mint 22.2 (Cinnamon) to have everything that the Desktop's Windows 11 already has:
- Claude Code
- HoneycombOfAI project (cloned from GitHub)
- All Python dependencies
- All 5 AI backends working (or as many as the hardware supports)
- Ready for cross-machine Linux-to-Linux testing with the Laptop (Debian 13)

---

## What We Know About the Desktop

- **OS:** Linux Mint 22.2 (Cinnamon) — based on Ubuntu 24.04 LTS
- **GPU:** Unknown — need to check what GPU the Desktop has
- **Dual boot:** Windows 11 (everything working) + Linux Mint 22.2
- **Network:** Same local network as the Laptop

---

## What We Learned from the Laptop Debian Setup

The Laptop Debian 13 setup took multiple days, mainly because of:
1. RTX 5090 Blackwell GPU driver issues (bleeding-edge hardware)
2. CUDA compatibility challenges

Linux Mint 22.2 is based on Ubuntu 24.04 which has better hardware support out of the box, so it should be smoother. But the same caution applies: **once GPU drivers are working, don't touch them.**

---

## Setup Steps (Step-by-Step)

### Phase 1: Verify What's Already Installed

```bash
# Open a terminal and run these commands:
python3 --version
node --version
npm --version
git --version
nvidia-smi
nvcc --version
```

Save this output — it's your baseline.

### Phase 2: Install Prerequisites

**Node.js (for Claude Code) — use nvm:**
```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
# Close and reopen terminal, then:
nvm install 22
```

**Claude Code:**
```bash
npm install -g @anthropic-ai/claude-code
claude --version
claude   # This will prompt for authentication
```

### Phase 3: Clone the Project

```bash
cd ~
git clone https://github.com/strulovitz/HoneycombOfAI.git
cd ~/HoneycombOfAI
```

### Phase 4: Set Up Python Virtual Environment

```bash
python3 -m venv ~/honeycomb-venv
source ~/honeycomb-venv/bin/activate
cd ~/HoneycombOfAI
pip install -r requirements.txt
```

### Phase 5: Install AI Backends

**Ollama:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llama3.2:3b
```

**llama.cpp (build from source):**
```bash
# First check if cmake is installed:
cmake --version
# If not: sudo apt install -y cmake

# Check for build tools:
gcc --version
# If not: sudo apt install -y build-essential

cd ~
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp

# If the Desktop has an NVIDIA GPU with CUDA:
cmake -B build -DGGML_CUDA=ON
# If NO NVIDIA GPU or no CUDA:
cmake -B build

cmake --build build --config Release -j$(nproc)
```

**Download a GGUF model:**
```bash
source ~/honeycomb-venv/bin/activate
pip install huggingface-hub
mkdir -p ~/models
huggingface-cli download Qwen/Qwen2.5-3B-Instruct-GGUF \
  qwen2.5-3b-instruct-q4_k_m.gguf --local-dir ~/models
```

**llama-cpp-python:**
```bash
source ~/honeycomb-venv/bin/activate
# With CUDA (if NVIDIA GPU):
CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python
# Without CUDA:
pip install llama-cpp-python
```

**vLLM (only if NVIDIA GPU with CUDA):**
```bash
source ~/honeycomb-venv/bin/activate
pip install vllm
```

**LM Studio:**
- Download from https://lmstudio.ai
- Install and load a model
- On Linux: Developer tab > Start Server

### Phase 6: Test All Backends

```bash
source ~/honeycomb-venv/bin/activate
cd ~/HoneycombOfAI
python -c "from backend_detector import detect_backends, display_detected_backends; display_detected_backends(detect_backends())"
```

### Phase 7: Configure for Cross-Machine Test

For the Linux-to-Linux test between Laptop and Desktop:
- One machine runs as Queen (`mode: queen` in config.yaml)
- The other runs as Worker (`mode: worker` in config.yaml)
- Both need to be on the same network

---

## CRITICAL WARNING: GPU/CUDA Is Fragile on Linux

Same rules as the Laptop Debian setup:

1. **NEVER** run `sudo apt upgrade` without checking
2. **NEVER** update NVIDIA drivers or CUDA once working
3. Before `apt install`, always `--dry-run` first
4. Use Python venvs for everything
5. Run `nvidia-smi` after every installation
6. See `DESKTOP_TASK_DEBIAN_SETUP.md` for the full warning

---

## After Setup Is Complete

Once everything is working on Desktop Linux Mint:
1. Run `demo_real.py` on Desktop Linux Mint (standalone test)
2. Run cross-machine test: Laptop Debian = Queen, Desktop Linux Mint = Worker (or vice versa)
3. This validates that HoneycombOfAI works in a full Linux environment, not just Windows
