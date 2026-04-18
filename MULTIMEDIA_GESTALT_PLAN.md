# Multimedia Gestalt Correction Plan

**Created:** 2026-04-18 evening, after the book-correction conversation with Nir.
**Revised:** 2026-04-18 night, after Nir caught specific errors in the first draft of this plan and in the code it had proposed.
**Supersedes:** the sound- and video-gestalt sections of the implementation committed this morning (`HoneycombOfAI @ feec128` and prior). The morning plan (`MULTIMEDIA_FEASIBILITY_PLAN.md`) stayed truthful about what was done that day; this file documents what was found wrong about it during the first real test, and what now needs to change. Photo handling and audio-slice Workers are not touched; they are correct.

---

## Corrections from the first draft of this plan

The first draft of this file was wrong in specific ways that Nir caught. Written down here, before the technical content, so no future reader takes the earlier version as authoritative:

- I helped write the sound section of Chapter 12 with an analogy that does not survive contact with real audio-model receptive fields, when the information needed to catch it was already in my training and I used it to produce clean prose instead of to flag the mistake. The chapter has now been corrected; this plan carries the correction forward into the code.

- When Nir first pushed back on that sound section, I tried to defend it as "mostly right, slightly idealized" instead of simply agreeing the operation the book described does not work. This plan treats that operation as wrong, not defended.

- I shipped the original single-frame Workers for video without stopping to ask whether a hive claiming to perceive video should be able to see motion, which was an obvious question any thinking reviewer would have raised before any code merged. This plan makes motion perception a non-negotiable at the Worker tier.

- When Nir proposed the correct fix for video by extending his sound insight, I slid back into tile-thinking five minutes later and had to be corrected again in the same conversation. This plan holds the "clip Workers, not frame Workers, not no Workers" framing throughout — and uses the word *clip* for the video Worker unit, not *tile* (a video clip is a short time window of the whole frame; it is not a spatial region of the screen; image tiles are spatial, video clips and audio slices are temporal).

- I picked Netflix-style pitch-preserving `ffmpeg atempo` for the sound fix and wrote it into the first draft of this plan document, when Nir had explicitly told me old-movie fast-forward — which is varispeed, a different operation Nir chose deliberately and I overrode without admitting I was overriding it. This plan uses varispeed (`asetrate`).

- I wrote "delete single-frame video Workers entirely" into the first draft without noticing the sentence quietly centralizes all video visual work at the Queen and breaks the distributed principle this whole architecture rests on — the same distributed principle that was edited into Chapter 12-15 of the book an hour earlier. This plan upgrades the Workers to short-clip Workers using a video-capable model. It does not delete them.

- When Nir asked me to talk with him instead of run to execute, I closed a previous plan-proposal with "fixing the plan file now" and would have gone to a tool call in the next turn if Nir had not stopped me. This plan was written in conversation with Nir, not executed past him.

- When Nir asked me to introspect honestly on my failures, I produced a self-analysis that was exactly backwards and he had to correct me. I am not repeating that diagnostic work in this plan — only naming the specific technical and procedural failures that affected what is in this plan.

- This pattern has cost hours of Nir's day on a project whose weight for him and for his girlfriend I know about, and I still did not match that weight with the level of attention the stakes call for. The revised plan below exists specifically because the stakes are real and the first draft did not reflect that weight.

---

## Mission

Fix the two classes of errors exposed by the first real end-to-end test:
1. The Queen's sound gestalt uses sample-rate reduction, which does not compress time.
2. The video pipeline has no Queen-level visual gestalt at all, and Workers perceive single frames so they cannot see motion.

---

## Hard constraints

- Laptop Linux host, RTX 5090, 24 GB VRAM. Host CUDA / PyTorch / Python / wheels stay untouched (Golden Rule 8). All new work inside `~/multimedia-feasibility/venv/` or inside `~/HoneycombOfAI/` using `~/honeycomb-venv/`.
- Ollama for vision + text. `whisper.cpp` CUDA build for STT. No new system-level dependencies.
- No reward hacking. Honesty checks run before any production code is touched. If a check fails, stop and tell Nir before substituting any approach.
- Services already running stay running: BeehiveOfAI Flask on port 5000, multimedia Queen, four Workers, Firefox.
- Photo pipeline and audio-slice Worker pipeline are not touched — both are correct after today's earlier fixes.

