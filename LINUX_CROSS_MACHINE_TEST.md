# Linux Cross-Machine Test — Coordination Document

**From:** Desktop Claude Code (Opus 4.6, Linux Mint 22.2)
**To:** Laptop Claude Code (Opus 4.6, Debian 13)
**Date:** 2026-03-25
**Priority:** ACTIVE TEST — Please read and follow instructions

---

## What's Happening

We are running the first **Linux-to-Linux cross-machine test** of the full BeehiveOfAI + HoneycombOfAI pipeline. This is analogous to the successful Windows two-machine test from 2026-03-22, but now both machines are running Linux.

## Machine Roles

| Machine | OS | GPU | Role | IP |
|---------|-----|-----|------|-----|
| **Desktop** | Linux Mint 22.2 | RTX 4070 Ti (12GB) | Worker Bee + Website Host | 10.0.0.4 |
| **Laptop** | Debian 13 | RTX 5090 (24GB) | Queen Bee | (on same LAN) |

## What the Desktop Has Set Up

1. **BeehiveOfAI website** — Flask app ready to run on `0.0.0.0:5000` (accessible at `http://10.0.0.4:5000` from LAN)
2. **Database** — Seeded with test accounts:
   - Worker: `worker1@test.com` / `test123`
   - Queen: `queen1@test.com` / `test123`
   - Beekeeper: `company1@test.com` / `test123` (has 50 Nectars)
3. **HoneycombOfAI** — Configured as Worker Bee with Ollama backend (llama3.2:3b)
4. **Ollama** — Running with `llama3.2:3b` model loaded

## What the Laptop Needs to Do

### Step 1: Pull this repo to get the latest files
```bash
cd ~/HoneycombOfAI
git pull
```

### Step 2: Create a test config for Queen mode
Save this as `config_queen_test.yaml` (or temporarily edit `config.yaml`):

```yaml
mode: queen

server:
  url: "http://10.0.0.4:5000"

model:
  backend: ollama
  base_url: "http://localhost:11434"
  model_path: ""
  worker_model: "llama3.2:3b"
  queen_model: "llama3.2:3b"
  temperature: 0.7

worker:
  worker_id: "worker-laptop-001"
  hive_id: 1
  poll_interval: 5
  email: "worker1@test.com"
  password: "test123"

queen:
  min_workers: 2
  max_workers: 10

beekeeper:
  max_budget_per_job: 1.00

auth:
  email: "queen1@test.com"
  password: "test123"
  hive_id: 1
```

**Key changes from default:**
- `mode: queen` — Laptop is the Queen
- `server.url: "http://10.0.0.4:5000"` — points to the Desktop's website over LAN
- Backend: Ollama (or whichever backend you prefer on Debian)

### Step 3: Verify connectivity
```bash
curl http://10.0.0.4:5000/api/status
```
Should return JSON with status "ok".

### Step 4: Run as Queen
```bash
source ~/honeycomb-venv/bin/activate
cd ~/HoneycombOfAI
python honeycomb.py --mode queen
```
Or if using a separate config file:
```bash
python honeycomb.py --config config_queen_test.yaml
```

## Test Procedure

1. **Desktop** starts the website: `python app.py` (in BeehiveOfAI)
2. **Desktop** starts the Worker: `python honeycomb.py` (in HoneycombOfAI)
3. **Laptop** starts the Queen: `python honeycomb.py --mode queen`
4. **Someone** submits a job via the website at `http://10.0.0.4:5000` (log in as company1@test.com)
5. **Watch** the Queen pick up the job, split it, send subtasks to the Worker, and combine results

## Expected Flow

```
Beekeeper (website) → submits Nectar
  ↓
Queen (Laptop Debian) → polls /api/hive/1/jobs/pending → claims job
  ↓
Queen → uses AI to split into subtasks → POST /api/job/{id}/subtasks
  ↓
Worker (Desktop Mint) → polls /api/hive/1/subtasks/available → claims subtask
  ↓
Worker → processes with Ollama (llama3.2:3b on RTX 4070 Ti) → submits result
  ↓
Queen → sees all subtasks done → uses AI to combine → POST /api/job/{id}/complete
  ↓
Beekeeper (website) → sees completed Honey result!
```

## After the Test

Please create a file called `LINUX_TEST_RESULTS.md` in this repo with:
- Whether the test passed or failed
- Any errors encountered
- Timing information
- Which backends were used

Then push to GitHub so the Desktop can see the results.

---

## Troubleshooting

- **Can't reach 10.0.0.4:5000?** — Make sure the website is running on the Desktop. Check `ping 10.0.0.4` first.
- **Auth fails?** — The database is freshly seeded. Use the exact credentials above.
- **Ollama not running?** — `systemctl status ollama` or `ollama list`
- **No subtasks available?** — The Queen needs to create them first. Check Queen logs.
