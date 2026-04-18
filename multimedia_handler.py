"""
multimedia_handler.py — Handle multimedia input (photo/sound/video) inside a Worker Bee.

The Worker Bee detects subtasks whose text starts with 'MULTIMEDIA:<type>:<url>'
and routes them to this module. Each handler:
  1. Fetches the file via HTTP from BeehiveOfAI's /uploads/<filename> endpoint
  2. Runs the recursive sub-sampling trick (chapter 12-15 of TheDistributedAIRevolution)
  3. Returns a text description

The recursive trick: give the Queen-tier model a low-fidelity GESTALT view,
give Worker-tier processes high-fidelity pieces of the input (image tiles for
photos — spatial regions; audio slices for sound — temporal windows; video
clips for video — temporal windows covering the whole frame), integrate child
reports onto the Queen's spatial/temporal map.

For Phase 5 Stage 4 MVP, one Worker runs the whole recursive pipeline sequentially
(Chapter 15's "cheap-test-bench" configuration). A future phase would distribute
the per-modality Worker subtasks to multiple Worker Bees via sub-sub-subtasks over
the BeehiveOfAI API.
"""
import io
import math
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from PIL import Image

# Models — aligned with ~/claude-memory and the VM cluster setup.
# Inside the Worker, we play both Queen and Worker roles sequentially.
VISION_MODEL = "qwen3-vl:8b"          # Queen-tier vision (also used for Worker subtasks on 24GB GPU)
TEXT_MODEL = "phi4-mini:3.8b"         # Text reasoner for integration

# whisper.cpp (CUDA-built) is expected at ~/multimedia-feasibility/whisper.cpp
# (Stage 0 installed it there). Keeping this path discoverable until the Worker
# config grows a proper field.
WHISPER_ROOT = Path.home() / "multimedia-feasibility" / "whisper.cpp"
WHISPER_BIN = WHISPER_ROOT / "build" / "bin" / "whisper-cli"
WHISPER_MODEL_Q = WHISPER_ROOT / "models" / "ggml-large-v3-turbo-q5_0.bin"


def _img_to_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def _run_ollama_vision(client, img: Image.Image, prompt: str) -> str:
    resp = client.generate(
        model=VISION_MODEL,
        prompt=prompt,
        images=[_img_to_bytes(img)],
        options={"temperature": 0.2},
    )
    return resp.response.strip()


def _run_ollama_text(client, prompt: str) -> str:
    resp = client.generate(
        model=TEXT_MODEL,
        prompt=prompt,
        options={"temperature": 0.3},
    )
    return resp.response.strip()


def _run_whisper(wav_path: Path) -> str:
    r = subprocess.run(
        [str(WHISPER_BIN), "-m", str(WHISPER_MODEL_Q), "-f", str(wav_path), "-nt"],
        capture_output=True, text=True,
    )
    return r.stdout.strip()


def _fetch_file(url: str, dest: Path) -> None:
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    dest.write_bytes(r.content)


# ---------- PHOTO ----------

