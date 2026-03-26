# Briefing: Guide Nir Through macOS VM Setup on the Laptop

**From:** Desktop Windows Claude Code (Opus 4.6)
**To:** Laptop Windows Claude Code
**Date:** 2026-03-26
**Priority:** HIGH — Guide Nir step by step, patiently, one step at a time

---

## What Is Happening

Nir is setting up macOS Sequoia virtual machines on BOTH his physical machines (Desktop and Laptop) to test the BeehiveOfAI distributed AI platform on Mac. The Desktop macOS VM is already fully set up and working. Now YOU need to guide Nir through doing the same on the Laptop.

Nir CANNOT copy-paste inside the macOS VM (VMware limitation), so he has to type everything manually. Be patient. Give him one step at a time. Do NOT dump 10 commands on him at once.

---

## What Is Already Done on the Laptop

- VMware Workstation 16 is already installed on the Laptop's Windows 11
- macOS Sequoia is already installed as a VM guest inside VMware
- The VM network adapter has been changed from NAT to **Bridged** mode, bridged to "Intel(R) Ethernet Controller I226-V"
- "Replicate physical network connection state" is OFF
- The macOS VM has IP **10.0.0.9** on the home LAN
- Ping from Desktop macOS VM (10.0.0.7) to Laptop macOS VM (10.0.0.9) confirmed working, 0% packet loss

---

## What YOU Need to Guide Nir Through (Step by Step)

Guide Nir through these steps ON THE LAPTOP's macOS VM. Give him ONE step at a time, wait for confirmation, then give the next step.

### Phase 1: Install Ollama

**Step 1:** Tell Nir to open the macOS VM in VMware (if not already running).

**Step 2:** Tell Nir to open Safari inside the macOS VM and go to: **ollama.com/download/mac**

**Step 3:** Tell Nir to download the .dmg file, open it, and drag Ollama to the Applications folder.

**Step 4:** Tell Nir to launch Ollama from Applications. It will appear as a small icon in the menu bar at the top of the screen.

**Step 5:** Tell Nir to open Terminal. He can find it by pressing Cmd+Space (Spotlight) and typing "Terminal", then pressing Enter.

**Step 6:** Tell Nir to type in Terminal:
```
ollama pull llama3.2:3b
```
This downloads the AI model (~2GB). Wait for it to finish.

**Step 7:** Tell Nir to test it:
```
ollama run llama3.2:3b
```
Have him type "hello" to verify it responds. Then type `/bye` to exit.

### Phase 2: Install Claude Code

**Step 8:** Tell Nir to type in Terminal:
```
curl -fsSL https://claude.ai/install.sh | sh
```
Wait for it to finish.

**Step 9:** IMPORTANT — After installation, it will say that ~/.local/bin is not in the PATH. Tell Nir to type:
```
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
```

**Step 10:** Tell Nir to type:
```
claude
```
It will ask about visual bell / option+Enter for newlines — tell him to press Yes/Enable.

**Step 11:** Claude Code will open Safari for authentication. Tell Nir to log in with his Anthropic account (MAX subscription). It will authorize automatically via claude.ai.

**Step 12:** Once Claude Code is running and authenticated, tell Nir to type this prompt into the macOS Claude Code:

```
Please read https://raw.githubusercontent.com/strulovitz/HoneycombOfAI/main/BRIEFING_MACOS_SETUP.md and follow all the steps in order. Do everything yourself using your tools - do not ask me to type commands.
```

This will make the macOS Claude Code read the detailed setup briefing and do everything else automatically (install Python, clone repos, set up virtual environments, install dependencies, test Ollama API, configure HoneycombOfAI, test the GUI and CLI).

### Phase 3: Verify

**Step 13:** After the macOS Claude Code finishes the setup, ask Nir to confirm:
- Can he run `python gui_main.py` in ~/HoneycombOfAI and see the GUI?
- Does `python honeycomb.py --mode worker` start without errors?
- Is the IP still 10.0.0.9? (check in System Settings > Network)

---

## Network Architecture (For Your Reference)

```
Desktop Windows 11 (host) — 10.0.0.4
  └── macOS Sequoia VM — 10.0.0.7 (bridged, working)

Laptop Windows 11 (host) — IP varies
  └── macOS Sequoia VM — 10.0.0.9 (bridged, working)

Router: 10.0.0.138
Subnet: 255.255.255.0
All machines on same LAN.
```

## Other macOS VMs on the Network

The Desktop macOS VM (10.0.0.7) is already fully set up:
- Ollama installed with llama3.2:3b
- Claude Code installed and authenticated
- Python 3 installed
- Both repos cloned (HoneycombOfAI, BeehiveOfAI)
- Virtual environments created with all dependencies
- GUI tested and working

## The Goal

Once BOTH macOS VMs are set up, Nir will run a cross-machine distributed AI test:
- macOS VM on Desktop (10.0.0.7): BeehiveOfAI website + one role (Queen or Worker)
- macOS VM on Laptop (10.0.0.9): another role (Worker or Queen)
- A beekeeper submits a job, the system distributes and processes it across two Macs
- Results go into Chapter 8 of the book ("The Proof: We Actually Did It")

## Important Reminders

- Nir cannot copy-paste in the macOS VM. Be patient. One step at a time.
- There is NO GPU in VMware macOS VMs. Ollama runs CPU-only. Tasks will be slow (30-60 seconds) but functional.
- If Nir asks what something means, explain it simply — he is not a deep coder but understands concepts well.
- Always show user-friendly error messages, not raw exceptions.
- The macOS Claude Code briefing is at: https://raw.githubusercontent.com/strulovitz/HoneycombOfAI/main/BRIEFING_MACOS_SETUP.md
