"""
tier_timeouts.py — Per-call Ollama timeout table for the GiantHoneyBee hive.

Importable from both HoneycombOfAI/ (OllamaClient consumers) and
GiantHoneyBee/ tier clients (which sys.path.insert HoneycombOfAI/).

Usage:
    from tier_timeouts import TIMEOUTS
    result = self.ai.generate(model=..., prompt=...,
                              timeout_sec=TIMEOUTS["text_calibration"])

Circuit-breaker ceilings (for component wall-clock checks) are
3 × the relevant gestalt timeout per tier.
"""

TIMEOUTS: dict[str, int] = {
    # ── Text ──────────────────────────────────────────────────────────────────
    "text_calibration":    60,    # simple calibration Q&A
    "text_integration":   120,    # non-leaf tier combining children's text

    # ── Photo ─────────────────────────────────────────────────────────────────
    "photo_worker_tile":  120,    # Worker: vision call on a 384×384 tile
    "photo_dq_gestalt":   120,    # DwarfQueen: vision gestalt (512×512)
    "photo_gq_gestalt":   180,    # GiantQueen: vision gestalt (768×768)
    "photo_raja_gestalt": 300,    # Raja: vision gestalt (1024×1024)

    # ── Audio (tier_audio.py, to be built) ────────────────────────────────────
    "audio_worker_slice":  60,
    "audio_dq_gestalt":   120,
    "audio_gq_gestalt":   180,
    "audio_raja_gestalt": 300,

    # ── Video ─────────────────────────────────────────────────────────────────
    "video_worker_clip":  180,
    "video_dq_gestalt":   180,
    "video_gq_gestalt":   300,
    "video_raja_gestalt": 300,

    # ── Fallback ──────────────────────────────────────────────────────────────
    "default":            120,
}

# Circuit-breaker wall-clock ceiling per tier = 3 × gestalt timeout.
# These are NOT Ollama call timeouts — they guard the entire component
# processing loop (download + vision + cut + upload + wait + integrate).
CIRCUIT_BREAKER: dict[str, int] = {
    "worker":       3 * TIMEOUTS["photo_worker_tile"],   # 360s
    "dwarf_queen":  3 * TIMEOUTS["photo_dq_gestalt"],    # 360s
    "giant_queen":  3 * TIMEOUTS["photo_gq_gestalt"],    # 540s
    "raja":         3 * TIMEOUTS["photo_raja_gestalt"],  # 900s
}
