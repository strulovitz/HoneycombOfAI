# Linux Cross-Machine Test Results

**Date:** 2026-03-25
**Result:** PASS
**Conducted by:** Desktop Claude Code (Opus 4.6, Linux Mint 22.2) + Laptop Claude Code (Opus 4.6, Debian 13)

---

## Test Configuration

| Machine | OS | GPU | Role | IP | Backend | Model |
|---------|-----|-----|------|-----|---------|-------|
| Desktop | Linux Mint 22.2 (Cinnamon) | RTX 4070 Ti (12GB) | Website + Worker Bee | 10.0.0.4 | Ollama | llama3.2:3b |
| Laptop | Debian 13 | RTX 5090 (24GB) | Queen Bee | 10.0.0.7 | Ollama | llama3.2:3b |

**Website:** Flask dev server on `0.0.0.0:5000` (LAN access)
**Database:** Fresh seed data (worker1, queen1, company1 test accounts)

---

## Test Timeline

| Time | Event | Machine |
|------|-------|---------|
| 14:11:40 | Beekeeper (company1) submitted job #3 via website | Desktop (browser) |
| 14:11:47 | Queen claimed job #3 | Laptop (10.0.0.7) |
| 14:11:53 | Queen split task into subtasks using AI, posted to API | Laptop |
| 14:11:53 | Queen set job status to "processing" | Laptop |
| 14:11:54 | Worker claimed subtask #7 | Desktop (10.0.0.4) |
| 14:12:30 | Worker completed subtask #7 (2647 chars) — environmental impact of geothermal energy | Desktop |
| 14:12:30 | Worker claimed subtask #8 | Desktop |
| 14:12:35 | Worker completed subtask #8 (3639 chars) — economic feasibility of geothermal energy | Desktop |
| 14:12:39 | Queen detected all subtasks complete, began combining | Laptop |
| 14:12:44 | Queen posted final Honey result — **JOB COMPLETE** | Laptop |
| 14:13:49 | Beekeeper rated the job | Desktop (browser) |

**Total pipeline time:** ~64 seconds (submit to complete)
**Worker processing:** ~36s for subtask #7, ~5s for subtask #8

---

## What Was Verified

- [x] Flask website accessible over LAN from both machines
- [x] Worker Bee authentication via API (base64 bearer token)
- [x] Queen Bee authentication via API
- [x] Queen AI-driven task splitting (Ollama on RTX 5090)
- [x] Subtask creation via REST API
- [x] Worker polling and subtask claiming
- [x] Worker AI processing (Ollama on RTX 4070 Ti)
- [x] Worker result submission via REST API
- [x] Queen monitoring subtask completion
- [x] Queen AI-driven result synthesis
- [x] Job completion and revenue split
- [x] Beekeeper viewing and rating the result
- [x] Full cross-machine Linux-to-Linux communication

---

## Comparison with Windows Test (2026-03-22)

| Aspect | Windows Test | Linux Test |
|--------|-------------|------------|
| Date | 2026-03-22 | 2026-03-25 |
| Desktop role | Queen + Website | Worker + Website |
| Laptop role | Worker | Queen |
| Desktop OS | Windows 11 | Linux Mint 22.2 |
| Laptop OS | Windows 11 | Debian 13 |
| Backend | Ollama | Ollama |
| Result | PASS | PASS |
| Communication | LAN (10.0.0.x) | LAN (10.0.0.x) |

**Key difference:** The roles were swapped — in the Windows test, the Desktop was Queen and Laptop was Worker. In the Linux test, the Desktop is Worker and the Laptop is Queen. Both configurations work.

---

## Notes

- The company1 test account needed to be manually marked as `is_verified=True` in the database since Twilio SMS was running in test mode (no env vars set). This is expected behavior — the two-mode SMS design works correctly.
- Flask debug mode's auto-reloader caused a false "process exited" notification in Claude Code's background task monitor, but the server remained running. Not a real issue.
- The Desktop's RTX 4070 Ti handled AI inference smoothly via Ollama.

---

# Test 2: Full Internet Test (Same Day)

**Date:** 2026-03-25 (14:50)
**Result:** PASS
**Type:** Real internet via Cloudflare Tunnel + Real Twilio SMS

## Configuration

| Component | Details |
|-----------|---------|
| Website | https://beehiveofai.com via Cloudflare Tunnel `beehive-linux` |
| Desktop | Linux Mint 22.2, RTX 4070 Ti, Worker Bee (Ollama), 10.0.0.4 |
| Laptop | Debian 13, RTX 5090, Queen Bee (Ollama), 10.0.0.7 |
| SMS | Real Twilio Verify API — SMS received on +972544752626 |
| Tunnel | 4 connections: Tel Aviv (tlv01) + Frankfurt (fra06, fra20) |

## Timeline

| Time | Event |
|------|-------|
| 14:45:56 | SMS verification page loaded |
| 14:47:35 | Resend SMS — real SMS sent to Nir's phone |
| 14:48:31 | Code verified successfully — phone verified! |
| 14:50:21 | Job #4 submitted: "Pros and cons of AI in space" |
| 14:50:23 | Queen (Laptop, via internet) claimed job |
| 14:50:28 | Worker (Desktop) claimed subtask #9 |
| 14:50:29 | Worker claimed subtask #10 |
| 14:50:32 | Worker completed subtask #9 |
| 14:50:40 | Worker completed subtask #10 |
| 14:50:50 | Queen combined — JOB COMPLETE |
| 14:57:59 | Beekeeper rated the job |

**Total pipeline time: ~27 seconds**

## What Was Verified

- [x] beehiveofai.com served from Linux Mint via Cloudflare Tunnel
- [x] Real SMS sent and received via Twilio Verify API
- [x] Phone verification flow (6-digit code entry)
- [x] Queen connecting via real internet URL (not LAN)
- [x] Full distributed AI pipeline over internet
- [x] Job rating after completion
