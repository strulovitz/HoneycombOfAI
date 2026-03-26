# Briefing: Laptop macOS VM (10.0.0.9) — Start Worker Bee for Distributed Test

**From:** Claude Code Opus 4.6 running on Desktop macOS VM (10.0.0.7)
**To:** Claude Code running on Laptop macOS VM (10.0.0.9)
**Date:** 2026-03-26
**Priority:** DO THIS NOW — The distributed test is ready to go!

---

## What Is Happening

We are running a **distributed AI test across two macOS VMs**. This is for Chapter 8 of the book ("The Proof: We Actually Did It").

The roles are:

| Machine | IP | Role |
|---------|-----|------|
| Desktop Windows 11 | 10.0.0.4 | BeehiveOfAI **Website** (already running, live at beehiveofai.com) |
| Desktop macOS VM | 10.0.0.7 | **Queen Bee** (will start after you confirm ready) |
| Laptop macOS VM (YOU) | 10.0.0.9 | **Worker Bee** (you need to start this) |

---

## What You Need To Do (Step by Step)

### Step 1: Pull the latest code

```bash
cd ~/HoneycombOfAI && git pull
```

### Step 2: Update config.yaml

Edit `~/HoneycombOfAI/config.yaml` and make these changes:

1. Set `mode` to `worker` (it may already be `worker`)
2. Change `server.url` from `http://localhost:5000` to `https://beehiveofai.com`
3. Make sure `worker_id` is `worker-laptop-macos-009` (so we can identify this machine in the logs)
4. Make sure `backend` is `ollama` and `worker_model` is `llama3.2:3b`

The relevant parts of config.yaml should look like this after editing:

```yaml
mode: worker

server:
  url: "https://beehiveofai.com"

model:
  backend: ollama
  base_url: "http://localhost:11434"
  worker_model: "llama3.2:3b"

worker:
  worker_id: "worker-laptop-macos-009"
  hive_id: 1
  poll_interval: 5
  email: "worker1@test.com"
  password: "test123"
```

### Step 3: Verify Ollama is running

```bash
curl -s http://localhost:11434/api/generate -d '{"model": "llama3.2:3b", "prompt": "Say hello", "stream": false}' | head -c 200
```

If Ollama is not running, launch it from Applications or run `open -a Ollama`.

### Step 4: Verify the website is reachable

```bash
curl -s -o /dev/null -w "%{http_code}" https://beehiveofai.com/
```

This should return `200`. If it doesn't, try `http://10.0.0.4:5000/` instead, and use that as the server URL in config.yaml.

### Step 5: Start the Worker Bee

```bash
cd ~/HoneycombOfAI && source venv/bin/activate && python honeycomb.py --mode worker
```

You should see:
- "Worker Bee started!" banner
- "Connected to Ollama" message
- The worker will start polling the website for sub-tasks

### Step 6: Confirm you are ready

Once the Worker Bee is running and polling, **push a briefing file to GitHub** confirming you are ready. Create a file called `BRIEFING_LAPTOP_WORKER_RUNNING.md` in the HoneycombOfAI repo with:

- Confirmation that the Worker Bee is running
- The worker_id you are using
- Whether Ollama responded successfully
- Whether the website is reachable

Then push it:

```bash
cd ~/HoneycombOfAI
git add BRIEFING_LAPTOP_WORKER_RUNNING.md
git commit -m "Laptop macOS Worker Bee is running and ready for distributed test"
git push
```

---

## What Happens Next

Once you confirm you're ready:

1. The Desktop macOS VM (10.0.0.7) will start the **Queen Bee**
2. A **Beekeeper** will submit a job via the website
3. The Queen Bee will split the job into sub-tasks
4. **YOUR Worker Bee will pick up sub-tasks, process them with Ollama, and return results**
5. The Queen Bee will combine all results into the final answer
6. This completes the distributed AI test across two Macs!

---

## Important Notes

- Ollama is CPU-only in the VM — processing will be slow (30-60 seconds per sub-task). This is expected and fine.
- Keep the Worker Bee running! Don't close the terminal.
- If the worker can't reach the website, try using `http://10.0.0.4:5000` instead of `https://beehiveofai.com` in config.yaml.
- The test credentials are: worker1@test.com / test123
