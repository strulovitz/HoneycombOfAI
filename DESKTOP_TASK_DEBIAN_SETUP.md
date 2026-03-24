# Task for Desktop Claude Code: Guide Nir Through Debian Setup

**From:** Laptop Claude Code (Opus 4.6, nir-laptop)
**To:** Desktop Claude Code (Opus 4.6, nir-desktop)
**Date:** 2026-03-24
**Priority:** Needed before vLLM can be installed on Debian

---

## The Situation

When Nir reboots the Laptop into Debian 13, he will NOT have Claude Code there yet. He will come to YOU (Desktop) for help installing everything on Debian. Once Claude Code is running on Debian, Laptop Claude Code takes over for the vLLM and project-specific work.

**Your job: Guide Nir step-by-step through the complete Debian setup, from scratch, until Claude Code is running successfully on Debian 13.**

Nir is a beginner — he needs every step spelled out clearly. Don't assume he knows Linux commands.

---

## What Nir Will Have on Debian

- **Debian 13 (Trixie)** — installed, bootable, desktop environment working
- **NVIDIA RTX 5090** with 24GB VRAM
- **Internet connection** — working
- **A terminal** — he can open one
- We do NOT know yet what's pre-installed (Python version, Node.js, NVIDIA drivers, CUDA, etc.)

---

## What You Need to Help Install (in order)

### Step 1: Verify Basics
Help Nir open a terminal and check what's already installed:
```bash
python3 --version          # Need Python 3.10+
node --version             # Need Node.js 18+
npm --version              # Comes with Node.js
git --version              # Need git
nvidia-smi                 # Check if NVIDIA drivers are installed
nvcc --version             # Check if CUDA toolkit is installed
```

### Step 2: Install Missing Prerequisites
Based on what's missing from Step 1, guide installation of:

**Python 3.10+ (if missing):**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

**Node.js 18+ (required for Claude Code):**
```bash
# Use NodeSource to get a modern version
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs
```

**Git (if missing):**
```bash
sudo apt install git
```

**NVIDIA Drivers (if nvidia-smi fails):**
This is the trickiest part on Debian. Options:
```bash
# Option A: Non-free Debian packages
sudo apt install nvidia-driver firmware-misc-nonfree
# Reboot after this

# Option B: If that doesn't have RTX 5090 support, may need
# the official NVIDIA .run installer from nvidia.com
```

**CUDA Toolkit (if nvcc fails):**
```bash
# After NVIDIA drivers are working:
sudo apt install nvidia-cuda-toolkit
# Or install from NVIDIA's official repo for newer CUDA
```

### Step 3: Install Claude Code
```bash
npm install -g @anthropic-ai/claude-code
```

Then Nir needs to authenticate:
```bash
claude
# This will open a browser for Anthropic login
# Or Nir can set ANTHROPIC_API_KEY environment variable
```

### Step 4: Verify Claude Code Works
```bash
claude --version
claude "Hello, are you working?"
```

### Step 5: Clone/Pull the Project
```bash
cd ~
git clone https://github.com/strulovitz/HoneycombOfAI.git
# Or if already cloned:
cd ~/HoneycombOfAI && git pull
```

### Step 6: Set Up Python Environment
```bash
cd ~/HoneycombOfAI
pip3 install -r requirements.txt
```

### Step 7: Hand Off to Laptop Claude Code
At this point, Nir can open Claude Code inside the project:
```bash
cd ~/HoneycombOfAI
claude
```

And Laptop Claude Code (on Debian) takes over for:
- Installing vLLM
- Installing Ollama on Debian (if desired)
- Testing all backends
- Any project-specific work

---

## Important Notes

- **Nir is a beginner** — explain every step, what it does, and what to expect
- **NVIDIA driver installation on Debian can be tricky** — especially for the very new RTX 5090. You may need to check which driver version supports it.
- **The RTX 5090 needs driver version 570+ or possibly newer** — Debian 13 may or may not have this in its repos yet. Be prepared to guide through the official NVIDIA installer if needed.
- **Suggest improvements, don't implement automatically** — discuss with Nir before each major step
- **If something goes wrong**, don't panic. Help Nir troubleshoot step by step.

---

## After Desktop's Job Is Done

Once Claude Code is running on Debian, Nir will use it directly on the Laptop (in Debian) for:
1. Installing vLLM (`pip install vllm`)
2. Downloading a model and starting vLLM server
3. Testing the HoneycombOfAI multi-backend system with vLLM
4. Pushing results to GitHub

You (Desktop) can go back to your regular duties (website server, etc.).

---

Thank you Desktop! This is a critical handoff step. 🐝
