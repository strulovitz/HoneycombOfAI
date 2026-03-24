"""
openai_compat_backend.py — OpenAI-Compatible AI Backend
========================================================
Handles LM Studio, llama.cpp server, and vLLM.
All three use the same OpenAI-compatible REST API format.
Uses the 'requests' library — does NOT depend on the 'openai' package.
"""

import time
import requests
from ai_backend import AIBackend

# Default ports for each backend type
DEFAULT_PORTS = {
    "lmstudio": 1234,
    "llamacpp": 8080,
    "vllm": 8000,
}

# Display names
DISPLAY_NAMES = {
    "lmstudio": "LM Studio",
    "llamacpp": "llama.cpp",
    "vllm": "vLLM",
}


class OpenAICompatBackend(AIBackend):
    """
    AI backend for any server that speaks the OpenAI-compatible API.
    Works with LM Studio, llama.cpp server (llama-server), and vLLM.
    """

    def __init__(self, base_url: str = None, backend_type: str = "lmstudio",
                 api_key: str = None, timeout: int = 120):
        """
        Args:
            base_url: Full URL like "http://localhost:1234". If None, uses default port for backend_type.
            backend_type: One of "lmstudio", "llamacpp", "vllm"
            api_key: Optional API key (vLLM can require one)
            timeout: Request timeout in seconds (default 120 — LLMs can be slow)
        """
        if backend_type not in DEFAULT_PORTS:
            raise ValueError(f"Unknown backend_type: {backend_type}. Must be one of: {list(DEFAULT_PORTS.keys())}")

        self.backend_type = backend_type
        self.timeout = timeout

        if base_url is None:
            port = DEFAULT_PORTS[backend_type]
            base_url = f"http://localhost:{port}"

        # Ensure no trailing slash
        self.base_url = base_url.rstrip("/")

        # Build headers
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    def ask(self, prompt: str, model: str = None, temperature: float = 0.7) -> str:
        """Send a chat completion request."""
        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        if model:
            payload["model"] = model

        try:
            resp = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                headers=self.headers,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except requests.exceptions.ConnectionError:
            return f"[ERROR] Cannot connect to {self.backend_name()} at {self.base_url}"
        except requests.exceptions.Timeout:
            return f"[ERROR] Request to {self.backend_name()} timed out after {self.timeout}s"
        except Exception as e:
            return f"[ERROR] {self.backend_name()} request failed: {str(e)}"

    def is_available(self) -> bool:
        """Check if the server is running by hitting the models endpoint."""
        try:
            resp = requests.get(
                f"{self.base_url}/v1/models",
                headers=self.headers,
                timeout=5,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list:
        """Get available models from the server."""
        try:
            resp = requests.get(
                f"{self.base_url}/v1/models",
                headers=self.headers,
                timeout=5,
            )
            resp.raise_for_status()
            data = resp.json()
            # OpenAI format: {"data": [{"id": "model-name", ...}, ...]}
            if "data" in data:
                return [m["id"] for m in data["data"]]
            # Some servers use "models" key instead
            if "models" in data:
                return [m.get("id") or m.get("name", "unknown") for m in data["models"]]
            return []
        except Exception:
            return []

    def backend_name(self) -> str:
        return DISPLAY_NAMES.get(self.backend_type, self.backend_type)

    def benchmark(self, test_prompt: str = "Explain what honey is in exactly 3 sentences.",
                  model: str = None) -> dict:
        """Benchmark with tokens/sec extraction from the API response."""
        result = {
            "backend": self.backend_name(),
            "model": model or "default",
            "available": False,
            "response_time_seconds": 0.0,
            "response_length": 0,
            "tokens_per_second": None,
        }

        if not self.is_available():
            return result

        result["available"] = True

        payload = {
            "messages": [{"role": "user", "content": test_prompt}],
            "temperature": 0.5,
        }
        if model:
            payload["model"] = model

        try:
            start = time.time()
            resp = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                headers=self.headers,
                timeout=self.timeout,
            )
            elapsed = time.time() - start
            resp.raise_for_status()
            data = resp.json()

            result["response_time_seconds"] = round(elapsed, 2)
            content = data["choices"][0]["message"]["content"]
            result["response_length"] = len(content)

            # Try to extract tokens/sec from response
            # llama.cpp includes "timings" with predicted_per_second
            if "timings" in data:
                tps = data["timings"].get("predicted_per_second")
                if tps:
                    result["tokens_per_second"] = round(tps, 1)

            # Try from usage info
            usage = data.get("usage", {})
            if usage and "completion_tokens" in usage and elapsed > 0:
                if result["tokens_per_second"] is None:
                    result["tokens_per_second"] = round(usage["completion_tokens"] / elapsed, 1)

            result["model"] = data.get("model", model or "unknown")

        except Exception:
            pass

        return result