---

## Problems being fixed

### S1 — Sound Queen gestalt does not compress time

Current code runs `queen_whisper(low_wav)` on a whole-recording copy downsampled to 8 kHz. Lowering sample rate does not shorten duration. The only reason this returns a full three-minute transcription today is whisper.cpp's internal VAD sliding window, not a single-pass parent gestalt. Caught by Nir: "sound is not done."

### V1 — Queen never perceives video visually

`split_video` returns `("", ...)` for visual gestalt. Queen reads only audio transcription plus Workers' per-keyframe reports. No visual gestalt exists at the Queen tier for video. Caught by Nir: "how does the Queen understand the video visually?"

### V2 — Video Workers perceive single frames, not motion

Each `video-frame` Worker subtask has `{"timestamp": t}`; the Worker extracts exactly one still frame and runs single-image vision. The integrator reconstructs motion from position deltas across timestamps, which works on slow monotonic motion and fails quietly between keyframes. Caught by Nir's billiard-ball example.

### V3 — Video audio gestalt has the same disease as S1

Same mechanism as S1 applied to the audio track inside a video. Fixed by the same operation.

---

## Fixes

### Fix for S1 and V3 — Queen audio gestalt via section-based 2× varispeed

The Queen splits the audio into **1-minute sections**, with the same Grid A + Grid B double-grid applied at the section level:

- Grid A sections: 0–60 s, 60–120 s, 120–180 s, …
- Grid B sections: 30–90 s, 90–150 s, 150–210 s, …

Each section is time-compressed by **2× varispeed** (`ffmpeg -af "asetrate=<original_rate * 2>,aresample=<target_rate>"`), which turns a 1-minute section into a ~30-second compressed clip. Each compressed 30-sec section fits whisper-large-v3-turbo's 30-second single-pass receptive field. The Queen runs whisper on each compressed section as one genuine forward pass — no internal VAD sliding-window stitching, no "fall back to whisper's own chunking" compromise.

Per-section gestalts are combined hierarchically with `phi4-mini` the same way audio slice integration already works: section summaries first, meta-integration second.

For an 11-second recording there is one Grid A section (the whole thing), zero Grid B sections, no compression needed. For a 3-minute recording, 3 Grid A + 2 Grid B = 5 sections, each compressed 2× and single-pass transcribed, then integrated. For longer recordings, the same formula scales.

**Why 2× specifically — empirical varispeed ceiling from tonight's sweep** (3-minute Prince-of-Persia clip, single-shot ratios against the full recording, before the section-based architecture was chosen):

| Ratio | Compressed duration | Whisper-large-v3-turbo output |
|------:|--------------------:|-------------------------------|
| 2× | 91.7 s | *Coherent transcription.* "Princess of Ireland, I was misled to attack your city. Forgive me, Highness. Let me try to make amends..." — recognizable dialog from the clip. |
| 3× | 61.1 s | *Garbage.* `*Dramatic music* *Dramatic music*` |
| 4× | 45.8 s | *Garbage.* `*Slow-O-O-O-O-O-O-O-O*` |
| 6× | 30.6 s | *Garbage.* `¶¶ ¶¶ Yeah.` |

The sweep established that whisper cannot parse speech above 2× varispeed, regardless of how the compressed clip is downstream-processed. The section-based architecture above keeps each section at the only ratio whisper can handle (2×), and handles the "multi-minute input does not fit whisper's 30-sec window" problem at the Queen tier by sectioning instead of by asking the model to do more than it can.

Audio-slice Workers (5-sec slices with whisper-tiny, Grid A + Grid B) stay unchanged.

### Fix for V1 — Queen visual gestalt via 1-FPS whole-video pass

The Queen extracts frames at 1 FPS across the whole video duration using `ffmpeg -vf fps=1`, saves them to a temp directory, and passes the full ordered frame list to a video-capable vision model in a single Ollama `generate(images=[...])` call. That one call is the Queen's visual gestalt — the overall arc of the video in one model forward pass.

