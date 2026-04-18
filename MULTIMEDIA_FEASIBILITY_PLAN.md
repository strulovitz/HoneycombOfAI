# Multimedia Feasibility Plan — Text, Photo, Sound, Video Input Handling 🐝🎬🎙️🖼️

**Created:** 2026-04-18 by Laptop Linux Claude, after planning conversation with Nir.
**Repo home:** `HoneycombOfAI/MULTIMEDIA_FEASIBILITY_PLAN.md` (canonical — edit in place per Golden Rule 2).

---

## Mission 🎯

Add to the **BeehiveOfAI** (website) + **HoneycombOfAI** (client) system the ability to handle **input files** of four types:
1. **Text** — trivial, any hive already handles prompts. 📝
2. **Photo** (JPEG) 🖼️
3. **Sound** (MP3) 🎙️
4. **Video** (MP4) 🎬

All processing uses the **recursive sub-sampling principle** from *TheDistributedAIRevolution* chapters 12–15:
*Parent gets low-fidelity whole, workers get high-fidelity slices, text flows up, parent integrates tile-text onto her gestalt map.*

---

## Hard Constraints 🚨

- All work on **Laptop Linux Debian 13** HOST (RTX 5090, 24 GB VRAM).
- **GPU only** — not CPU, because we want fast results.
- **Ollama** for vision + text; **whisper.cpp (CUDA-built)** for audio. No other backends.
- **Golden Rule 8 (locked in 2026-04-18):** all new installs inside an isolated env (`conda`, `venv`, or `uv`). NEVER touch host CUDA / PyTorch / Python / wheels / NVIDIA. `--dry-run` before installs. `nvidia-smi` after.
- **Chapter 15 scope discipline** — do NOT test:
  - Vector mesh / RAG-over-reality (needs real drones + senses)
  - Simulated 3D/4D physical mapping
  - Single-value sensor gradient fields
  - 4-tier RajaBee hierarchy (Queen + Workers = 2 tiers is enough for this experiment)
- Report progress via **WaggleDance ICQ** to Desktop Windows — short, 2 sentences each: starting / done / stuck.
- Repos touched today: **ONLY** `HoneycombOfAI` (plan + code) and `BeehiveOfAI` (file-upload at Stage 4). No KillerBee, no GiantHoneyBee, no book repos, no BeeSting/MadHoney.

---

## Models (same as yesterday's VM build, now on host GPU) 🤖

Pulled to host Ollama yesterday during Phase 3. Reusing, not reinstalling.

| Tier   | Vision              | Audio (STT)                        | Text (Dense)                   |
|--------|---------------------|------------------------------------|--------------------------------|
| Queen  | `qwen3-vl:8b`       | `whisper large-v3-turbo` (809M)    | `phi4-mini:3.8b`               |
| Worker | `qwen3.5:0.8b`      | `whisper tiny` (39M)               | `qwen3:1.7b`                   |

Notes:
- Vision + text = Ollama. Audio = whisper.cpp (no STT in Ollama).
- Per slippery point #3 (Ch 15): Queen runs BIGGEST model her hardware affords; workers run smallest that fits their role. Not the reverse.
- 24 GB VRAM comfortably holds any one of these at a time, sequential load/unload.

---

## Stages 🪜

### Stage 0 — Isolated environment (must come first; Rule 8) 🔒

