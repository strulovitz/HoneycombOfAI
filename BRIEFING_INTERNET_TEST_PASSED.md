# Briefing: Full Internet Test PASSED — 2026-03-25

**From:** Desktop Claude Code (Opus 4.6, Linux Mint 22.2)
**To:** ALL Claude Code instances (Laptop Debian, Laptop Windows, Desktop Windows, any future instance)
**Date:** 2026-03-25
**Priority:** MAJOR MILESTONE — Read this before doing any work on the project

---

## What Happened Today (2026-03-25)

The Desktop computer was set up on Linux Mint 22.2 and two major tests were completed:

### Test 1: Linux LAN Test (14:11 — PASSED)
- Desktop Linux Mint = Worker Bee + Website (on LAN at 10.0.0.4:5000)
- Laptop Debian 13 = Queen Bee
- Job #3: Geothermal energy analysis
- Queen split → Worker processed 2 subtasks (2647 + 3639 chars) → Queen combined → Complete
- Pipeline time: ~64 seconds

### Test 2: Full Internet Test (14:50 — PASSED)
- Website served to **the real internet** via Cloudflare Tunnel at https://beehiveofai.com
- **Real Twilio SMS** sent to Nir's phone for verification — code received and entered successfully
- Desktop Linux Mint = Worker Bee + Website + Cloudflare Tunnel
- Laptop Debian 13 = Queen Bee (connected via https://beehiveofai.com, NOT LAN IP)
- Job #4: Pros and cons of AI in space
- Queen split → Worker processed 2 subtasks → Queen combined → Complete
- Pipeline time: **~27 seconds**
- Beekeeper rated the job ✅

---

## What Was Set Up on Desktop Linux Mint 22.2

### Software Installed
- GitHub CLI (`gh`) — authenticated as strulovitz
- Python 3.12.3 with two virtual environments:
  - `~/beehive-venv` — for BeehiveOfAI website (Flask + all dependencies)
  - `~/honeycomb-venv` — for HoneycombOfAI client (requests, pyyaml, rich, ollama)
- Ollama — running as systemd service with `llama3.2:3b` model
- Cloudflare Tunnel (`cloudflared`) — tunnel `beehive-linux` serving beehiveofai.com
- cmake, gcc, build-essential — ready for future builds

### Hardware
- GPU: NVIDIA GeForce RTX 4070 Ti (12GB VRAM)
- Driver: 580.126.09, CUDA: 13.0
- LAN IP: 10.0.0.4

### How to Start Everything on Desktop Linux Mint

**Terminal 1 — Website (with Twilio SMS):**
```bash
export TWILIO_ACCOUNT_SID=<from .env file>
export TWILIO_AUTH_TOKEN=<from .env file>
export TWILIO_VERIFY_SERVICE_SID=<from .env file>
source ~/beehive-venv/bin/activate
cd ~/BeehiveOfAI
python app.py
```

**Terminal 2 — Cloudflare Tunnel:**
```bash
cloudflared tunnel run beehive-linux
```

**Terminal 3 — Worker Bee:**
```bash
source ~/honeycomb-venv/bin/activate
cd ~/HoneycombOfAI
python honeycomb.py
```

### Cloudflare Tunnel Details
- Tunnel name: `beehive-linux`
- Tunnel ID: 96467138-c2c4-4caa-9885-bc976b48a97c
- Config: `/home/nir/.cloudflared/config.yml`
- Credentials: `/home/nir/.cloudflared/96467138-c2c4-4caa-9885-bc976b48a97c.json`
- DNS: beehiveofai.com → beehive-linux tunnel
- Note: The old Windows tunnel (`beehive`, ID 18a52f43) still exists but DNS now points to the Linux tunnel. When switching back to Windows, DNS must be re-routed: `cloudflared tunnel route dns --overwrite-dns beehive beehiveofai.com`

### Twilio SMS
- Credentials stored in `~/BeehiveOfAI/.env` (NOT in git)
- Three env vars: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_VERIFY_SERVICE_SID
- Must be exported before starting the website for real SMS to work
- Without env vars, falls back to test mode (prints codes to console)

---

## Current Config State

**HoneycombOfAI config.yaml** is set for the Linux cross-machine test:
- `mode: worker`
- `server.url: http://10.0.0.4:5000` (LAN — change to https://beehiveofai.com for internet test)
- `backend: ollama`
- `worker_model: llama3.2:3b`
- `worker_id: worker-desktop-mint-001`

---

## Test History Summary

| Date | Test | OS | Result |
|------|------|-----|--------|
| 2026-03-22 | First two-machine LAN test | Windows + Windows | PASS |
| 2026-03-22 | Cloudflare Tunnel internet test | Windows | PASS |
| 2026-03-22 | Mobile phone verification (off-wifi) | Windows | PASS |
| 2026-03-25 | Linux LAN test | Linux Mint + Debian | PASS |
| 2026-03-25 | **Full internet test (Cloudflare + Twilio SMS)** | **Linux Mint + Debian** | **PASS** |

---

## CRITICAL WARNINGS (unchanged)

1. **NEVER** run `sudo apt upgrade` on any Linux machine with NVIDIA GPU
2. **NEVER** update NVIDIA drivers or CUDA once working
3. Twilio credentials are in `.env` — never commit to git
4. Cloudflare credentials are in `~/.cloudflared/` — never share the JSON file
5. The `beehive-linux` tunnel DNS overrode the `beehive` (Windows) tunnel. Only one can serve beehiveofai.com at a time.

---

## What's Next

- GUI development for HoneycombOfAI (native desktop app)
- More AI backends on Desktop Linux Mint (llama.cpp, vLLM, LM Studio)
- Production hardening (Waitress instead of Flask dev server for Linux)
- Cross-internet test with machines on different networks (not just same LAN)
