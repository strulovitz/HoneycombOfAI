"""
queen_multimedia.py — The Queen Bee for multimedia Jobs.

Per MULTIMEDIA_GESTALT_PLAN.md (commit 5da9d13):

- Sound: Queen splits audio into 1-minute Grid A + Grid B sections. Each
  section is 2x-varispeed-compressed (ffmpeg asetrate) to ~30 s and fed to
  whisper-large as one genuine single-pass call — no reliance on whisper's
  internal VAD chunking. Workers still process 5-sec audio slices.
- Video visual: Queen samples frames at 1 FPS per 1-minute Grid A + Grid B
  section, passes the frame sequence to qwen3-vl:8b via Ollama (with
  /no_think directive so the response is the motion description, not
  thinking tokens). Per-section descriptions collected as the visual gestalt.
- Video audio: same section-based Queen gestalt as pure sound. Workers still
  process 5-sec audio-slice tiles.
- Video worker tiles: short video *clips* (3 s, Grid A at 0/3/6..., Grid B
  at 1.5/4.5/...). Each Worker extracts its clip and runs qwen3-vl on a
  2-FPS frame sequence from the clip, returning a motion description.
  Workers see motion, not single frames.
- Integration stays hierarchical when tile count exceeds CHUNK_SIZE.

Run: python3 queen_multimedia.py
Requires queen1@test.com credentials (queen of hive 1 per seed_data).
"""
import io
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

import ollama
import requests
from PIL import Image
from rich.console import Console
from rich.panel import Panel

from api_client import BeehiveAPIClient

console = Console()

# Models.
QUEEN_VISION = "qwen3-vl:8b"
QUEEN_TEXT = "phi4-mini:3.8b"

# whisper.cpp CUDA
WHISPER_ROOT = Path.home() / "multimedia-feasibility" / "whisper.cpp"
WHISPER_BIN = WHISPER_ROOT / "build" / "bin" / "whisper-cli"
WHISPER_MODEL = WHISPER_ROOT / "models" / "ggml-large-v3-turbo-q5_0.bin"

WEBSITE = "http://127.0.0.1:5000"
QUEEN_EMAIL = "queen1@test.com"
QUEEN_PASSWORD = "test123"
HIVE_ID = 1
POLL_INTERVAL = 5
SUBTASK_TIMEOUT = 1800  # 30 min

# Queen-tier section sizes (for gestalts that don't fit one model call).
AUDIO_SECTION_SEC = 60.0
AUDIO_SECTION_OFFSET = 30.0
VARISPEED_RATIO = 2.0  # empirical ceiling whisper tolerates for speech
VIDEO_SECTION_SEC = 60.0
VIDEO_SECTION_OFFSET = 30.0
VIDEO_GESTALT_FPS = 1.0  # frames per second sampled by Queen across each video section

# Worker-tier tile sizes.
SOUND_SLICE_LEN = 5.0  # audio slices (also used inside video for speech detail)
SOUND_SLICE_OFFSET = 2.5
VIDEO_CLIP_LEN = 3.0
VIDEO_CLIP_OFFSET = 1.5
VIDEO_CLIP_SAMPLE_FPS = 2.0  # frames per second within each Worker clip


# ---------- basic helpers ----------

def parse_multimedia_nectar(nectar: str) -> tuple[str | None, str | None]:
    m = re.search(r"\[multimedia:(photo|sound|video)\]", nectar)
    if not m:
        return None, None
    media_type = m.group(1)
    m2 = re.search(r"url=(\S+)", nectar)
    url = m2.group(1) if m2 else None
    return media_type, url


def fetch_file(url: str, dest: Path) -> None:
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    dest.write_bytes(r.content)


def img_to_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def queen_text(client: ollama.Client, prompt: str, num_predict: int = 600) -> str:
    resp = client.generate(
        model=QUEEN_TEXT,
        prompt=prompt,
        options={"temperature": 0.3, "num_predict": num_predict, "num_ctx": 8192},
    )
    return resp.response.strip()