1. `mkdir -p ~/multimedia-feasibility && cd ~/multimedia-feasibility`
2. Create dedicated Python env: `python3 -m venv venv` (or `conda create -n multimedia-feasibility python=3.11` if conda is preferred).
3. Activate; install ONLY inside the env: `pillow`, `ffmpeg-python`, `numpy`, `ollama` (python client), `requests`. All pinned.
4. Clone whisper.cpp into `~/multimedia-feasibility/whisper.cpp`, build with CUDA (`cmake -B build -DGGML_CUDA=ON && cmake --build build -j`).
5. Download ggml models into `whisper.cpp/models/`: `ggml-large-v3-turbo-q5_0.bin`, `ggml-tiny.bin`.
6. Verify host still healthy: `nvidia-smi` (driver + GPU OK), `ollama list` (yesterday's models still present), `python3 --version` unchanged.
7. **ICQ:** `[STAGE 0 DONE] venv+whisper.cpp CUDA built at ~/multimedia-feasibility, host CUDA/Python/Ollama untouched. Ready for Stage 1.`

---

### Stage 1 — Direct feasibility (Ollama + Python, no bees) 🧪

Prove each modality works end-to-end on one file. One pass, one model, no hierarchy.

**Stage 1a — Photo** 🖼️
- Download 1 JPEG (rich scene with people + objects + text) from Pexels or Wikimedia Commons into `test_inputs/sample.jpg`.
- `stage1_photo.py`: read image, base64-encode, POST to Ollama `/api/generate` with `qwen3-vl:8b`.
- Print the returned description.
- **Pass criterion:** description mentions ≥3 items actually visible.
- **ICQ** starting → done (2 sentences: what it saw, wall time).

**Stage 1b — Sound** 🎙️
- Download 1 MP3 (speech + background, ~1–2 min) from Internet Archive or LibriVox into `test_inputs/sample.mp3`.
- `stage1_sound.py`: convert to 16 kHz WAV via ffmpeg, call whisper.cpp CUDA binary with `-m large-v3-turbo` and `-ngl 99`.
- Print transcription + wall time. Confirm GPU actually used (check `nvidia-smi` during run).
- **Pass criterion:** transcription is legible, wall time clearly faster than CPU.
- **ICQ** starting → done.

**Stage 1c — Video** 🎬
- Download 1 MP4 (30–120 sec, with sound) from Pexels or Mixkit into `test_inputs/sample.mp4`.
- `stage1_video.py`: use ffmpeg to split (a) audio track → WAV for whisper, (b) keyframes every 5 sec → JPEGs for vision.
- Run whisper on audio, Ollama vision on each keyframe. Output = transcription + per-timestamp visual summary.
- **Pass criterion:** output mentions things from both visual and audio streams.
- **ICQ** starting → done.

---

### Stage 2 — One bee (single process, full recursive sub-sampling) 🐝

Goal: one Python process (one "bee") runs the book's recursive trick end-to-end on one file, sequential load/unload. Matches Ch 15's "cheap-test-bench" configuration.

For **PHOTO**:
1. Make low-res whole (every 2nd pixel, both axes) → `qwen3-vl:8b` pass → **gestalt text**.
2. Cut full-res image with Chapter 12's **double-grid trick**: grid A at 0/50/100%, grid B offset at 25/75% → 8 tiles total (4 + 4).
3. Run vision model sequentially on each tile → 8 **tile descriptions**.
4. Integrate: final text = gestalt + tile descriptions placed onto gestalt layout.

For **SOUND**: same trick on 1D:
1. Low-sample-rate pass on whole recording → **temporal gestalt**.
2. Cut full-rate into 1-sec slices.
3. whisper on each slice → **slice transcriptions**.
4. Integrate: final text = gestalt + per-timestamp details.

For **VIDEO**: combine PHOTO trick per keyframe + SOUND trick on audio track, then stitch by timestamp.

- **ICQ** per modality (3 messages: starting → done, with 2-sentence summary).

---

### Stage 3 — Few bees (Queen + Workers, 2-tier hierarchy) 👑🐝🐝🐝🐝

Distribute Stage 2 across multiple processes on the same host to validate dispatch + integration across bees.

- 1 Queen process + 4 Worker processes (local, same host, separate Python interpreters).
- IPC: simple local HTTP (Flask) or UNIX sockets — intentionally lightweight. NOT KillerBee, NOT GiantHoneyBee, just a minimal test harness.
- Queen runs BIGGEST models (`qwen3-vl:8b`, `large-v3-turbo`, `phi4-mini:3.8b`). Workers run SMALLER models (`qwen3.5:0.8b`, `tiny`, `qwen3:1.7b`). Per slippery point #3.
- Queen: low-fidelity gestalt pass on whole input. Cuts full-res into tiles. Dispatches tiles to Workers (2 tiles per Worker for an 8-tile photo split).
- Workers: run their model on their tile, return text to Queen.
- Queen: integrates Workers' text onto her gestalt map, returns final description.
- All 3 modalities (photo, sound, video).
- **ICQ** per modality.

---

### Stage 4 — Integration into BeehiveOfAI website + HoneycombOfAI client 🌐

Production path — user uploads file on website, HoneycombOfAI Worker client picks it up, runs Stage-2 or Stage-3 code locally on GPU, result flows back to website.

- **BeehiveOfAI:** add a file-upload endpoint (accepts JPEG/MP3/MP4), store upload, mark task as `multimedia:<type>` in the existing polling API.
- **HoneycombOfAI Worker:** extend polling loop to recognize `multimedia:*` task types. When one arrives, run the matching multimedia handler (Stage 2 logic imported as a module), submit resulting text via existing submission API.
- **Test:** run BeehiveOfAI locally on Laptop Linux (Flask dev server), open browser, upload one JPEG, verify HoneycombOfAI Worker analyzes and the result appears back in the website. Same for MP3, same for MP4.
- **ICQ** per modality.

---

## Reporting protocol — WaggleDance ICQ to Desktop Windows 📡

ASCII only (no emojis) — the ICQ pipeline strips them and they break JSON.

Format:
- `[STAGE X STARTING] <short description>`
- `[STAGE X DONE] <two sentences: what happened, what's next>`
- `[STAGE X STUCK] <two sentences: what broke, where I am stuck>`

Command:
```bash
curl -s -X POST http://localhost:8765/send \
  -H "Content-Type: application/json" \
  -d '{"from": "laptop-claude", "type": "REPLY", "message": "[STAGE X ...]"}'
```

Use `type:"TASK"` only when Desktop Claude is expected to act. Everything else is `REPLY`.

---

## Files this plan creates 📂

Inside `~/multimedia-feasibility/` (outside any repo, host-local scratch):
- `venv/` — isolated Python env
- `whisper.cpp/` — CUDA-built binary + ggml models
- `test_inputs/` — the JPEG, MP3, MP4 test files
- `stage1_photo.py`, `stage1_sound.py`, `stage1_video.py`
- `stage2_one_bee.py`
- `stage3_queen_worker.py` + tiny local dispatch harness

Inside `HoneycombOfAI/` repo:
- `MULTIMEDIA_FEASIBILITY_PLAN.md` (this file)
- Stage 4 deliverable: multimedia handler module integrated into the existing Worker class.

Inside `BeehiveOfAI/` repo (Stage 4 only):
- File-upload endpoint + storage for uploads.
- Task-type extension in the existing polling API.

---

## Success Criteria ✅

- Each stage produces correct-looking text output for a real input file.
- Host CUDA / PyTorch / Python / wheels **untouched** (verified: `nvidia-smi` + `ollama list` unchanged before and after).
- All new deps live inside `~/multimedia-feasibility/venv` or `~/multimedia-feasibility/` subdirs.
- Progress reported via ICQ to Desktop Windows at each stage boundary.
- Final Stage 4 demo: upload JPEG/MP3/MP4 via browser to local BeehiveOfAI, see description come back through HoneycombOfAI.

---

## What this plan does NOT do 🚫 (scope discipline)

- No vector mesh / RAG-over-reality (needs real drones + real physical space, per Ch 15).
- No simulated 3D/4D physical mapping.
- No distributed single-value sensor gradient fields.
- No 4-tier RajaBee hierarchy today (Queen + Workers, 2 tiers, is enough).
- No KillerBee / GiantHoneyBee VM infrastructure — direct on host.
- No touching of book repos, BeeSting, MadHoney, WaggleDance code.
- No handling of OUTPUT generation (text → image, text → sound, text → video) — only INPUT / analysis.

---

## Go/No-Go

Plan pushed to GitHub for Nir's review. **Laptop Claude will not start executing Stage 0 until Nir explicitly says GO.** 🚦

---

*Canonical. Edit in place as the plan evolves. Git is the time machine. — 2026-04-18* 📜🐝
