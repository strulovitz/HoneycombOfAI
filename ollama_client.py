"""
ollama_client.py — Ollama AI Backend
=====================================
Connects to Ollama (the local AI engine) using the official Python library.
Extends the AIBackend base class.

Auto-safeguards (applied uniformly to all callers):
  - /no_think auto-prepend for qwen3 family (covers qwen3:Xb, qwen3-vl:Xb,
    qwen3.5:Xb). Case-insensitive. Logged at DEBUG level.
  - Per-call timeout_sec (default 120s) enforced via a fresh httpx-backed
    ollama.Client created for each call. The HTTP connection is actually
    killed on timeout — not just abandoned in the background.
  - On timeout: returns a structured error object with _timed_out=True.
  - On other errors: returns a structured error object with _error=<str>.
  - Fallback: if response is empty but thinking is non-empty, thinking is
    promoted to response (logged at WARNING level).
"""

import logging
import ollama
from ai_backend import AIBackend

logger = logging.getLogger(__name__)

# ── Sentinel response object ───────────────────────────────────────────────────

class _OllamaResult:
    """Lightweight return type for generate() / chat().

    Always has .response (str) and .thinking (str).
    On timeout: ._timed_out = True
    On error:   ._error = <str>
    """
    def __init__(self, response: str = "", thinking: str = "",
                 timed_out: bool = False, error: str = ""):
        self.response = response
        self.thinking = thinking
        self._timed_out = timed_out if timed_out else None   # None means no timeout
        self._error = error if error else None               # None means no error

    def __repr__(self):
        if self._timed_out:
            return f"<OllamaResult TIMED_OUT>"
        if self._error:
            return f"<OllamaResult ERROR={self._error[:60]}>"
        return f"<OllamaResult response={self.response[:60]!r}>"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _is_qwen3(model: str) -> bool:
    """Return True if model is in the qwen3 family (needs /no_think)."""
    return model.lower().startswith("qwen3")


def _ensure_no_think(prompt: str, model: str) -> str:
    """Prepend /no_think to prompt for qwen3 family if not already present."""
    if _is_qwen3(model) and not prompt.lstrip().startswith("/no_think"):
        logger.debug("[OLLAMA] Auto-prepending /no_think for model=%s", model)
        return "/no_think " + prompt
    return prompt


def _make_client(base_url: str, timeout_sec: float) -> ollama.Client:
    """Create a fresh ollama.Client with the given timeout.

    A fresh client is required per-call because the ollama Python library
    sets timeout at Client construction (httpx-backed). This is the only
    way to actually kill the underlying HTTP connection on timeout.
    """
    return ollama.Client(host=base_url, timeout=timeout_sec)


def _extract_text(resp) -> tuple[str, str]:
    """Extract (response_text, thinking_text) from an ollama response object."""
    response_text = ""
    thinking_text = ""
    if hasattr(resp, "response"):
        response_text = (resp.response or "").strip()
    if hasattr(resp, "thinking"):
        thinking_text = (getattr(resp, "thinking", "") or "").strip()
    elif hasattr(resp, "message"):
        # chat() returns message.content
        msg = resp.message
        if hasattr(msg, "content"):
            response_text = (msg.content or "").strip()
        if hasattr(msg, "thinking"):
            thinking_text = (getattr(msg, "thinking", "") or "").strip()
    return response_text, thinking_text


# ── Main client ────────────────────────────────────────────────────────────────

