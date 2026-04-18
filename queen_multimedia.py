"""
queen_multimedia.py — The Queen Bee for multimedia Jobs.

Watches a BeehiveOfAI hive for pending Jobs whose Nectar carries a
'[multimedia:<type>] ... url=<url>' marker (produced by
BeehiveOfAI /hive/<id>/submit-multimedia). For each such Job:

  1. Claims the Job and fetches the file over HTTP.
  2. Runs her OWN low-fidelity gestalt pass with the Queen-tier models
     (qwen3-vl:8b for photo/video, whisper-large-v3-turbo for sound/video).
     Ch 15 slippery point 2: "every tier perceives, with its own model."
  3. Splits the input into N tile subtasks, preserving the Grid A + Grid B
     double-grid from Book 1 Ch 12 (dog-under-the-table fix):
        - Photo: 4 Grid-A quadrants + 4 Grid-B straddling tiles = 8 tiles.
        - Sound: ceil(dur) Grid-A 1-sec slices + floor(dur) Grid-B 0.5-offset
          1-sec slices.
        - Video: 1 frame per 5 sec Grid-A + offset frames at 2.5s Grid-B,
          plus audio slices identical to the sound case.
  4. Creates tile subtasks on the website via api.create_subtasks. Each
     MULTIMEDIA_TILE subtask carries (url, crop|start|duration|timestamp)
     so Worker Bees crop/slice locally and run ONE model pass each.
  5. Waits for every tile subtask to reach status=completed.
  6. Integrates the workers' tile texts onto her own gestalt map using
     phi4-mini:3.8b, then calls api.complete_job with the final Honey.

Run: python3 queen_multimedia.py
Requires queen1@test.com credentials (queen of hive 1 per seed_data).
"""
import io
import math
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

# Models — Queen runs the biggest her host affords (Ch 15 slippery point 3).
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
SUBTASK_TIMEOUT = 900  # 15 minutes — some modalities spawn many tiles


# ---------- helpers ----------

def parse_multimedia_nectar(nectar: str) -> tuple[str | None, str | None]:
    m = re.search(r"\[multimedia:(photo|sound|video)\]", nectar)
    if not m:
        return None, None
    media_type = m.group(1)
    m2 = re.search(r"url=(\S+)", nectar)
    url = m2.group(1) if m2 else None
    return media_type, url


def fetch_file(url: str, dest: Path) -> None:
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    dest.write_bytes(r.content)


def img_to_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def queen_vision(client: ollama.Client, img: Image.Image, prompt: str) -> str:
    resp = client.generate(model=QUEEN_VISION, prompt=prompt,
                           images=[img_to_bytes(img)], options={"temperature": 0.2})
    return resp.response.strip()


def queen_text(client: ollama.Client, prompt: str, num_predict: int = 600) -> str:
    resp = client.generate(
        model=QUEEN_TEXT,
        prompt=prompt,
        options={"temperature": 0.3, "num_predict": num_predict, "num_ctx": 8192},
    )
    return resp.response.strip()


def queen_whisper(wav_path: Path) -> str:
    r = subprocess.run(
        [str(WHISPER_BIN), "-m", str(WHISPER_MODEL), "-f", str(wav_path), "-nt"],
        capture_output=True, text=True,
    )
    return r.stdout.strip()


def make_tile_text(media_type: str, label: str, url: str, params: dict) -> str:
    """Build a MULTIMEDIA_TILE:<...> subtask string. Pipes separate params so
    crop rectangles 'x1,y1,x2,y2' don't collide with the separator."""
    param_str = "|".join(f"{k}={v}" for k, v in params.items())
    return f"MULTIMEDIA_TILE:{media_type}:{label}:{url}|{param_str}"


# ---------- PHOTO split ----------

