# Briefing: macOS Sequoia VM Setup for BeehiveOfAI Testing

**From:** Desktop Windows Claude Code (Opus 4.6)
**To:** Claude Code running on macOS Sequoia VM (Desktop or Laptop)
**Date:** 2026-03-26
**Priority:** FOLLOW THESE STEPS IN ORDER

---

## Context

You are running on a macOS Sequoia virtual machine (VMware Workstation 16 guest, Windows 11 host). This macOS VM is being used to test the BeehiveOfAI distributed AI platform on Mac.

There are TWO macOS VMs:
- **Desktop macOS VM** — IP: 10.0.0.7
- **Laptop macOS VM** — IP: 10.0.0.9

Both are on the same LAN (subnet 255.255.255.0, router 10.0.0.138). Ping between them confirmed working.

Ollama is already installed and working. The model llama3.2:3b has been pulled.

There is **NO GPU** in these VMs — Ollama runs CPU-only. This is expected and fine.

The GitHub repos are:
- https://github.com/strulovitz/BeehiveOfAI (the website/marketplace)
- https://github.com/strulovitz/HoneycombOfAI (the desktop client)
- https://github.com/strulovitz/TheDistributedAIRevolution (the book)

The user is Nir (GitHub: strulovitz). He has a Claude MAX subscription.

---

## Steps to Complete (do these in order)

### Step 1: Check/Install Python 3

macOS Sequoia may have Python 3 pre-installed. Check:

```bash
python3 --version
```

If NOT installed, install via Homebrew:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Then:

```bash
brew install python@3.12
```

If Homebrew is already installed, just do the `brew install python@3.12`.

### Step 2: Install Git (if needed)

Check if git is available:

```bash
git --version
```

macOS usually has git via Xcode Command Line Tools. If not:

```bash
xcode-select --install
```

### Step 3: Clone the repos

```bash
cd ~
git clone https://github.com/strulovitz/HoneycombOfAI.git
git clone https://github.com/strulovitz/BeehiveOfAI.git
```

### Step 4: Set up Python virtual environment for HoneycombOfAI

```bash
cd ~/HoneycombOfAI
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Note: PyQt6 should work on macOS. If it fails, try: `pip install PyQt6 --only-binary=:all:`

### Step 5: Set up Python virtual environment for BeehiveOfAI

```bash
cd ~/BeehiveOfAI
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 6: Test Ollama is working

```bash
curl http://localhost:11434/api/generate -d '{"model": "llama3.2:3b", "prompt": "Say hello in one sentence", "stream": false}'
```

Should return a JSON response with the AI's answer.

### Step 7: Configure HoneycombOfAI

Edit config.yaml in HoneycombOfAI to set:
- mode: worker (or queen, depending on the test)
- server: the BeehiveOfAI website address
- ai_backend: ollama
- model: llama3.2:3b

### Step 8: Test the GUI

```bash
cd ~/HoneycombOfAI
source venv/bin/activate
python gui_main.py
```

Verify the PyQt6 GUI opens and shows the three role cards (Worker Bee, Queen Bee, Beekeeper).

### Step 9: Test the CLI

```bash
cd ~/HoneycombOfAI
source venv/bin/activate
python honeycomb.py --mode worker
```

Verify it starts and tries to connect to the server.

---

## What Machine Am I?

If you are not sure which macOS VM you are running on, check your IP:

```bash
ifconfig en0 | grep "inet "
```

- If IP is **10.0.0.7** → you are the Desktop macOS VM
- If IP is **10.0.0.9** → you are the Laptop macOS VM

---

## Network Architecture

```
Desktop Windows 11 (host) — 10.0.0.4
  └── macOS Sequoia VM — 10.0.0.7 (bridged networking)

Laptop Windows 11 (host) — 10.0.0.?
  └── macOS Sequoia VM — 10.0.0.9 (bridged networking)

Router: 10.0.0.138
All on same LAN, all can talk to each other.
```

---

## Goal

The goal is to run BeehiveOfAI tests on macOS:
1. First, get both macOS VMs fully set up (Python, repos, dependencies)
2. Run BeehiveOfAI website on one Mac, Worker/Queen on the other
3. Complete a full distributed AI job across two macOS machines
4. Test the PyQt6 GUI on macOS
5. Results will be added to Chapter 8 of the book ("The Proof: We Actually Did It")

---

## Important Notes

- No GPU — Ollama runs CPU-only. Tasks will be slow but functional.
- User (Nir) cannot easily copy-paste in VMware macOS. Run commands yourself via Bash tool when possible.
- Be patient with slow AI processing — CPU-only llama3.2:3b may take 30-60 seconds per task.
- If pip install fails for any package, try installing it individually and report what works.
- PyQt6 on macOS may need: `brew install qt@6` first if the pip install fails.