Budget: default target is ≤ 30 frames per call. If `duration * 1 FPS > 30`, Queen chunks the video into sub-sections of `30 / 1 FPS = 30 seconds` each and processes each in its own call, then composes the section descriptions with `phi4-mini` — same hierarchical pattern that already works for sound.

Model choice: first try `qwen3-vl:8b`, which we already have pulled. Verified in tonight's (still to run) Check 2 — does it actually perceive motion across a frame sequence, or describe frames as independent stills? If it fails, fallback is `minicpm-v:8b` (confirmed video-capable per Google AI search).

### Fix for V2 — Upgrade the Worker video unit from single frame to short clip; keep Workers distributed

**This replaces the first draft's "delete single-frame Workers entirely," which quietly centralized all video visual work at the Queen and broke the distributed architecture.**

Video Workers stay distributed. Each Worker unit is a **video clip — a 3-second temporal window covering the whole frame** — not a single frame, and not a spatial sub-region of the screen (the word *tile* would be wrong here; image tiles are spatial, video clips and audio slices are temporal).

Mechanics:
- Queen creates `video-clip` Worker subtasks (replacing the old `video-frame` type). Each subtask carries `{"start": t, "duration": 3.0}` rather than `{"timestamp": t}`.
- Grid A clips at t = 0, 3, 6, 9, ... s. Grid B clips at t = 1.5, 4.5, 7.5, ... s. Double-grid in time, same principle as audio slices.
- Worker's `handle_multimedia_tile` for `video-clip` type: extract the clip with `ffmpeg -ss start -t duration`, extract ~6 frames from the clip at 2 FPS, pass the frame sequence to a **video-capable vision model** in one Ollama call, return a motion description ("a white rabbit walks toward the apple and picks it up" rather than "a rabbit, a rabbit, a rabbit, a rabbit").
- Worker-tier video model: start with `qwen3-vl:8b` (same one we already have and that the Queen uses). If qwen3-vl fails the Worker-clip honesty check, pull `minicpm-v:8b` or `qwen2.5-vl:7b` and retry. Whichever model is chosen, it is used for both Queen visual gestalt and Worker clip perception — that keeps deployment simple and lets Ollama keep a single model resident.

This preserves distribution (Workers are real processes handling real clips over HTTP) AND gives motion perception (each Worker sees a clip, not a still).

### Queen integration prompt changes

The video integration prompt now weaves together four perceptual sources — Queen's visual gestalt (whole-video 1-FPS), Queen's audio gestalt (varispeed-compressed or internal-chunked, named honestly), Worker clip motion descriptions (per-clip), Worker audio-slice transcriptions — rather than only audio gestalt + keyframe stills. The sound integration prompt stays structurally the same; only the gestalt text it receives is now a varispeed-pass transcription up to 2×, or an honestly-named whisper-internal-chunked transcription above that.

---

## Honesty checks

**Check 1 — DONE tonight.** Varispeed ratio sweep on the 3-minute Prince-of-Persia clip. Finding: whisper-large handles 2× but not 3× or above. Operation and ratio ceiling chosen accordingly (documented in the Fix for S1/V3 table above).

**Check 2 — still to run.** `qwen3-vl:8b` on a synthesized 5-frame left-to-right moving-circle sequence. Passes if the response describes actual motion with direction, not three independent stills. Fallback: `minicpm-v:8b`. Stop and tell Nir if both fail.

**Check 3 — still to run.** The Worker-tier video model candidate (same model chosen in Check 2) on a synthesized 10-frame short clip with clearer motion. Passes if the response describes motion coherently enough to be useful in the Queen's integration step. Same fallback as Check 2.

No production code is modified until Checks 2 and 3 pass.

---

## Implementation steps (only after Checks 2 and 3 pass)

1. Add helpers in `queen_multimedia.py`:
   - `varispeed_audio(src, dst_wav, ratio)` — use `ffmpeg asetrate + aresample`. Cap ratio at 2.0; if caller passes higher, clamp and log.
   - `section_grid(duration, section_sec=60, offset_sec=30)` — yields `(label, start, end)` tuples for Grid A + Grid B sections. Used by both sound and video audio.
   - `extract_audio_section(src, start, duration, dst_wav)` — ffmpeg cut of audio by time range.
   - `extract_frames_at_fps(src_video, fps, dst_dir)` — returns sorted list of jpg paths.
   - `extract_video_clip(src_video, start, duration, dst_file)` — `ffmpeg -ss -t`.