class OllamaClient(AIBackend):
    """Connects to Ollama and sends prompts to the AI model.

    All inference methods (generate, chat, ask) enforce:
      - /no_think auto-prepend for qwen3 family
      - Per-call timeout with graceful error return (never raises on timeout)
      - Thinking-to-response fallback when response is empty
    """

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        # Keep a persistent client for non-inference calls (list, is_available).
        # Inference calls create their own per-call clients with the right timeout.
        self.client = ollama.Client(host=base_url)

    # ── Inference: generate ────────────────────────────────────────────────────

    def generate(self, model: str, prompt: str,
                 timeout_sec: float = 120.0,
                 options: dict = None,
                 images: list = None,
                 **kwargs) -> _OllamaResult:
        """Call /api/generate. Returns _OllamaResult (never raises).

        Parameters
        ----------
        model       : Ollama model name.
        prompt      : The prompt string. /no_think is auto-prepended for qwen3.
        timeout_sec : HTTP timeout in seconds (default 120). The underlying
                      httpx connection is killed on expiry.
        options     : Ollama options dict (temperature, num_predict, etc.).
        images      : Optional list of image bytes for vision models.
        **kwargs    : Forwarded to ollama.Client.generate() (e.g. stream=False).
        """
        prompt = _ensure_no_think(prompt, model)
        call_opts = options or {}
        try:
            client = _make_client(self.base_url, timeout_sec)
            gen_kwargs = dict(
                model=model,
                prompt=prompt,
                options=call_opts,
                **kwargs,
            )
            if images is not None:
                gen_kwargs["images"] = images
            resp = client.generate(**gen_kwargs)
            response_text, thinking_text = _extract_text(resp)

            # Fallback: promote thinking to response when response is empty
            if not response_text and thinking_text:
                logger.warning(
                    "[OLLAMA] model=%s: response empty, promoting thinking (%d chars)",
                    model, len(thinking_text)
                )
                response_text = thinking_text

            return _OllamaResult(response=response_text, thinking=thinking_text)

        except Exception as e:
            err_str = str(e)
            # httpx raises ReadTimeout / TimeoutException for per-request timeouts
            is_timeout = any(tok in type(e).__name__ for tok in
                             ("Timeout", "timeout", "ReadTimeout", "ConnectTimeout"))
            if not is_timeout:
                # Also catch by message string (belt-and-suspenders)
                is_timeout = "timeout" in err_str.lower()
            if is_timeout:
                logger.error("[OLLAMA TIMEOUT] model=%s after %.0fs", model, timeout_sec)
                return _OllamaResult(timed_out=True)
            else:
                logger.error("[OLLAMA ERROR] model=%s: %s", model, err_str)
                return _OllamaResult(error=err_str)

    # ── Inference: chat ────────────────────────────────────────────────────────

    def chat(self, model: str, messages: list,
             timeout_sec: float = 120.0,
             options: dict = None,
             **kwargs) -> _OllamaResult:
        """Call /api/chat. Returns _OllamaResult (never raises).

        The last user message's content gets /no_think prepended for qwen3.

        Parameters
        ----------
        model       : Ollama model name.
        messages    : List of {"role": ..., "content": ...} dicts.
        timeout_sec : HTTP timeout in seconds (default 120).
        options     : Ollama options dict.
        **kwargs    : Forwarded to ollama.Client.chat().
        """
        # Auto-prepend /no_think on the last user message for qwen3 family
        if _is_qwen3(model) and messages:
            messages = list(messages)  # shallow copy — don't mutate caller's list
            for i in reversed(range(len(messages))):
                if messages[i].get("role") == "user":
                    content = messages[i].get("content", "")
                    if not content.lstrip().startswith("/no_think"):
                        logger.debug(
                            "[OLLAMA] Auto-prepending /no_think in chat for model=%s", model
                        )
                        messages[i] = dict(messages[i], content="/no_think " + content)
                    break

        call_opts = options or {}
        try:
            client = _make_client(self.base_url, timeout_sec)
            resp = client.chat(
                model=model,
                messages=messages,
                options=call_opts,
                **kwargs,
            )
            response_text, thinking_text = _extract_text(resp)

            if not response_text and thinking_text:
                logger.warning(
                    "[OLLAMA] model=%s: chat response empty, promoting thinking (%d chars)",
                    model, len(thinking_text)
                )
                response_text = thinking_text

            return _OllamaResult(response=response_text, thinking=thinking_text)

        except Exception as e:
            err_str = str(e)
            is_timeout = any(tok in type(e).__name__ for tok in
                             ("Timeout", "timeout", "ReadTimeout", "ConnectTimeout"))
            if not is_timeout:
                is_timeout = "timeout" in err_str.lower()
            if is_timeout:
                logger.error("[OLLAMA TIMEOUT] model=%s after %.0fs", model, timeout_sec)
                return _OllamaResult(timed_out=True)
            else:
                logger.error("[OLLAMA ERROR] model=%s: %s", model, err_str)
                return _OllamaResult(error=err_str)

    # ── Backward-compat: ask() ─────────────────────────────────────────────────

    def ask(self, prompt: str, model: str = "llama3.2:3b",
            temperature: float = 0.7,
            timeout_sec: float = 120.0) -> str:
        """Simple text-in / text-out wrapper. Returns str (empty string on error).

        Existing callers that pass (prompt=, model=, temperature=) continue to
        work unchanged. timeout_sec defaults to 120s.
        """
        result = self.generate(
            model=model,
            prompt=prompt,
            timeout_sec=timeout_sec,
            options={"temperature": temperature},
        )
        if result._timed_out:
            return f"[TIMEOUT after {timeout_sec:.0f}s]"
        if result._error:
            return f"[ERROR] {result._error}"
        return result.response

    # ── Non-inference helpers (unchanged) ──────────────────────────────────────

    def is_available(self) -> bool:
        try:
            self.client.list()
            return True
        except Exception:
            return False

    def list_models(self) -> list:
        try:
            models = self.client.list()
            return [m.model for m in models.models] if hasattr(models, 'models') else []
        except Exception:
            return []

    def backend_name(self) -> str:
        return "Ollama"
