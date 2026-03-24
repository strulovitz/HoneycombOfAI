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

## CRITICAL WARNING: THE DEBIAN SETUP IS EXTREMELY FRAGILE

**READ THIS BEFORE DOING ANYTHING ON DEBIAN.**

The RTX 5090 uses NVIDIA's new **Blackwell architecture** — NOT the same as RTX 4090 (Ada Lovelace). Debian 13 support for it is bleeding-edge. Nir spent **multiple full days** with Claude getting CUDA and the GPU drivers working correctly on Debian. The current setup works, but it is very sensitive to version changes.

**Even routine OS updates (`apt upgrade`) have broken the GPU stack in the past.**

### Rules You MUST Follow:

1. **NEVER run `sudo apt upgrade` or `sudo apt dist-upgrade`** — this can pull in new kernel or driver versions that break CUDA
2. **NEVER update NVIDIA drivers, CUDA, or cuDNN** unless there is absolutely no other choice
3. **NEVER run `sudo apt install` for something that wants to upgrade or remove CUDA-related packages** — if apt shows it wants to remove or upgrade anything CUDA/NVIDIA-related, STOP immediately and tell Nir
4. **Pin all Python package versions** — always use `pip install package==x.y.z`, never just `pip install package`
5. **Use a Python virtual environment** for the HoneycombOfAI project — this isolates project packages from system packages:
   ```bash
   python3 -m venv ~/honeycomb-venv
   source ~/honeycomb-venv/bin/activate
   ```
6. **Use `pip install --no-deps` when possible** to avoid pip pulling in unwanted dependency upgrades
7. **Run `nvidia-smi` AFTER every installation** to verify the GPU stack is still working
8. **Before running any `apt install`**, first run it with `--dry-run` to see what it wants to change:
   ```bash
   sudo apt install --dry-run <package-name>
   # Read the output carefully — if it removes or upgrades CUDA/NVIDIA packages, DO NOT proceed
   ```
9. **For Node.js**: prefer using `nvm` (Node Version Manager) or a standalone binary rather than apt, to avoid any risk of apt touching system packages:
   ```bash
   curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
   source ~/.bashrc
   nvm install 22
   ```

### What to Check First (Before Installing Anything):

Run these commands and **save the output** — this is your "known good" baseline:
```bash
nvidia-smi                           # GPU driver version + CUDA version
nvcc --version                       # CUDA compiler version
dpkg -l | grep -i nvidia | head -20  # All installed NVIDIA packages + versions
dpkg -l | grep -i cuda | head -20    # All installed CUDA packages + versions
python3 --version                    # Python version
pip3 list | grep -i -E "torch|cuda|nvidia"  # Any GPU-related Python packages
```

**If any of these look wrong or nvidia-smi fails, DO NOT install anything else. Troubleshoot the GPU stack first.**

### Revised Step 6: Set Up Python Environment (USE VENV!)

```bash
# Create an isolated virtual environment
python3 -m venv ~/honeycomb-venv
source ~/honeycomb-venv/bin/activate

# Now install project dependencies inside the venv
cd ~/HoneycombOfAI
pip install -r requirements.txt
```

This way, our project packages cannot interfere with system-level CUDA packages.

---

## Important Notes

- **Nir is a beginner** — explain every step, what it does, and what to expect
- **NVIDIA drivers and CUDA are ALREADY installed and working** — Nir confirmed this. DO NOT reinstall them. Only verify they still work.
- **The whole point of Step 1 is verification, not installation** — check that everything is still intact after the last boot
- **Suggest improvements, don't implement automatically** — discuss with Nir before each major step
- **If something goes wrong**, don't panic. Help Nir troubleshoot step by step. But NEVER try to fix CUDA problems by upgrading packages.

---

## After Desktop's Job Is Done

Once Claude Code is running on Debian, Nir will use it directly on the Laptop (in Debian) for:
1. Installing vLLM (`pip install vllm` — inside the venv, with pinned versions)
2. Downloading a model and starting vLLM server
3. Testing the HoneycombOfAI multi-backend system with vLLM
4. Pushing results to GitHub

**Pass along the fragile-setup warning to Laptop Claude Code on Debian** — make sure it knows about all these rules too. This information must survive the handoff.

You (Desktop) can go back to your regular duties (website server, etc.).

---

Thank you Desktop! This is a critical handoff step — and protecting the Debian GPU stack is the #1 priority. 🐝