def handle_photo(jpeg_path: Path, client) -> str:
    img = Image.open(jpeg_path).convert("RGB")
    W, H = img.size

    # 1. Gestalt on low-res whole image
    low = img.resize((W // 2, H // 2), Image.LANCZOS)
    gestalt = _run_ollama_vision(client, low, "Describe the overall scene, layout, and what you see. 3-4 sentences.")

    # 2. Double-grid image tiles (4 Grid A quadrants + 4 Grid B straddling tiles — these ARE spatial regions of the photo)
    qw, qh = W // 4, H // 4
    tiles = [
        ("A-UL", img.crop((0, 0, W // 2, H // 2))),
        ("A-UR", img.crop((W // 2, 0, W, H // 2))),
        ("A-LL", img.crop((0, H // 2, W // 2, H))),
        ("A-LR", img.crop((W // 2, H // 2, W, H))),
        ("B-TOP-MID", img.crop((qw, 0, W - qw, H // 2))),
        ("B-BOT-MID", img.crop((qw, H // 2, W - qw, H))),
        ("B-LEFT-MID", img.crop((0, qh, W // 2, H - qh))),
        ("B-RIGHT-MID", img.crop((W // 2, qh, W, H - qh))),
    ]
    tile_descs: list[tuple[str, str]] = []
    for name, tile in tiles:
        desc = _run_ollama_vision(client, tile, "Describe what you see in this image region in one sentence.")
        tile_descs.append((name, desc))

    # 3. Integrate
    tile_section = "\n".join(f"- {n}: {d}" for n, d in tile_descs)
    prompt = f"""Integrate a photo's vision analysis from a hive of tile-Workers.

Gestalt (low-resolution overview of the whole photo):
{gestalt}

Image tile reports (Grid A = 4 quadrants; Grid B = 4 tiles at 25% offset to recover anything Grid A sliced in half):
{tile_section}

Produce one coherent description. Use the gestalt as your spatial map. Merge duplicates across overlapping tiles. Do not emit tile labels. 5-8 sentences."""
    return _run_ollama_text(client, prompt)


# ---------- SOUND ----------

def handle_sound(audio_path: Path, client) -> str:
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        full_wav = tdp / "full.wav"
        low_wav = tdp / "low.wav"
        subprocess.run(["ffmpeg", "-y", "-i", str(audio_path), "-ac", "1", "-ar", "16000", "-vn", str(full_wav)],
                       capture_output=True, check=True)
        subprocess.run(["ffmpeg", "-y", "-i", str(audio_path), "-ac", "1", "-ar", "8000", "-vn", str(low_wav)],
                       capture_output=True, check=True)
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=nw=1:nk=1", str(full_wav)], capture_output=True, text=True)
        dur = float(r.stdout.strip())

        # Gestalt pass on low-rate whole recording
        gestalt = _run_whisper(low_wav)

        # Grid A at integer seconds, grid B at .5 offsets
        slice_len = 1.0
        offset = 0.5
        slice_reports: list[tuple[float, str, str]] = []
        for start in range(int(math.ceil(dur))):
            if start + slice_len <= dur:
                slice_wav = tdp / f"slice_A_{start}.wav"
                subprocess.run(["ffmpeg", "-y", "-i", str(full_wav), "-ss", str(start), "-t", str(slice_len),
                                "-ac", "1", "-ar", "16000", str(slice_wav)], capture_output=True, check=True)
                slice_reports.append((float(start), "A", _run_whisper(slice_wav)))
        for start in range(int(math.floor(dur))):
            s = start + offset
            if s + slice_len <= dur:
                slice_wav = tdp / f"slice_B_{s:.1f}.wav"
                subprocess.run(["ffmpeg", "-y", "-i", str(full_wav), "-ss", str(s), "-t", str(slice_len),
                                "-ac", "1", "-ar", "16000", str(slice_wav)], capture_output=True, check=True)
                slice_reports.append((s, "B", _run_whisper(slice_wav)))

        slice_reports.sort(key=lambda x: (x[0], x[1]))
        slice_section = "\n".join(f"- t={s:.1f}s ({lbl}): {txt}" for s, lbl, txt in slice_reports)
        prompt = f"""Integrate an audio recording's analysis from a hive of slice-workers.

Gestalt (whisper-large-v3-turbo on low-rate whole recording):
{gestalt}

Slice transcriptions (grid A at integer seconds + grid B at .5 offsets to catch words grid A split):
{slice_section}

Produce one final transcription. De-duplicate words appearing in overlapping A/B slices. End with a 1-2 sentence summary."""
        return _run_ollama_text(client, prompt)


# ---------- VIDEO ----------

def handle_video(video_path: Path, client) -> str:
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        wav = tdp / "audio.wav"
        frames_dir = tdp / "frames"
        frames_dir.mkdir()

        subprocess.run(["ffmpeg", "-y", "-i", str(video_path), "-ac", "1", "-ar", "16000", "-vn", str(wav)],
                       capture_output=True, check=True)
        subprocess.run(["ffmpeg", "-y", "-i", str(video_path), "-vf", "fps=1/5",
                        str(frames_dir / "frame_%03d.jpg")], capture_output=True, check=True)
        frames = sorted(frames_dir.glob("*.jpg"))

        audio_gestalt = _run_whisper(wav)

        visual: list[tuple[int, str]] = []
        for i, fp in enumerate(frames):
            img = Image.open(fp).convert("RGB")
            desc = _run_ollama_vision(client, img, "Describe this video frame in one sentence.")
            visual.append((i * 5, desc))

        visual_section = "\n".join(f"- t={ts}s: {d}" for ts, d in visual)
        prompt = f"""Integrate a short video's analysis.

Audio track (whisper-large-v3-turbo on whole audio):
{audio_gestalt if audio_gestalt else '(no clear speech)'}

Visual timeline (one description per keyframe every 5 seconds):
{visual_section}

Produce a coherent 3-6 sentence narrative combining audio and visuals."""
        return _run_ollama_text(client, prompt)


# ---------- dispatcher ----------

def handle_multimedia_subtask(subtask_text: str, ollama_client) -> str:
    """Legacy single-Worker path (old Stage 4 shortcut — do ALL pieces inside one Worker).

    Retained for fallback only. The real distributed path is `handle_multimedia_tile`
    below (one Worker = one modality-specific piece: an image tile, a sound slice,
    a video clip, or a video audio slice — as Book 1 Chapters 12-14 describe).
    """
    if not subtask_text.startswith("MULTIMEDIA:"):
        raise ValueError(f"Not a multimedia subtask: {subtask_text[:80]}")

    parts = subtask_text.split(":", 2)
    if len(parts) != 3:
        raise ValueError(f"Malformed multimedia subtask: {subtask_text[:80]}")
    _, media_type, url = parts
    url = url.strip()

    path = urlparse(url).path
    ext = Path(path).suffix or {"photo": ".jpg", "sound": ".mp3", "video": ".mp4"}.get(media_type, ".bin")

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / f"input{ext}"
        t0 = time.monotonic()
        _fetch_file(url, tmp)
        fetch_s = time.monotonic() - t0

        t0 = time.monotonic()
        if media_type == "photo":
            result = handle_photo(tmp, ollama_client)
        elif media_type == "sound":
            result = handle_sound(tmp, ollama_client)
        elif media_type == "video":
            result = handle_video(tmp, ollama_client)
        else:
            raise ValueError(f"Unknown media type: {media_type}")
        process_s = time.monotonic() - t0

    return f"{result}\n\n---\n[multimedia:{media_type}] fetched {fetch_s:.2f}s, processed {process_s:.2f}s"


# ---------- MULTIMEDIA_TILE protocol (one Worker = one modality-specific piece, distributed) ----------
#
# Terminology: the MULTIMEDIA_TILE: prefix is an opaque routing key preserved
# for wire compatibility. Inside, the concrete Worker unit depends on media_type:
#   photo       → image tile (a spatial region of the photo)
#   sound       → audio slice (a temporal window of audio)
#   video-clip  → video clip  (a short temporal window of the whole frame)
#   video-audio → audio slice (a temporal window of the video's audio track)

def _parse_params(params_str: str) -> dict:
    """Parse 'k1=v1|k2=v2' (pipe-separated) into a dict. Pipe is used instead of
    comma so crop rectangles written as 'x1,y1,x2,y2' in a single value don't
    collide with the separator."""
    out: dict[str, str] = {}
    if not params_str:
        return out
    for part in params_str.split("|"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def handle_multimedia_tile(subtask_text: str, ollama_client) -> str:
    """Process ONE Worker unit of a multimedia input.

    The Worker unit shape depends on the media_type carried in the subtask:
      - photo       → image tile (spatial crop of the photo)
      - sound       → audio slice (temporal window of audio)
      - video-clip  → video clip (temporal window covering the whole frame;
                      NOT a spatial crop of the screen)
      - video-audio → audio slice (temporal window of the video's audio track)

    Subtask text formats (emitted by the multimedia Queen):
      MULTIMEDIA_TILE:photo:<label>:<url>|crop=x1,y1,x2,y2
      MULTIMEDIA_TILE:sound:<label>:<url>|start=<s>|duration=<s>
      MULTIMEDIA_TILE:video-clip:<label>:<url>|start=<s>|duration=<s>|fps=<f>
      MULTIMEDIA_TILE:video-audio:<label>:<url>|start=<s>|duration=<s>

    The Worker fetches the FULL source file from <url>, extracts the specified
    tile/slice/clip locally, and runs ONE model pass on it. For video clips,
    "ONE model pass" means a single multi-frame qwen3-vl call on the frames
    sampled from inside the clip, so the Worker perceives MOTION rather than a
    still photograph. Returns the Worker-unit's text.
    """
    if not subtask_text.startswith("MULTIMEDIA_TILE:"):
        raise ValueError(f"Not a Worker-subtask: {subtask_text[:80]}")

    # Split on ':' but only the first 4 parts — the URL may contain colons (scheme)
    header, _, rest = subtask_text.partition(":")   # drops "MULTIMEDIA_TILE"
    media_type, _, rest = rest.partition(":")
    label, _, rest = rest.partition(":")
    # `rest` is now 'http://host/path|k=v|k=v'
    url_and_params = rest.split("|", 1)
    url = url_and_params[0].strip()
    params = _parse_params(url_and_params[1] if len(url_and_params) > 1 else "")

    path = urlparse(url).path
    ext_map = {"photo": ".jpg", "sound": ".mp3",
               "video-clip": ".mp4", "video-audio": ".mp4"}
    ext = Path(path).suffix or ext_map.get(media_type, ".bin")

    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        src = tdp / f"source{ext}"
        t0 = time.monotonic()
        _fetch_file(url, src)
        fetch_s = time.monotonic() - t0

        t0 = time.monotonic()
        if media_type == "photo":
            crop = params.get("crop")
            if not crop:
                raise ValueError(f"photo tile missing crop param (image tiles are spatial, need x1,y1,x2,y2): {subtask_text[:120]}")
            x1, y1, x2, y2 = (int(v) for v in crop.split(","))
            img = Image.open(src).convert("RGB").crop((x1, y1, x2, y2))
            desc = _run_ollama_vision(
                ollama_client, img,
                "Describe what you see in this image region in one sentence.",
            )
        elif media_type == "sound":
            start = float(params.get("start", "0"))
            duration = float(params.get("duration", "1"))
            slice_wav = tdp / "slice.wav"
            subprocess.run([
                "ffmpeg", "-y", "-i", str(src),
                "-ss", str(start), "-t", str(duration),
                "-ac", "1", "-ar", "16000", str(slice_wav)
            ], capture_output=True, check=True)
            desc = _run_whisper(slice_wav)
        elif media_type == "video-clip":
            # Motion-perceiving Worker: extract a short clip, sample several
            # frames from inside it, pass the frame sequence to a video-capable
            # vision model in ONE call. Worker sees motion, not stills.
            start = float(params.get("start", "0"))
            duration = float(params.get("duration", "3"))
            fps = float(params.get("fps", "2"))
            frame_dir = tdp / "frames"
            frame_dir.mkdir()
            subprocess.run([
                "ffmpeg", "-y", "-ss", str(start), "-i", str(src),
                "-t", str(duration), "-vf", f"fps={fps}",
                str(frame_dir / "frame_%03d.jpg"),
            ], capture_output=True, check=True)
            frame_paths = sorted(frame_dir.glob("frame_*.jpg"))
            if not frame_paths:
                desc = "(no frames extracted from clip)"
            else:
                frame_bytes = [fp.read_bytes() for fp in frame_paths]
                # /no_think so qwen3-vl returns the actual description,
                # not internal thinking tokens. Fall back to .thinking if empty.
                resp = ollama_client.generate(
                    model="qwen3-vl:8b",
                    prompt=(
                        f"/no_think These are {len(frame_bytes)} frames from a "
                        f"{duration:.1f}-second video clip in time order. Describe the "
                        "motion and actions across the frames in one or two sentences "
                        "— what moves, in what direction, who does what."
                    ),
                    images=frame_bytes,
                    options={"temperature": 0.1, "num_predict": 300, "num_ctx": 16384},
                )
                desc = (resp.response or "").strip()
                if not desc:
                    desc = (getattr(resp, "thinking", "") or "").strip() or "(empty)"
        elif media_type == "video-audio":
            start = float(params.get("start", "0"))
            duration = float(params.get("duration", "1"))
            slice_wav = tdp / "slice.wav"
            subprocess.run([
                "ffmpeg", "-y", "-i", str(src), "-vn",
                "-ss", str(start), "-t", str(duration),
                "-ac", "1", "-ar", "16000", str(slice_wav)
            ], capture_output=True, check=True)
            desc = _run_whisper(slice_wav)
        else:
            raise ValueError(f"Unknown Worker-subtask media_type: {media_type}")
        process_s = time.monotonic() - t0

    # Label the trailer with the actual Worker-unit kind rather than the generic "tile".
    unit_kind = {"photo": "image tile", "sound": "audio slice",
                 "video-clip": "video clip", "video-audio": "audio slice"}.get(media_type, media_type)
    return f"{desc}\n\n---\n[{unit_kind} {label}] fetched {fetch_s:.2f}s, processed {process_s:.2f}s"
