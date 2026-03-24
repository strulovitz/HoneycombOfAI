# 🍯 Honeycomb Of AI

**The Distributed AI Software — WorkerBee, QueenBee, and Beekeeper Modules**

---

## What Is This?

Honeycomb Of AI is the software you install on your computer to participate in the [Beehive Of AI](https://github.com/strulovitz/BeehiveOfAI) network — a distributed AI computing platform where home computers work together to process AI tasks for companies.

Run this software on your machine and you instantly become part of the hive.

---

## The Three Modules

Honeycomb Of AI contains three modules in a single program. You choose which role to run:

### 💻 WorkerBeeModule
For home computer owners who want to earn money by sharing their AI processing power.
- Receives sub-tasks from a Queen Bee
- Processes them using your local AI model (Ollama, LM Studio, etc.)
- Returns results and earns micro-payments automatically

### 👑 QueenBeeModule
For experienced users who want to manage a team (Hive) and earn more.
- Accepts full AI tasks from Beekeepers
- Splits them into sub-tasks and distributes to Worker Bees
- Combines all results into a polished final answer
- Earns a coordination fee on top of processing fees

### 🏢 BeekeeperModule
For companies and developers who need affordable AI processing.
- Submits AI tasks (Nectars) to a Hive
- Monitors job progress in real time
- Receives the final combined answer (Honey)
- Pays per token processed — far cheaper than cloud AI

---

## Supported AI Backends

Works with any of the popular local AI runners:

| Backend | Notes |
|---------|-------|
| **Ollama** | Recommended — easiest setup |
| **LM Studio** | Great GUI for beginners. **Linux users:** you must manually start the local server in LM Studio's Developer tab (Windows does this automatically) |
| **llama.cpp** | Lowest resource usage |
| **vLLM** | Best for high-throughput servers |

---

## Quick Demo (No AI Required)

Want to see how it works without installing any AI model?

```bash
python demo.py
```

This runs a complete simulated workflow: Beekeeper → Queen Bee → 3 Worker Bees → combined result — all locally, no network or AI required.

---

## Installation

> Coming soon — full installation instructions will be published in Phase 2.

**Requirements (planned):**
- Python 3.10+
- [Ollama](https://ollama.ai) (or another supported AI backend)
- At least one model installed: `ollama pull llama3.2:3b`

```bash
git clone https://github.com/strulovitz/HoneycombOfAI.git
cd HoneycombOfAI
pip install -r requirements.txt
# Edit config.yaml to set your mode and model
python honeycomb.py
```

---

## Usage

```bash
# Start as a Worker Bee (default if config.yaml says mode: worker)
python honeycomb.py

# Override mode from command line
python honeycomb.py --mode worker
python honeycomb.py --mode queen
python honeycomb.py --mode beekeeper
```

---

## Configuration

Edit `config.yaml` to set your mode, AI backend, and model. Full documentation coming in Phase 2.

---

## License

MIT License — see [LICENSE](LICENSE) for details.