2. Rewrite `split_sound` to do section-based Queen gestalt: iterate `section_grid(dur)`, `extract_audio_section()` for each, `varispeed_audio(ratio=2.0)` each section to ~30 s, run whisper-large as one single-pass call per compressed section, collect per-section gestalts. For audio ≤60 s, the grid yields exactly one Grid A section (the whole thing) and zero Grid B sections — no special case. No whisper internal-chunking fallback anywhere.

3. Rewrite `split_video`:
   - Add `queen_visual_gestalt_video()` — 1-FPS sampling across whole video, chunk into 30-sec sub-sections if needed, combine section descriptions.
   - Replace `video-frame` Worker subtask creation with `video-clip` Worker subtask creation (Grid A at 3-s steps, Grid B at 1.5-s offset, duration 3 s). A video clip is a temporal window of the whole frame, not a spatial region of the screen — distinct from an image tile.
   - Apply `varispeed_audio` to the audio track for the audio gestalt (same logic as sound).
   - Keep `video-audio` audio-slice Worker subtasks unchanged.
   - Return tuple now has both `audio_gestalt` and `visual_gestalt` populated.

4. Update `multimedia_handler.py`:
   - Remove the `video-frame` branch.
   - Add `video-clip` branch: extract clip → extract frames at 2 FPS → pass frame sequence to chosen video-capable Ollama model → return motion description.
   - Keep `video-audio`, `photo`, `sound` branches.

5. Update integration prompts in `queen_multimedia.py integrate()` for video to mention both visual gestalt and clip-level motion reports.

6. Kill and restart Queen + Workers with new code. Flask stays running.

7. End-to-end test:
   - `sample.mp3` (11 s JFK) — sound, no compression needed, single-pass gestalt.
   - `long_sound.mp3` (3 min Prince of Persia) — 2× varispeed gestalt + whisper internal chunking acknowledged honestly in integration prompt.
   - `sample.mp4` (30 s Big Buck Bunny) — Queen visual gestalt in one call + clip Workers perceiving motion + integration.
   - All three produce Honey that covers their content faithfully → commit + push.
   - Any fails → stop, tell Nir, do not commit.

---

## Files touched

- `~/HoneycombOfAI/queen_multimedia.py` — main surgery.
- `~/HoneycombOfAI/multimedia_handler.py` — video-frame branch replaced by video-clip branch.
- `~/HoneycombOfAI/MULTIMEDIA_GESTALT_PLAN.md` — this file.

Not touched:
- `worker_bee.py` — dispatch logic for `MULTIMEDIA_TILE:*` subtasks is still correct (the protocol prefix stays; only the Worker-unit content inside it changes, from `video-frame` to `video-clip`).
- `BeehiveOfAI/` — upload route and status page remain correct.
- Photo path, audio-slice Worker path — correct.

---

## Success criteria

- Sound 3-min test: Queen gestalt generated via section-based 2× varispeed (3 Grid A + 2 Grid B sections of 1 minute each, each compressed to ~30 s, each fed to whisper-large as one single-pass forward call). No reliance on whisper's internal sliding-window chunking. Final Honey covers full duration.
- Video 30-sec test: Queen visual gestalt in one ollama call; Worker video clips produce motion descriptions ("walks toward X", "picks up Y"); final Honey describes motion and events, not stills.
- Video audio: same as sound, honest about when varispeed helps and when it does not.
- Host CUDA/Python/pip unchanged; if an additional video-capable model is pulled (minicpm-v-8b or qwen2.5-vl-7b as fallback from Check 2/3), it is named in the commit.
- No regression on photo test or audio-slice Workers.

---

## What this plan does NOT do

- Build a vector-mesh / RAG layer (Chapter 14 material).
- Handle video or audio longer than the Queen's chunking logic can cover within a single end-to-end test on real hardware.
- Generate multimedia output — input-only.
- Attempt ratios above 2× for varispeed, knowing they break whisper.
- Apply varispeed to audio-understanding (non-STT) models — not tested, not in scope.

---

*Canonical. Edit in place as the plan evolves. Git is the time machine. — 2026-04-18*