def queen_vision_multi(client: ollama.Client, frames: list[bytes], prompt: str,
                      num_predict: int = 500) -> str:
    """Multi-frame Queen/Worker vision call. Prepends /no_think so qwen3-vl
    does not waste num_predict on internal thinking tokens. Falls back to the
    thinking field if the response is empty (which happens when the model
    decided to think despite /no_think)."""
    resp = client.generate(
        model=QUEEN_VISION,
        prompt=f"/no_think {prompt}",
        images=frames,
        options={"temperature": 0.1, "num_predict": num_predict, "num_ctx": 32768},
    )
    text = (resp.response or "").strip()
    if not text:
        # Fallback: some qwen3-vl variants ignore /no_think and put content in thinking.
        thinking = getattr(resp, "thinking", "") or ""
        text = thinking.strip()
    return text


def queen_vision_single(client: ollama.Client, img: Image.Image, prompt: str) -> str:
    return queen_vision_multi(client, [img_to_bytes(img)], prompt, num_predict=500)


def run_whisper(wav_path: Path) -> str:
    r = subprocess.run(
        [str(WHISPER_BIN), "-m", str(WHISPER_MODEL), "-f", str(wav_path), "-nt"],
        capture_output=True, text=True,
    )
    return r.stdout.strip()


def make_tile_text(media_type: str, label: str, url: str, params: dict) -> str:
    param_str = "|".join(f"{k}={v}" for k, v in params.items())
    return f"MULTIMEDIA_TILE:{media_type}:{label}:{url}|{param_str}"


# ---------- ffmpeg wrappers ----------

def _ff(args: list[str]) -> None:
    subprocess.run(args, capture_output=True, check=True)


def extract_audio(src: Path, dst_wav: Path, rate: int = 16000) -> None:
    _ff(["ffmpeg", "-y", "-i", str(src), "-ac", "1", "-ar", str(rate),
         "-vn", str(dst_wav)])


def extract_audio_section(src: Path, start: float, duration: float,
                         dst_wav: Path, rate: int = 16000) -> None:
    _ff(["ffmpeg", "-y", "-i", str(src), "-ss", f"{start}", "-t", f"{duration}",
         "-ac", "1", "-ar", str(rate), "-vn", str(dst_wav)])


def varispeed_audio(src_wav: Path, dst_wav: Path, ratio: float,
                    rate: int = 16000) -> None:
    """Tape-style varispeed (pitch shifts up with speed) via asetrate+aresample.
    Ratio is clamped to VARISPEED_RATIO so we never ask whisper to parse speech
    beyond its trained pitch range."""
    ratio = min(ratio, VARISPEED_RATIO)
    new_rate = int(rate * ratio)
    _ff(["ffmpeg", "-y", "-i", str(src_wav),
         "-af", f"asetrate={new_rate},aresample={rate}",
         "-ac", "1", str(dst_wav)])


def extract_video_clip(src: Path, start: float, duration: float,
                      dst_mp4: Path) -> None:
    _ff(["ffmpeg", "-y", "-ss", f"{start}", "-i", str(src),
         "-t", f"{duration}", "-an", "-c:v", "copy", str(dst_mp4)])


def extract_frames(src: Path, start: float, duration: float, fps: float,
                  dst_dir: Path) -> list[Path]:
    """Extract frames from [start, start+duration) at given FPS. Returns sorted paths."""
    _ff(["ffmpeg", "-y", "-ss", f"{start}", "-i", str(src),
         "-t", f"{duration}", "-vf", f"fps={fps}",
         str(dst_dir / "frame_%04d.jpg")])
    return sorted(dst_dir.glob("frame_*.jpg"))


def probe_duration(src: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(src)],
        capture_output=True, text=True,
    )
    return float(r.stdout.strip())


# ---------- section grid (Queen-tier time sectioning) ----------

