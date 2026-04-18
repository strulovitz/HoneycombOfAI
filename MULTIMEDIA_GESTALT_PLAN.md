# Multimedia Gestalt Correction Plan

**Created:** 2026-04-18 evening, after the book-correction conversation with Nir.
**Supersedes:** the sound- and video-gestalt sections of the implementation committed this morning (`HoneycombOfAI @ feec128` and prior). The morning plan (`MULTIMEDIA_FEASIBILITY_PLAN.md`) stayed truthful about what was done that day; this file documents what was found wrong about it during the first real test, and what now needs to change. Photo handling and audio-slice Workers are not touched; they are correct.

---

## Mission

Two specific errors in the current implementation came out of today's first real end-to-end test on a three-minute audio clip and a thirty-second video clip. Both were flagged by Nir. Both are traceable to the same root cause — the chapter-12 "parent runs her tiny model on a low-fidelity whole copy" framing was internalized as "lower per-second fidelity" when the correct operation is "compress the axis the model cannot hold." This plan fixes both, with honesty checks before any production code is touched.

---

## Hard constraints

- Laptop Linux host, RTX 5090, 24 GB VRAM. Host CUDA / PyTorch / Python / wheels stay untouched (Golden Rule 8). All new work inside `~/multimedia-feasibility/venv/` or inside `~/HoneycombOfAI/` using `~/honeycomb-venv/`.
- Ollama for vision + text. `whisper.cpp` CUDA build for STT. No new system-level dependencies.
- No reward hacking. Honesty checks run before any commit. If a check fails, stop and tell Nir before substituting any approach.
- Services already running stay running: BeehiveOfAI Flask on port 5000, multimedia Queen, four Workers, Firefox.
- Photo pipeline and audio-slice Worker pipeline are not touched — both are already correct after today's earlier fixes.
- ICQ cadence: silent during execution, one update at end, only break silence on real blocker (per Nir's rule from 13:30).

---

## Problems being fixed

### Problem S1 — Sound Queen gestalt does not compress time

**Current code:** `queen_multimedia.py split_sound` calls `queen_whisper(low_wav)` where `low_wav` is the whole recording downsampled to 8 kHz. Lowering the sample rate halves samples per second; it does not shorten the recording's duration.

**Why this is wrong:** whisper-large's receptive field is thirty seconds. The only reason `queen_whisper` returns a full three-minute transcription today is that whisper.cpp internally VAD-chunks the audio into 30-sec windows and stitches the output. That internal stitching is hidden plumbing, not the book's single-pass parent gestalt.

**How it was caught:** Nir, after the book-chapter-12 correction, noted that the currently-running Queen gestalt was still the wrong operation ("sound is not done").

### Problem V1 — Queen never perceives video visually

**Current code:** `split_video` returns `("", ...)` for the visual gestalt. The Queen reads only the audio transcription plus Workers' keyframe reports. No visual gestalt exists at the Queen tier for video.

**Why this is wrong:** chapter 12 says every tier perceives with its own model. For video, the Queen's visual gestalt is the single most important contextual signal in the entire integration step, and it is missing.

**How it was caught:** Nir asked "how does the Queen understand the video visually?" during review.

### Problem V2 — Video Workers perceive single frames, not motion

**Current code:** each `video-frame` tile has `{"timestamp": t}`. Worker `handle_multimedia_tile` for `video-frame` runs `ffmpeg -ss t -frames:v 1` to extract ONE frame, then passes it to a single-image vision model call. The Worker describes a still photograph.

**Why this is wrong:** video is fundamentally about motion. Workers that see still frames cannot perceive motion; the integrator reconstructs motion as text from position deltas at multiple timestamps, which only works on slow monotonic motion and silently fails on anything between keyframes (bounces, gestures, facial micro-expressions, speed, rhythm).

**How it was caught:** Nir's billiard-ball thought experiment — three Workers on a rolling-ball clip report "left," "middle," "right"; none of them saw the ball roll.

### Problem V3 — Video audio gestalt has the same disease as Problem S1

Same mechanism as S1, just on the audio track inside a video container. Fixed by the same operation.

---

## Fixes

### Fix for S1 and V3 — time-compressed Queen audio gestalt

Replace sample-rate reduction with pitch-preserving time-scale compression (what Netflix's 1.5× playback does; algorithmically WSOLA; in ffmpeg, the `atempo` filter).

- Choose a target output duration that comfortably fits whisper-large's 30-sec native window. Use `target_output_duration = 25` seconds to leave margin.
- Compute compression ratio `r = original_duration / target_output_duration`.
  - If `r <= 1.0`: no compression needed, use the original audio in one pass.
  - If `r > 1.0`: produce a time-compressed copy.
- ffmpeg `atempo` accepts a per-filter ratio in [0.5, 2.0]. For ratios above 2, chain multiple filters: e.g., `atempo=2.0,atempo=2.0,atempo=1.5` for 6×. Helper builds the chain.
- Queen runs `whisper-cli` on the compressed clip, single forward pass, no internal VAD stitching required.

Applies to both pure sound and the audio track of video.

### Fix for V1 — Queen visual gestalt from 1-FPS multi-frame pass

The Queen extracts frames from the whole video at ~1 frame per second (or denser if the video is short enough to afford it) with ffmpeg's `-vf fps=1` filter, saves them to a temp dir, and passes the full ordered frame list to a video-capable vision model in a single Ollama `generate()` call with `images=[frame1_bytes, frame2_bytes, ...]`.

Default target: cover the whole video in ≤30 frames per call. If `duration * target_fps > 30`, reduce fps or chunk the video.

Chunking fallback for long videos:
- If total frame count at 1 FPS exceeds a safe single-call budget (initial budget: 30 frames per call, tuned after honesty check), Queen splits the video into sub-sections of `budget / target_fps` seconds each, calls the vision model once per sub-section on its frame sequence, then integrates the sub-gestalts with phi4-mini the same way the hierarchical sound integration already works.
- For a thirty-second clip at 1 FPS: 30 frames, single call. No chunking.
- For a three-minute clip at 1 FPS: 180 frames. Exceeds 30-frame budget. Chunk into six ~30-sec sub-sections, six model calls, integrate.

### Fix for V2 — delete single-frame video Workers entirely

The `video-frame` tile type disappears from `queen_multimedia.py split_video` and from `multimedia_handler.py handle_multimedia_tile`. In the corrected architecture, video visual perception happens only at the Queen tier, in the one-call-on-whole-video step described above. There is no visual Worker in the new video path.

The `video-audio` tile type is unchanged — audio slice Workers continue to do what they already do correctly.

This means for video in the corrected pipeline:
- Queen's visual gestalt: one (or few) ollama calls by the Queen.
- Queen's audio gestalt: whisper-large on a time-compressed copy of the audio track.
- Worker audio slices: 5-sec audio slices with whisper-tiny, Grid A + Grid B — unchanged.

Future extension, not part of this plan: a distributed version where each 30-sec visual sub-section is assigned to a "DwarfQueen" process running its own vision model. For today's implementation, the Queen does all visual calls herself (iterating over sub-sections if chunking is needed).

### Fix for Queen integration prompts

The integration prompt for video needs to mention both the audio gestalt and the visual gestalt now (previously only audio). The sound integration prompt stays structurally the same — the only change is the gestalt text it receives is a cleaner single-pass transcription from a compressed clip.

---

## Honesty checks — run BEFORE any production code is written

### Check 1 — whisper-large on a 6× time-compressed 3-min clip

**Input:** `~/multimedia-feasibility/test_inputs/long_sound.mp3` (Prince-of-Persia ending, 183 sec).

**Procedure:** ffmpeg atempo chain for ratio 6 (e.g., `atempo=2.0,atempo=2.0,atempo=1.5`), output as 16 kHz mono WAV, run `whisper-cli -m ggml-large-v3-turbo-q5_0.bin -f compressed.wav -nt`.

**Pass criterion:** the returned transcription mentions content from all three parts of the original recording (beginning, middle, end), in one forward pass, without relying on internal VAD stitching (output duration of compressed clip ≤ 31 sec so whisper processes it as a single window). Manual spot-check: does the text reference events from the final thirty seconds of the original, not just the first minute?

**If fail:** try ratio 4× (output ~46 sec, still in single-pass range), or switch to sox `tempo` filter, or fall back to chunked atempo.

### Check 2 — qwen3-vl multi-frame motion perception

**Input:** synthesized 5-frame PNG sequence of a red circle moving left-to-right across a 640×480 white background (50 pixels per frame, over 5 frames, so the circle moves ~250 px across the sequence). Generate with PIL.

**Procedure:** pass all five frames to `ollama.Client().generate(model='qwen3-vl:8b', images=[...], prompt='These are 5 frames from a short video in time order. Describe the motion you observe across the frames.')`.

**Pass criterion:** the response describes actual motion — specifically mentions direction of movement (left-to-right), continuity, and treats the frames as a sequence not as five separate images. If the response says "I see a red circle. I see a red circle. I see a red circle." without any mention of motion or order, the model is treating the frames as independent images and does not perceive motion.

**If fail:** pull `minicpm-v:8b` (`ollama pull minicpm-v:8b`) and rerun the same check. If that also fails, stop and tell Nir before trying a third option.

### Check 3 — qwen3-vl frame-order preservation (sanity)

**Input:** 3 frames each containing large text "FRAME 1", "FRAME 2", "FRAME 3". Pass them once in order and once reversed.

**Procedure:** same multi-frame Ollama call; prompt asks which frame appears first, second, third.

**Pass criterion:** model respects the list order in both cases (calls the first image first, etc.), not some internal re-ordering.

**If fail:** same fallback as check 2.

---

## Implementation steps (only if ALL honesty checks pass)

### Step 1 — utilities in `queen_multimedia.py`

Add at the top of the file, alongside existing helpers:

```python
TARGET_GESTALT_AUDIO_SEC = 25.0   # comfortable whisper single-pass window
TARGET_VISUAL_FRAMES_PER_CALL = 30
TARGET_VISUAL_FPS = 1.0

def time_compress_audio(src: Path, dst_wav: Path) -> float:
    """Pitch-preserving time compression via ffmpeg atempo chain, to fit TARGET_GESTALT_AUDIO_SEC.
    Returns the compression ratio used."""
    ...

def extract_frames_at_fps(src_video: Path, fps: float, dst_dir: Path) -> list[Path]:
    """ffmpeg -vf fps=<fps>, returns sorted list of jpg paths."""
    ...
```

### Step 2 — rewrite `split_sound`

Replace the current "low-rate whole recording → gestalt" with "time-compressed whole recording → gestalt." Keep audio slice generation (Grid A + Grid B at 5-sec) exactly as is.

### Step 3 — rewrite `split_video`

Remove all `video-frame` subtask generation. Add `queen_visual_gestalt_video(local_file, client)` that:
1. Extracts frames at `TARGET_VISUAL_FPS` (default 1.0) across the whole duration.
2. If frame count ≤ `TARGET_VISUAL_FRAMES_PER_CALL`: one Ollama call with all frames, prompt explains this is a frame sequence in time order, returns description.
3. Else: chunk frames into groups of `TARGET_VISUAL_FRAMES_PER_CALL`, one Ollama call per chunk, collect chunk descriptions, do a second phi4-mini integration pass over the chunk descriptions (identical pattern to the existing hierarchical audio integration).

Apply the Fix-for-V3 time compression to the audio track for the video audio gestalt.

Keep `video-audio` tile generation unchanged.

Return signature becomes `(audio_gestalt, visual_gestalt, tile_texts)` with the visual_gestalt field actually populated.

### Step 4 — update `multimedia_handler.py`

Delete the `video-frame` branch in `handle_multimedia_tile`. Keep `video-audio`, `photo`, `sound`.

### Step 5 — update integration prompts

Video integration prompt now weaves together:
- `visual_gestalt` (new, real content from Queen's one-call-on-whole-video)
- `audio_gestalt` (now from the time-compressed clip)
- Workers' audio slice transcripts

Tell phi4-mini explicitly that the visual gestalt is the whole video seen end-to-end, and the audio slices are the fine-grained speech detail.

### Step 6 — kill and restart services

Kill the current Queen, restart with new code. Workers keep running unchanged. Flask keeps running unchanged.

### Step 7 — end-to-end test

1. Submit `sample.mp3` (11-sec JFK) via `stage4_test_submit.py sound`. Expect: single-pass gestalt (no compression needed for 11 sec), slice Workers, hierarchical integration. Verify Honey.
2. Submit `long_sound.mp3` (3-min Prince-of-Persia) via `stage4_test_submit.py sound long_sound.mp3`. Expect: 6× compressed gestalt, slice Workers, hierarchical integration. Verify Honey covers all three minutes.
3. Submit `sample.mp4` (30-sec Big Buck Bunny) via `stage4_test_submit.py video`. Expect: single-call visual gestalt, audio gestalt from (barely-compressed) audio, audio Workers, integration. Verify Honey describes actual motion (the rabbit character's arc, not just "a white rabbit in a field" three times).

Pass on all three → commit + push.
Fail on any → stop, tell Nir, do not commit.

---

## Files this plan will touch

- `~/HoneycombOfAI/queen_multimedia.py` — the main surgery: split_sound, split_video, new helpers, visual gestalt function, integration prompts.
- `~/HoneycombOfAI/multimedia_handler.py` — delete `video-frame` branch.
- `~/HoneycombOfAI/MULTIMEDIA_GESTALT_PLAN.md` — this file.
- `~/HoneycombOfAI/MULTIMEDIA_FEASIBILITY_PLAN.md` — append a short pointer at the end of the existing Execution Status table noting that sound and video sections were later superseded by `MULTIMEDIA_GESTALT_PLAN.md`. The morning plan stays truthful about that day's implementation; the corrections live here.

Not touched:
- `~/HoneycombOfAI/worker_bee.py` — dispatch logic is still correct; MULTIMEDIA_TILE routing still needed for audio tiles.
- `~/BeehiveOfAI/` — upload route and status page are correct, no change.
- Photo path, audio-slice Worker path — both correct.

---

## Success criteria

- **Sound 3-min test** (`long_sound.mp3`): Queen gestalt produced from time-compressed clip in one whisper pass; output covers full original duration; final Honey references events from start, middle, and end of the three minutes.
- **Video 30-sec test** (`sample.mp4`): Queen visual gestalt is a single Ollama call on 30 frames across the clip; final Honey describes motion — the character does something (walks, picks apple, interacts with butterfly), not just "there is a white rabbit in a field" repeated.
- **Host integrity** (Rule 8): `/usr/bin/pip --version` unchanged, Python unchanged, driver unchanged, `ollama list` shows same seven models (unless we pulled minicpm-v as a fallback, which adds one — named in the commit if so).
- **No regression** on sound 11-sec JFK test or photo test — both still pass.

---

## What this plan does NOT do

- Change photo handling (already correct).
- Change the audio-slice Worker machinery (already correct after the 5-sec fix).
- Build a distributed video-visual Worker tier. Today the Queen does the video visual herself, iterating if needed. The book-faithful DwarfQueen-per-visual-sub-section version is future work and explicitly out of scope here.
- Apply time compression to the audio track for interpretive high-level gestalt ("this is a dramatic scene with orchestral score"). Whisper-large on the compressed clip gives a transcription gestalt, which is what we need for integration. A non-STT audio-understanding model on the compressed clip is a separate, later improvement.
- Address very long videos (> 1 hour) — chunking logic is written to scale, but testing is limited to the ≤3-minute clips on disk.

---

## Go / No-Go

Plan written for Nir's review. **Laptop Claude will NOT start the honesty checks until Nir explicitly says GO.** If Nir says "skip the plan document step, just do it," Claude still runs the honesty checks before any production code, because honesty checks are the point of the plan, not plan-writing.

---

*Canonical. Edit in place as the plan evolves. Git is the time machine. — 2026-04-18*