def split_photo(url: str, local_file: Path, client: ollama.Client) -> tuple[str, list[str]]:
    """Return (gestalt_text, list_of_tile_subtask_texts). 8 tiles = 4 Grid A + 4 Grid B."""
    img = Image.open(local_file).convert("RGB")
    W, H = img.size
    low = img.resize((W // 2, H // 2), Image.LANCZOS)
    gestalt = queen_vision(client, low,
                           "Describe the overall scene, layout, and what you see. 3-4 sentences.")
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


# ---------- SOUND split ----------

SOUND_SLICE_LEN = 5.0   # 5-second slices (Grid A)
SOUND_SLICE_OFFSET = 2.5  # Grid B offset = half slice, so boundaries recover


def split_sound(url: str, local_file: Path) -> tuple[str, float, list[str]]:
    """Return (gestalt_transcription, duration_sec, list_of_tile_subtasks).
    Grid A = 5-sec slices at integer step SOUND_SLICE_LEN. Grid B = same length
    shifted by half a slice (SOUND_SLICE_OFFSET). 1-sec was too short — produced
    hundreds of near-noise slices that drown the Queen's integration pass."""
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        full_wav = tdp / "full.wav"
        low_wav = tdp / "low.wav"
        subprocess.run(["ffmpeg", "-y", "-i", str(local_file), "-ac", "1", "-ar", "16000", "-vn", str(full_wav)],
                       capture_output=True, check=True)
        subprocess.run(["ffmpeg", "-y", "-i", str(local_file), "-ac", "1", "-ar", "8000", "-vn", str(low_wav)],
                       capture_output=True, check=True)
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=nw=1:nk=1", str(full_wav)], capture_output=True, text=True)
        dur = float(r.stdout.strip())
        gestalt = queen_whisper(low_wav)

    texts: list[str] = []
    # Grid A: 0, 5, 10, ... seconds
    s = 0.0
    while s + SOUND_SLICE_LEN <= dur:
        texts.append(make_tile_text("sound", f"A-{s:.1f}", url,
                                    {"start": f"{s:.1f}", "duration": f"{SOUND_SLICE_LEN:.1f}"}))
        s += SOUND_SLICE_LEN
    # Grid B: 2.5, 7.5, ... (offset by half a slice to catch anything split by Grid A cuts)
    s = SOUND_SLICE_OFFSET
    while s + SOUND_SLICE_LEN <= dur:
        texts.append(make_tile_text("sound", f"B-{s:.1f}", url,
                                    {"start": f"{s:.1f}", "duration": f"{SOUND_SLICE_LEN:.1f}"}))
        s += SOUND_SLICE_LEN
    return gestalt, dur, texts


# ---------- VIDEO split ----------

def split_video(url: str, local_file: Path) -> tuple[str, str, list[str]]:
    """Return (audio_gestalt, visual_gestalt_or_placeholder, list_of_tiles).

    Tiles:
      - Grid A keyframes at 0s, 5s, 10s, ... (photo-like tile subtasks)
      - Grid B keyframes at 2.5s, 7.5s, ... (offset)
      - Audio slices (sound-style tile subtasks) for the audio track.
    """
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        wav = tdp / "audio.wav"
        subprocess.run(["ffmpeg", "-y", "-i", str(local_file), "-ac", "1", "-ar", "16000", "-vn", str(wav)],
                       capture_output=True, check=True)
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=nw=1:nk=1", str(wav)], capture_output=True, text=True)
        dur = float(r.stdout.strip())
        audio_gestalt = queen_whisper(wav)

    texts: list[str] = []
    # Grid A keyframes every 5 s. Stop >= 0.5s BEFORE end-of-stream so ffmpeg
    # always has a real frame to extract (avoids stuck subtasks at dur=N.0).
    safe_end = max(0.0, dur - 0.5)
    t = 0.0
    while t <= safe_end:
        texts.append(make_tile_text("video-frame", f"KF-A-{int(t)}s", url,
                                    {"timestamp": f"{t:.1f}"}))
        t += 5.0
    # Grid B keyframes offset by 2.5 s
    t = 2.5
    while t <= safe_end:
        texts.append(make_tile_text("video-frame", f"KF-B-{t:.1f}s", url,
                                    {"timestamp": f"{t:.1f}"}))
        t += 5.0
    # Audio slices: 5-second slices with 2.5-sec offset (same as sound — avoids
    # the "too many short slices" failure mode that drowns the Queen integration).
    slice_len = SOUND_SLICE_LEN
    half = SOUND_SLICE_OFFSET
    s = 0.0
    while s + slice_len <= dur:
        texts.append(make_tile_text("video-audio", f"AU-A-{s:.1f}", url,
                                    {"start": f"{s:.1f}", "duration": f"{slice_len:.1f}"}))
        s += slice_len
    s = half
    while s + slice_len <= dur:
        texts.append(make_tile_text("video-audio", f"AU-B-{s:.1f}", url,
                                    {"start": f"{s:.1f}", "duration": f"{slice_len:.1f}"}))
        s += slice_len
    return audio_gestalt, "", texts


# ---------- integrate ----------

# ---------- hierarchical integration ----------
#
# phi4-mini (3.8B) drowns when given 300+ tile-lines in one prompt — it
# produces a partial transcription focused on the first cluster and stops.
# The book's Ch 13-14 recursive principle says: if a single integrator can't
# carry the load, add a tier. Here we add ONE sub-tier of integration
# (chunked pre-summaries), then a meta-integration over the chunk summaries.

CHUNK_SIZE = 20  # tile lines per sub-integration call


def _tile_label(subtask_text: str) -> str:
    m = re.match(r"MULTIMEDIA_TILE:[^:]+:([^:]+):", subtask_text)
    return m.group(1) if m else "?"


def _tile_timestamp(label: str) -> float:
    """Extract a rough timestamp from a tile label so we can sort and chunk in time order.
    Photo labels have no timestamp — return 0. Sound labels are 'A-<s>' or 'B-<s>'.
    Video labels are 'KF-A-<s>s', 'KF-B-<s>s', 'AU-A-<s>', 'AU-B-<s>'. Missing -> 0."""
    m = re.search(r"-(\d+(?:\.\d+)?)(?:s)?$", label)
    return float(m.group(1)) if m else 0.0


def _chunk_sub_integrate_sound(client, chunk_lines: list[str], chunk_idx: int, n_chunks: int) -> str:
    body = "\n".join(chunk_lines)
    prompt = f"""You are summarizing time-window {chunk_idx+1} of {n_chunks} from an audio recording.

Slice transcriptions (Grid A + Grid B overlapping 5-sec slices, may contain whisper-tiny errors):
{body}

Produce ONE coherent paragraph (2-4 sentences) of what was said in this time window. Preserve proper nouns, numbers, distinct phrases. Merge duplicates across overlapping A/B slices. If a slice is blank/noise, skip it."""
    return queen_text(client, prompt, num_predict=300)


def _chunk_sub_integrate_video(client, chunk_lines: list[str], chunk_idx: int, n_chunks: int) -> str:
    body = "\n".join(chunk_lines)
    prompt = f"""You are summarizing time-window {chunk_idx+1} of {n_chunks} from a short video.

Reports in this window mix keyframe descriptions (KF-*) and audio slice transcriptions (AU-*):
{body}

Produce ONE coherent paragraph (2-4 sentences) of what happens in this time window — both what is seen and what is heard. Merge duplicates across overlapping A/B tiles. If nothing interesting, say so briefly."""
    return queen_text(client, prompt, num_predict=300)


def _meta_integrate_sound(client, gestalt_aud: str, chunk_paragraphs: list[str]) -> str:
    sections = "\n\n".join(f"Window {i+1}:\n{p}" for i, p in enumerate(chunk_paragraphs))
    prompt = f"""You are the Queen Bee integrating an audio recording end-to-end.

Your own gestalt (whisper-large-v3-turbo on a low-rate copy of the WHOLE recording):
{gestalt_aud}

Chunk summaries from your DwarfQueens (each covers ~{CHUNK_SIZE} overlapping 5-sec slices in time order):
{sections}

Write one coherent transcription that COVERS THE ENTIRE RECORDING from start to finish. Use the gestalt as backbone and fill in detail from the chunk summaries. End with a 2-3 sentence summary of what the recording is about."""
    return queen_text(client, prompt, num_predict=2000)


def _meta_integrate_video(client, gestalt_aud: str, chunk_paragraphs: list[str]) -> str:
    sections = "\n\n".join(f"Window {i+1}:\n{p}" for i, p in enumerate(chunk_paragraphs))
    prompt = f"""You are the Queen Bee integrating a video end-to-end.

Audio gestalt (whisper-large-v3-turbo on the WHOLE audio track):
{gestalt_aud}

Chunk summaries from your DwarfQueens (each covers ~{CHUNK_SIZE} mixed visual+audio tiles in time order):
{sections}

Write one coherent narrative that COVERS THE ENTIRE VIDEO from start to finish. Weave visual and audio into a single time-ordered story. End with a 2-3 sentence summary."""
    return queen_text(client, prompt, num_predict=2000)


def integrate(client: ollama.Client, media_type: str, gestalt_vis: str, gestalt_aud: str,
              tile_results: list[dict]) -> str:
    # tile_results: [{'subtask': text, 'result': text, 'worker_id': str}]

    if media_type == "photo":
        # Photo has at most 8 tiles — fits easily in one phi4-mini call, no
        # hierarchical tier needed. Keep the original single-pass integration.
        lines = []
        for tr in tile_results:
            label = _tile_label(tr['subtask'])
            lines.append(f"- {label} (worker {tr.get('worker_id')}): {tr['result'].splitlines()[0][:220]}")
        tile_section = "\n".join(lines)
        prompt = f"""You are the Queen Bee integrating a photo analysis from a hive of tile-worker Bees.

Your own gestalt (Queen ran qwen3-vl on a low-resolution copy of the whole photo):
{gestalt_vis}

Tile reports (Grid A = 4 quadrants A-UL/A-UR/A-LL/A-LR; Grid B = 4 straddling tiles B-TOP-MID/B-BOT-MID/B-LEFT-MID/B-RIGHT-MID at 25% offsets to recover anything Grid A sliced in half — the dog-under-the-table fix):
{tile_section}

Produce one coherent description. Use your own gestalt as the spatial map, place tile-detail onto it, merge duplicates between overlapping A and B tiles. Do NOT emit tile labels in the output. 5-8 sentences."""
        return queen_text(client, prompt, num_predict=800)

    # Sound / video — sort tiles by time and chunk for hierarchical integration.
    sorted_tiles = sorted(
        tile_results,
        key=lambda tr: _tile_timestamp(_tile_label(tr['subtask'])),
    )
    lines = []
    for tr in sorted_tiles:
        label = _tile_label(tr['subtask'])
        snippet = tr['result'].splitlines()[0][:220] if tr['result'] else ""
        lines.append(f"- {label}: {snippet}")

    # If the input fits in one call comfortably, skip the hierarchical layer.
    if len(lines) <= CHUNK_SIZE:
        body = "\n".join(lines)
        if media_type == "sound":
            prompt = f"""You are the Queen integrating an audio recording from a hive of slice-worker Bees.

Your gestalt (whisper-large-v3-turbo on a low-rate copy of the whole recording):
{gestalt_aud}

Slice transcriptions (Grid A + Grid B overlapping 5-sec slices, in time order):
{body}

Produce one final transcription covering the whole recording. De-duplicate overlapping A/B slices. End with a 1-2 sentence summary."""
        else:  # video
            prompt = f"""You are the Queen integrating a short video from a hive of tile-worker Bees.

Audio gestalt (whisper-large-v3-turbo on whole audio):
{gestalt_aud}

Tile reports mixing keyframes (KF-*) and audio slices (AU-*) in time order:
{body}

Produce a coherent narrative from start to finish. Do NOT emit tile labels. 4-8 sentences."""
        return queen_text(client, prompt, num_predict=1200)

    # Hierarchical path: chunk -> sub-integrate each chunk -> meta-integrate.
    chunks = [lines[i:i+CHUNK_SIZE] for i in range(0, len(lines), CHUNK_SIZE)]
    console.print(f"  [cyan]Hierarchical integration: {len(lines)} tiles -> {len(chunks)} chunks of ~{CHUNK_SIZE}[/cyan]")
    chunk_paragraphs: list[str] = []
    sub_fn = _chunk_sub_integrate_sound if media_type == "sound" else _chunk_sub_integrate_video
    for idx, chunk in enumerate(chunks):
        t0 = time.monotonic()
        para = sub_fn(client, chunk, idx, len(chunks))
        chunk_paragraphs.append(para)
        console.print(f"    [dim]sub-integration {idx+1}/{len(chunks)} done in {time.monotonic()-t0:.1f}s[/dim]")

    meta_fn = _meta_integrate_sound if media_type == "sound" else _meta_integrate_video
    return meta_fn(client, gestalt_aud, chunk_paragraphs)


# ---------- main Queen loop ----------

def wait_for_subtasks(api: BeehiveAPIClient, job_id: int, subtask_ids: list[int],
                      timeout: int, check_interval: int = 4) -> list[dict]:
    start = time.time()
    while True:
        elapsed = time.time() - start
        if elapsed > timeout:
            raise TimeoutError(f"Subtasks not completed within {timeout}s")
        subtasks = api.get_job_subtasks(job_id)
        relevant = [st for st in subtasks if st['id'] in subtask_ids]
        completed = [st for st in relevant if st['status'] == 'completed']
        console.print(f"  [dim]progress {len(completed)}/{len(relevant)} done ({int(elapsed)}s)[/dim]")
        if len(completed) == len(relevant):
            return [{"subtask": st['subtask_text'], "result": st['result_text'] or '',
                     "worker_id": str(st.get('worker_id', 'unknown'))}
                    for st in completed]
        time.sleep(check_interval)


def process_job(api: BeehiveAPIClient, client: ollama.Client, job_data: dict) -> None:
    job_id = job_data['id']
    nectar = job_data['nectar']
    media_type, url = parse_multimedia_nectar(nectar)
    if media_type is None:
        console.print(f"[dim]Job #{job_id} is not multimedia — skipping.[/dim]")
        return

    console.print(f"\n[bold green]🍯 Queen picking up multimedia job #{job_id} ({media_type})[/bold green]")
    console.print(f"[dim]URL: {url}[/dim]")

    api.claim_job(job_id)
    api.update_job_status(job_id, 'splitting')

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
            gestalt_aud, _, tile_texts = split_video(url, local)
            # Optional: also compute a visual gestalt on the middle keyframe for video (cheap extra richness)

        console.print(f"  [cyan]Queen split into {len(tile_texts)} tile subtasks[/cyan]")

    # Create subtasks on website
    created = api.create_subtasks(job_id, tile_texts)
    subtask_ids = [c['id'] for c in created]
    api.update_job_status(job_id, 'processing')
    console.print(f"  [cyan]Created {len(subtask_ids)} MULTIMEDIA_TILE subtasks — waiting for Workers...[/cyan]")

    # Wait for all workers to finish
    tile_results = wait_for_subtasks(api, job_id, subtask_ids, timeout=SUBTASK_TIMEOUT)

    # Integrate
    api.update_job_status(job_id, 'combining')
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
                mt, _ = parse_multimedia_nectar(j.get('nectar', ''))
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
                        api.update_job_status(job['id'], 'failed')
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