def section_grid(duration: float, section_sec: float, offset_sec: float):
    """Yield (label, start, end) for Grid A + Grid B sections over `duration`.

    Grid A: 0, section_sec, 2*section_sec, ...
    Grid B: offset_sec, offset_sec+section_sec, ...
    A section shorter than half section_sec is dropped (not enough content
    to be worth a separate model call).
    For duration <= section_sec, exactly one Grid A section (the whole thing)."""
    min_keep = max(1.0, section_sec * 0.3)
    # Grid A
    s = 0.0
    idx = 0
    while s < duration - 0.1:
        end = min(s + section_sec, duration)
        if end - s >= min_keep or idx == 0:
            yield (f"A-{idx}", s, end)
        s += section_sec
        idx += 1
    # Grid B (only if audio is longer than the offset plus min_keep)
    if duration <= offset_sec + min_keep:
        return
    s = offset_sec
    idx = 0
    while s < duration - 0.1:
        end = min(s + section_sec, duration)
        if end - s >= min_keep:
            yield (f"B-{idx}", s, end)
        s += section_sec
        idx += 1


# ---------- PHOTO split (unchanged) ----------

def split_photo(url: str, local_file: Path, client: ollama.Client) -> tuple[str, list[str]]:
    img = Image.open(local_file).convert("RGB")
    W, H = img.size
    low = img.resize((W // 2, H // 2), Image.LANCZOS)
    gestalt = queen_vision_single(
        client, low,
        "Describe the overall scene, layout, and what you see. 3-4 sentences.",
    )
    qw, qh = W // 4, H // 4
    tiles = [
        ("A-UL", (0, 0, W // 2, H // 2)),
        ("A-UR", (W // 2, 0, W, H // 2)),
        ("A-LL", (0, H // 2, W // 2, H)),
        ("A-LR", (W // 2, H // 2, W, H)),
        ("B-TOP-MID", (qw, 0, W - qw, H // 2)),
        ("B-BOT-MID", (qw, H // 2, W - qw, H)),
        ("B-LEFT-MID", (0, qh, W // 2, H - qh)),
        ("B-RIGHT-MID", (W // 2, qh, W, H - qh)),
    ]
    texts = []
    for label, (x1, y1, x2, y2) in tiles:
        texts.append(make_tile_text("photo", label, url,
                                    {"crop": f"{x1},{y1},{x2},{y2}"}))
    return gestalt, texts


# ---------- SOUND split (section-based Queen gestalt + 5-sec slice Workers) ----------

def _queen_audio_gestalt(local_file: Path, dur: float, tdp: Path) -> str:
    """Section-based Queen audio gestalt. For each Grid A + Grid B section,
    compress by 2x varispeed and run whisper-large as one genuine single-pass
    call on the compressed ~30-sec clip. Return text with section labels so
    the downstream integrator knows what time window each line covers."""
    lines: list[str] = []
    for label, start, end in section_grid(dur, AUDIO_SECTION_SEC, AUDIO_SECTION_OFFSET):
        sec_wav = tdp / f"audsec_{label}.wav"
        comp_wav = tdp / f"audsec_{label}_2x.wav"
        extract_audio_section(local_file, start, end - start, sec_wav)
        varispeed_audio(sec_wav, comp_wav, VARISPEED_RATIO)
        text = run_whisper(comp_wav)
        console.print(f"    [dim]audio gestalt section {label} ({start:.0f}-{end:.0f}s): {text[:80]}[/dim]")
        lines.append(f"[{label} {start:.0f}-{end:.0f}s] {text}")
    return "\n".join(lines)


def split_sound(url: str, local_file: Path) -> tuple[str, float, list[str]]:
    """Return (gestalt_text, duration_sec, list_of_tile_subtask_texts)."""
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        full_wav = tdp / "full.wav"
        extract_audio(local_file, full_wav)
        dur = probe_duration(full_wav)
        console.print(f"  [cyan]sound duration {dur:.1f}s — running section-based Queen gestalt[/cyan]")
        gestalt = _queen_audio_gestalt(local_file, dur, tdp)

    # Worker 5-sec slice tiles (unchanged — give the integrator fine-grained detail).
    texts: list[str] = []
    s = 0.0
    while s + SOUND_SLICE_LEN <= dur:
        texts.append(make_tile_text("sound", f"A-{s:.1f}", url,
                                    {"start": f"{s:.1f}", "duration": f"{SOUND_SLICE_LEN:.1f}"}))
        s += SOUND_SLICE_LEN
    s = SOUND_SLICE_OFFSET
    while s + SOUND_SLICE_LEN <= dur:
        texts.append(make_tile_text("sound", f"B-{s:.1f}", url,
                                    {"start": f"{s:.1f}", "duration": f"{SOUND_SLICE_LEN:.1f}"}))
        s += SOUND_SLICE_LEN
    return gestalt, dur, texts


# ---------- VIDEO split ----------

def _queen_visual_gestalt(local_file: Path, dur: float, client: ollama.Client,
                          tdp: Path) -> str:
    """Section-based Queen visual gestalt. For each 1-min Grid A + Grid B
    section of the video, extract frames at 1 FPS and pass the frame sequence
    to qwen3-vl:8b in one call. Return text with section labels."""
    lines: list[str] = []
    for label, start, end in section_grid(dur, VIDEO_SECTION_SEC, VIDEO_SECTION_OFFSET):
        frame_dir = tdp / f"vsec_{label}"
        frame_dir.mkdir(exist_ok=True)
        frames = extract_frames(local_file, start, end - start, VIDEO_GESTALT_FPS, frame_dir)
        frame_bytes = [fp.read_bytes() for fp in frames]
        if not frame_bytes:
            continue
        t0 = time.monotonic()
        text = queen_vision_multi(
            client, frame_bytes,
            f"These are {len(frame_bytes)} frames from section {label} of a video, "
            f"sampled at 1 frame per second, covering {end - start:.0f} seconds in time order. "
            "Describe the motion, actions, scene changes, and who/what is present. "
            "One short paragraph. No tile labels in the output.",
            num_predict=500,
        )
        dt = time.monotonic() - t0
        console.print(f"    [dim]visual gestalt section {label} ({start:.0f}-{end:.0f}s, {len(frame_bytes)} frames, {dt:.1f}s): {text[:80]}[/dim]")
        lines.append(f"[{label} {start:.0f}-{end:.0f}s] {text}")
    return "\n".join(lines)


def split_video(url: str, local_file: Path, client: ollama.Client) -> tuple[str, str, list[str]]:
    """Return (audio_gestalt, visual_gestalt, list_of_tile_subtask_texts).

    Tiles:
      - Worker video-clip tiles: 3-sec clips, Grid A at 0/3/6..., Grid B at 1.5/4.5/...
      - Worker video-audio tiles: 5-sec audio slices, same double grid
    No more video-frame single-still tiles — those could not perceive motion.
    """
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        dur = probe_duration(local_file)
        console.print(f"  [cyan]video duration {dur:.1f}s — running section-based audio+visual Queen gestalts[/cyan]")
        audio_gestalt = _queen_audio_gestalt(local_file, dur, tdp)
        visual_gestalt = _queen_visual_gestalt(local_file, dur, client, tdp)

    texts: list[str] = []
    # Video CLIP tiles (Worker motion perception)
    s = 0.0
    while s + VIDEO_CLIP_LEN <= dur:
        texts.append(make_tile_text("video-clip", f"CL-A-{s:.1f}", url,
                                    {"start": f"{s:.1f}",
                                     "duration": f"{VIDEO_CLIP_LEN:.1f}",
                                     "fps": f"{VIDEO_CLIP_SAMPLE_FPS:.1f}"}))
        s += VIDEO_CLIP_LEN
    s = VIDEO_CLIP_OFFSET
    while s + VIDEO_CLIP_LEN <= dur:
        texts.append(make_tile_text("video-clip", f"CL-B-{s:.1f}", url,
                                    {"start": f"{s:.1f}",
                                     "duration": f"{VIDEO_CLIP_LEN:.1f}",
                                     "fps": f"{VIDEO_CLIP_SAMPLE_FPS:.1f}"}))
        s += VIDEO_CLIP_LEN

    # Video AUDIO slice tiles (Worker speech detail — unchanged)
    s = 0.0
    while s + SOUND_SLICE_LEN <= dur:
        texts.append(make_tile_text("video-audio", f"AU-A-{s:.1f}", url,
                                    {"start": f"{s:.1f}", "duration": f"{SOUND_SLICE_LEN:.1f}"}))
        s += SOUND_SLICE_LEN
    s = SOUND_SLICE_OFFSET
    while s + SOUND_SLICE_LEN <= dur:
        texts.append(make_tile_text("video-audio", f"AU-B-{s:.1f}", url,
                                    {"start": f"{s:.1f}", "duration": f"{SOUND_SLICE_LEN:.1f}"}))
        s += SOUND_SLICE_LEN

    return audio_gestalt, visual_gestalt, texts


# ---------- hierarchical integration (phi4-mini) ----------

CHUNK_SIZE = 20  # tile lines per sub-integration call


def _tile_label(subtask_text: str) -> str:
    m = re.match(r"MULTIMEDIA_TILE:[^:]+:([^:]+):", subtask_text)
    return m.group(1) if m else "?"


def _tile_timestamp(label: str) -> float:
    m = re.search(r"-(\d+(?:\.\d+)?)(?:s)?$", label)
    return float(m.group(1)) if m else 0.0


def _chunk_sub_integrate_sound(client, chunk_lines, chunk_idx, n_chunks):
    body = "\n".join(chunk_lines)
    prompt = f"""You are summarizing time-window {chunk_idx+1} of {n_chunks} from an audio recording.

Slice transcriptions (Grid A + Grid B overlapping 5-sec slices; whisper-tiny may introduce minor errors):
{body}

Produce ONE coherent paragraph (2-4 sentences) of what was said in this time window. Preserve proper nouns, numbers, and distinctive phrases. Merge duplicates across overlapping A/B slices. Skip silent/blank slices."""
    return queen_text(client, prompt, num_predict=300)


def _chunk_sub_integrate_video(client, chunk_lines, chunk_idx, n_chunks):
    body = "\n".join(chunk_lines)
    prompt = f"""You are summarizing time-window {chunk_idx+1} of {n_chunks} from a short video.

Reports in this window mix motion-perceived video clip descriptions (CL-*) and audio slice transcriptions (AU-*):
{body}

Produce ONE coherent paragraph (2-4 sentences) of what happens in this time window — both what is seen (motion, actions) and what is heard. Merge duplicates across overlapping A/B tiles."""
    return queen_text(client, prompt, num_predict=300)


def _meta_integrate_sound(client, gestalt_aud, chunk_paragraphs):
    sections = "\n\n".join(f"Window {i+1}:\n{p}" for i, p in enumerate(chunk_paragraphs))
    prompt = f"""You are the Queen Bee integrating an audio recording end-to-end.

Your own section-based gestalt (whisper-large run as single-pass forward calls on 2x-varispeed-compressed 1-minute sections of the recording):
{gestalt_aud}

Chunk summaries of the fine-grained 5-sec slice transcriptions in time order:
{sections}

Write one coherent transcription that COVERS THE ENTIRE RECORDING from start to finish. Use the section gestalts as the backbone and fill in detail from the chunk summaries. End with a 2-3 sentence summary of what the recording is about."""
    return queen_text(client, prompt, num_predict=2000)


def _meta_integrate_video(client, gestalt_aud, gestalt_vis, chunk_paragraphs):
    sections = "\n\n".join(f"Window {i+1}:\n{p}" for i, p in enumerate(chunk_paragraphs))
    prompt = f"""You are the Queen Bee integrating a video end-to-end.

Your own visual gestalt (qwen3-vl single multi-frame call per 1-minute section of the video, 1 FPS sampling — describes motion, action, presence over time):
{gestalt_vis}

Your own audio gestalt (whisper-large run as single-pass forward calls on 2x-varispeed-compressed 1-minute sections of the audio track):
{gestalt_aud}

Chunk summaries of fine-grained Worker reports (3-sec video clips that perceived motion + 5-sec audio slices) in time order:
{sections}

Write one coherent narrative that COVERS THE ENTIRE VIDEO from start to finish. Weave visual and audio into a single time-ordered story — what happens, who does what, what is said. End with a 2-3 sentence summary."""
    return queen_text(client, prompt, num_predict=2000)


def integrate(client: ollama.Client, media_type: str, gestalt_vis: str,
              gestalt_aud: str, tile_results: list[dict]) -> str:
    if media_type == "photo":
        lines = []
        for tr in tile_results:
            label = _tile_label(tr["subtask"])
            lines.append(f"- {label} (worker {tr.get('worker_id')}): "
                         f"{tr['result'].splitlines()[0][:220]}")
        tile_section = "\n".join(lines)
        prompt = f"""You are the Queen Bee integrating a photo analysis from a hive of tile-worker Bees.

Your own gestalt (Queen ran qwen3-vl on a low-resolution copy of the whole photo):
{gestalt_vis}

Tile reports (Grid A = 4 quadrants A-UL/A-UR/A-LL/A-LR; Grid B = 4 straddling tiles B-TOP-MID/B-BOT-MID/B-LEFT-MID/B-RIGHT-MID at 25% offsets to recover anything Grid A sliced in half):
{tile_section}

Produce one coherent description. Use your own gestalt as the spatial map, place tile-detail onto it, merge duplicates across overlapping A and B tiles. Do NOT emit tile labels in the output. 5-8 sentences."""
        return queen_text(client, prompt, num_predict=800)

    # Sound / video — sort tile reports by time and chunk for hierarchical integration.
    sorted_tiles = sorted(
        tile_results,
        key=lambda tr: _tile_timestamp(_tile_label(tr["subtask"])),
    )
    lines = []
    for tr in sorted_tiles:
        label = _tile_label(tr["subtask"])
        snippet = tr["result"].splitlines()[0][:220] if tr["result"] else ""
        lines.append(f"- {label}: {snippet}")

    # Fits one call — skip hierarchical layer.
    if len(lines) <= CHUNK_SIZE:
        body = "\n".join(lines)
        if media_type == "sound":
            prompt = f"""You are the Queen integrating an audio recording from a hive of slice-worker Bees.

Your own section-based gestalt (whisper-large on 2x-varispeed 1-minute sections):
{gestalt_aud}

Slice transcriptions (Grid A + Grid B overlapping 5-sec slices, in time order):
{body}

Produce one final transcription covering the whole recording. De-duplicate overlapping A/B slices. End with a 1-2 sentence summary."""
        else:  # video
            prompt = f"""You are the Queen integrating a short video from a hive of tile-worker Bees.

Your own visual gestalt (qwen3-vl multi-frame calls per 1-minute section, 1 FPS):
{gestalt_vis}

Your own audio gestalt (whisper-large on 2x-varispeed 1-minute sections of the audio track):
{gestalt_aud}

Tile reports mixing motion-perceived video clips (CL-*) and audio slices (AU-*) in time order:
{body}

Produce a coherent narrative from start to finish, weaving visual and audio. Do NOT emit tile labels. 4-8 sentences."""
        return queen_text(client, prompt, num_predict=1500)

    # Hierarchical path.
    chunks = [lines[i:i + CHUNK_SIZE] for i in range(0, len(lines), CHUNK_SIZE)]
    console.print(f"  [cyan]Hierarchical integration: {len(lines)} tiles -> {len(chunks)} chunks[/cyan]")
    chunk_paragraphs: list[str] = []
    sub_fn = _chunk_sub_integrate_sound if media_type == "sound" else _chunk_sub_integrate_video
    for idx, chunk in enumerate(chunks):
        t0 = time.monotonic()
        para = sub_fn(client, chunk, idx, len(chunks))
        chunk_paragraphs.append(para)
        console.print(f"    [dim]sub-integration {idx+1}/{len(chunks)} done in {time.monotonic()-t0:.1f}s[/dim]")

    if media_type == "sound":
        return _meta_integrate_sound(client, gestalt_aud, chunk_paragraphs)
    else:
        return _meta_integrate_video(client, gestalt_aud, gestalt_vis, chunk_paragraphs)


# ---------- main Queen loop ----------

def wait_for_subtasks(api: BeehiveAPIClient, job_id: int, subtask_ids: list[int],
                      timeout: int, check_interval: int = 4) -> list[dict]:
    start = time.time()
    while True:
        elapsed = time.time() - start
        if elapsed > timeout:
            raise TimeoutError(f"Subtasks not completed within {timeout}s")
        subtasks = api.get_job_subtasks(job_id)
        relevant = [st for st in subtasks if st["id"] in subtask_ids]
        completed = [st for st in relevant if st["status"] == "completed"]
        console.print(f"  [dim]progress {len(completed)}/{len(relevant)} done ({int(elapsed)}s)[/dim]")
        if len(completed) == len(relevant):
            return [{"subtask": st["subtask_text"], "result": st["result_text"] or "",
                     "worker_id": str(st.get("worker_id", "unknown"))}
                    for st in completed]
        time.sleep(check_interval)


def process_job(api: BeehiveAPIClient, client: ollama.Client, job_data: dict) -> None:
    job_id = job_data["id"]
    nectar = job_data["nectar"]
    media_type, url = parse_multimedia_nectar(nectar)
    if media_type is None:
        console.print(f"[dim]Job #{job_id} is not multimedia — skipping.[/dim]")
        return

    console.print(f"\n[bold green]🍯 Queen picking up multimedia job #{job_id} ({media_type})[/bold green]")
    console.print(f"[dim]URL: {url}[/dim]")

    api.claim_job(job_id)
    api.update_job_status(job_id, "splitting")

    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        ext = {"photo": ".jpg", "sound": ".mp3", "video": ".mp4"}[media_type]
        local = tdp / f"source{ext}"
        fetch_file(url, local)
        console.print(f"  [cyan]Queen fetched source file ({local.stat().st_size/1024:.0f} KB)[/cyan]")

        gestalt_vis, gestalt_aud = "", ""
        if media_type == "photo":
            gestalt_vis, tile_texts = split_photo(url, local, client)
        elif media_type == "sound":
            gestalt_aud, _, tile_texts = split_sound(url, local)
        else:  # video
            gestalt_aud, gestalt_vis, tile_texts = split_video(url, local, client)

        console.print(f"  [cyan]Queen split into {len(tile_texts)} tile subtasks[/cyan]")

    created = api.create_subtasks(job_id, tile_texts)
    subtask_ids = [c["id"] for c in created]
    api.update_job_status(job_id, "processing")
    console.print(f"  [cyan]Created {len(subtask_ids)} MULTIMEDIA_TILE subtasks — waiting for Workers...[/cyan]")

    tile_results = wait_for_subtasks(api, job_id, subtask_ids, timeout=SUBTASK_TIMEOUT)

    api.update_job_status(job_id, "combining")
    console.print(f"  [cyan]Queen integrating {len(tile_results)} tile reports onto her gestalt...[/cyan]")
    honey = integrate(client, media_type, gestalt_vis, gestalt_aud, tile_results)

    api.complete_job(job_id, honey)
    console.print(f"[bold green]✅ Job #{job_id} complete — {len(honey)} chars of Honey delivered.[/bold green]")


def main() -> int:
    api = BeehiveAPIClient(WEBSITE)
    data = api.login(QUEEN_EMAIL, QUEEN_PASSWORD)
    client = ollama.Client()
    console.print(Panel(
        f"[bold yellow]👑 Multimedia Queen Bee started[/]\n"
        f"Logged in as {data['username']} (role={data['role']})\n"
        f"Hive #{HIVE_ID}, poll every {POLL_INTERVAL}s",
        border_style="yellow"))

    while True:
        try:
            jobs = api.get_pending_jobs(HIVE_ID)
            multimedia_jobs = []
            for j in jobs:
                mt, _ = parse_multimedia_nectar(j.get("nectar", ""))
                if mt is not None:
                    multimedia_jobs.append(j)
            if not multimedia_jobs:
                time.sleep(POLL_INTERVAL)
                continue
            for job in multimedia_jobs:
                try:
                    process_job(api, client, job)
                except Exception as e:
                    console.print(f"[bold red]Job #{job.get('id')} failed: {e}[/bold red]")
                    try:
                        api.update_job_status(job["id"], "failed")
                    except Exception:
                        pass
        except KeyboardInterrupt:
            console.print("\n[yellow]Queen shutting down.[/yellow]")
            return 0
        except Exception as e:
            console.print(f"[red]Queen poll error: {e}. Retry in {POLL_INTERVAL}s[/red]")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    raise SystemExit(main())
