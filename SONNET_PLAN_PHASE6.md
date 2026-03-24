# Phase 6 Implementation Plan — For Sonnet 4.6
## Multi-Backend AI Support

**Created by:** Opus 4.6 (Laptop)
**Date:** 2026-03-24
**Instructions:** Follow each task in order. Do NOT skip steps. After each task, verify it works.

---

## TASK 1: Create `ai_backend.py` — Abstract Base Class

Create a new file `ai_backend.py` in the project root with:

```python
"""
ai_backend.py — Abstract Base Class for AI Backends
====================================================
Every AI backend (Ollama, LM Studio, llama.cpp, vLLM) must implement this interface.
The bees don't care which AI engine is behind the scenes — they just call these methods.
"""

import json
import re
import time
from abc import ABC, abstractmethod


class AIBackend(ABC):
    """Abstract base class that all AI backends must implement."""

    @abstractmethod
    def ask(self, prompt: str, model: str, temperature: float = 0.7) -> str:
        """Send a prompt to the AI and get a text response."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this backend is running and accessible."""
        pass

    @abstractmethod
    def list_models(self) -> list:
        """Get list of available models."""
        pass

    @abstractmethod
    def backend_name(self) -> str:
        """Return the display name of this backend (e.g. 'Ollama', 'LM Studio')."""
        pass

    def ask_for_json_list(self, prompt: str, model: str, temperature: float = 0.3) -> list:
        """
        Send a prompt and expect a JSON list back.

        This is a shared implementation — it calls ask() and parses the result.
        All backends inherit this; no need to override.
        """
        raw_response = self.ask(prompt, model, temperature)

        # Try to parse the whole response as JSON
        try:
            result = json.loads(raw_response)
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

        # Try to find a JSON array inside the response text
        match = re.search(r'\[.*?\]', raw_response, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group())
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                pass

        # Last resort: split by newlines and numbered items
        lines = [line.strip() for line in raw_response.split('\n') if line.strip()]
        tasks = []
        for line in lines:
            cleaned = re.sub(r'^[\d]+[\.\)]\s*', '', line)
            cleaned = re.sub(r'^[-\*]\s*', '', cleaned)
            cleaned = cleaned.strip().strip('"').strip("'")
            if len(cleaned) > 10:
                tasks.append(cleaned)

        if tasks:
            return tasks

        return [raw_response]

    def benchmark(self, test_prompt: str = "Explain what honey is in exactly 3 sentences.",
                  model: str = None) -> dict:
        """
        Run a quick benchmark to measure this backend's performance.

        Returns dict with:
            - backend: str — backend name
            - model: str — model used
            - available: bool — whether the backend responded
            - response_time_seconds: float — time to get response
            - response_length: int — character count of response
            - tokens_per_second: float or None — if the backend reports it
        """
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
        start = time.time()
        response = self.ask(test_prompt, model=model, temperature=0.5)
        elapsed = time.time() - start

        result["response_time_seconds"] = round(elapsed, 2)
        result["response_length"] = len(response)

        return result
```

**Key design decisions:**
- `ask_for_json_list` is in the base class (moved from `ollama_client.py`) — all backends share it
- `benchmark` is in the base class with a default implementation — backends CAN override it to add tokens/sec from their API response
- The interface is minimal: `ask`, `is_available`, `list_models`, `backend_name`

---

## TASK 2: Refactor `ollama_client.py` — Extend AIBackend

Modify `ollama_client.py` to extend `AIBackend`. Keep the class name `OllamaClient` and keep ALL existing method signatures so nothing breaks.

Changes:
1. Add `from ai_backend import AIBackend` import
2. Change `class OllamaClient:` to `class OllamaClient(AIBackend):`
3. Add `backend_name()` method that returns `"Ollama"`
4. REMOVE `ask_for_json_list` method (it's now inherited from AIBackend)
5. Keep everything else identical

The file should look like:

```python
"""
ollama_client.py — Ollama AI Backend
=====================================
Connects to Ollama (the local AI engine) using the official Python library.
Extends the AIBackend base class.
"""

import ollama
from ai_backend import AIBackend


class OllamaClient(AIBackend):
    """Connects to Ollama and sends prompts to the AI model."""

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.client = ollama.Client(host=base_url)

    def ask(self, prompt: str, model: str = "llama3.2:3b", temperature: float = 0.7) -> str:
        try:
            response = self.client.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": temperature}
            )
            return response["message"]["content"].strip()
        except Exception as e:
            return f"[ERROR] Failed to get AI response: {str(e)}"

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
```

**IMPORTANT:** After this change, run `python demo_real.py` to verify nothing is broken. The demo should work exactly as before.

---

## TASK 3: Create `openai_compat_backend.py` — LM Studio / llama.cpp / vLLM

Create a new file `openai_compat_backend.py`. This ONE class handles three backends because they all speak the same OpenAI-compatible API.

```python
"""
openai_compat_backend.py — OpenAI-Compatible AI Backend
========================================================
Handles LM Studio, llama.cpp server, and vLLM.
All three use the same OpenAI-compatible REST API format.
Uses the 'requests' library — does NOT depend on the 'openai' package.
"""

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
        # If no model specified, we'll use whatever the server has loaded.
        # For llama.cpp, model name doesn't matter much — it serves one model.
        # For LM Studio/vLLM, we should specify which model.
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
        """
        Benchmark with tokens/sec extraction from the API response.
        The OpenAI-compatible API often returns usage info we can use.
        """
        import time

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
```

**Key design decisions:**
- One class, parameterized by `backend_type`
- Uses `requests` library only (no `openai` package)
- Default ports are coded in — if you say "lmstudio" with no URL, it tries localhost:1234
- `benchmark()` is overridden to extract tokens/sec from the API response (llama.cpp returns this in `timings`)
- Timeout is 120 seconds — LLMs can be slow, especially on first load

---

## TASK 4: Create `llamacpp_python_backend.py` — Direct Python Binding

Create a new file `llamacpp_python_backend.py`. This is for users who want to run a model directly in Python without a separate server.

```python
"""
llamacpp_python_backend.py — llama.cpp Python Backend
======================================================
Runs a GGUF model directly in Python using the llama-cpp-python library.
No separate server needed — the model runs inside this process.
This is the convenient-but-slower option (compared to llama-server).
"""

from ai_backend import AIBackend


class LlamaCppPythonBackend(AIBackend):
    """
    AI backend using llama-cpp-python to run a GGUF model directly.

    Requires:
        - pip install llama-cpp-python
        - A GGUF model file on disk
    """

    def __init__(self, model_path: str, n_gpu_layers: int = -1, n_ctx: int = 4096):
        """
        Args:
            model_path: Path to the GGUF model file
            n_gpu_layers: Number of layers to offload to GPU (-1 = all)
            n_ctx: Context window size
        """
        self.model_path = model_path
        self.n_gpu_layers = n_gpu_layers
        self.n_ctx = n_ctx
        self._llm = None  # Lazy-loaded

    def _load_model(self):
        """Load the model on first use (lazy loading)."""
        if self._llm is not None:
            return

        try:
            from llama_cpp import Llama
            self._llm = Llama(
                model_path=self.model_path,
                n_gpu_layers=self.n_gpu_layers,
                n_ctx=self.n_ctx,
                verbose=False,
            )
        except ImportError:
            raise ImportError(
                "llama-cpp-python is not installed. "
                "Install it with: pip install llama-cpp-python"
            )

    def ask(self, prompt: str, model: str = None, temperature: float = 0.7) -> str:
        """
        Send a prompt and get a response.
        The 'model' parameter is ignored — we always use the loaded GGUF file.
        """
        try:
            self._load_model()
            response = self._llm.create_chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
            )
            return response["choices"][0]["message"]["content"].strip()
        except ImportError as e:
            return f"[ERROR] {str(e)}"
        except Exception as e:
            return f"[ERROR] llama.cpp Python failed: {str(e)}"

    def is_available(self) -> bool:
        """Check if the model file exists and llama-cpp-python is installed."""
        try:
            import llama_cpp  # noqa: F401
        except ImportError:
            return False

        import os
        return os.path.isfile(self.model_path)

    def list_models(self) -> list:
        """Return the loaded model file name."""
        import os
        if os.path.isfile(self.model_path):
            return [os.path.basename(self.model_path)]
        return []

    def backend_name(self) -> str:
        return "llama.cpp (Python)"
```

**Key design decisions:**
- Lazy loading: model is NOT loaded until `ask()` is first called (loading takes several seconds)
- The `model` parameter in `ask()` is ignored — you always use the GGUF file specified in the constructor
- `n_gpu_layers=-1` means offload all layers to GPU by default
- `is_available()` checks both that the library is installed AND the model file exists

---

## TASK 5: Create `backend_factory.py` — Factory Function

Create a new file `backend_factory.py`:

```python
"""
backend_factory.py — Create the Right AI Backend from Config
=============================================================
Reads the config and returns the appropriate AIBackend instance.
"""

from ai_backend import AIBackend


def create_backend(config: dict) -> AIBackend:
    """
    Create an AIBackend instance based on the config.

    Args:
        config: The full config dict (from config.yaml)

    Returns:
        An AIBackend instance ready to use

    Raises:
        ValueError: If the backend type is unknown
    """
    model_config = config.get("model", {})
    backend = model_config.get("backend", "ollama")
    base_url = model_config.get("base_url")

    if backend == "ollama":
        from ollama_client import OllamaClient
        return OllamaClient(base_url=base_url or "http://localhost:11434")

    elif backend == "lmstudio":
        from openai_compat_backend import OpenAICompatBackend
        return OpenAICompatBackend(
            base_url=base_url,  # None is fine — will use default port 1234
            backend_type="lmstudio",
        )

    elif backend == "llamacpp-server":
        from openai_compat_backend import OpenAICompatBackend
        return OpenAICompatBackend(
            base_url=base_url,  # None is fine — will use default port 8080
            backend_type="llamacpp",
        )

    elif backend == "llamacpp-python":
        from llamacpp_python_backend import LlamaCppPythonBackend
        model_path = model_config.get("model_path", "")
        if not model_path:
            raise ValueError(
                "backend 'llamacpp-python' requires 'model_path' in config.yaml "
                "pointing to a GGUF model file"
            )
        return LlamaCppPythonBackend(model_path=model_path)

    elif backend == "vllm":
        from openai_compat_backend import OpenAICompatBackend
        return OpenAICompatBackend(
            base_url=base_url,  # None is fine — will use default port 8000
            backend_type="vllm",
        )

    else:
        raise ValueError(
            f"Unknown backend: '{backend}'. "
            f"Supported: ollama, lmstudio, llamacpp-server, llamacpp-python, vllm"
        )
```

---

## TASK 6: Create `backend_detector.py` — Auto-Detection

Create a new file `backend_detector.py`:

```python
"""
backend_detector.py — Detect Which AI Backends Are Running
===========================================================
Scans common ports to find which AI backends are currently available.
Used to show the user what's running and suggest defaults.
"""

import requests
from rich.console import Console
from rich.table import Table

console = Console()


def detect_backends() -> list[dict]:
    """
    Scan for all known AI backends and return their status.

    Returns:
        List of dicts, each with:
            - name: str (e.g., "Ollama")
            - backend_key: str (e.g., "ollama") — the value for config.yaml
            - url: str (e.g., "http://localhost:11434")
            - available: bool
            - models: list[str] — available models (empty if not running)
    """
    backends = [
        {
            "name": "Ollama",
            "backend_key": "ollama",
            "url": "http://localhost:11434",
            "health_endpoint": "/api/tags",
            "models_parser": _parse_ollama_models,
        },
        {
            "name": "LM Studio",
            "backend_key": "lmstudio",
            "url": "http://localhost:1234",
            "health_endpoint": "/v1/models",
            "models_parser": _parse_openai_models,
        },
        {
            "name": "llama.cpp server",
            "backend_key": "llamacpp-server",
            "url": "http://localhost:8080",
            "health_endpoint": "/v1/models",
            "models_parser": _parse_openai_models,
        },
        {
            "name": "vLLM",
            "backend_key": "vllm",
            "url": "http://localhost:8000",
            "health_endpoint": "/v1/models",
            "models_parser": _parse_openai_models,
        },
    ]

    # Check llama-cpp-python separately (it's a library, not a server)
    llamacpp_python = {
        "name": "llama.cpp (Python)",
        "backend_key": "llamacpp-python",
        "url": "N/A (in-process)",
        "available": False,
        "models": [],
    }
    try:
        import llama_cpp  # noqa: F401
        llamacpp_python["available"] = True
        llamacpp_python["models"] = ["(requires GGUF model path)"]
    except ImportError:
        pass

    results = []
    for b in backends:
        status = {
            "name": b["name"],
            "backend_key": b["backend_key"],
            "url": b["url"],
            "available": False,
            "models": [],
        }
        try:
            resp = requests.get(b["url"] + b["health_endpoint"], timeout=2)
            if resp.status_code == 200:
                status["available"] = True
                status["models"] = b["models_parser"](resp.json())
        except Exception:
            pass
        results.append(status)

    results.append(llamacpp_python)
    return results


def _parse_ollama_models(data: dict) -> list:
    """Parse model list from Ollama's /api/tags response."""
    models = data.get("models", [])
    return [m.get("name", "unknown") for m in models]


def _parse_openai_models(data: dict) -> list:
    """Parse model list from OpenAI-compatible /v1/models response."""
    if "data" in data:
        return [m.get("id", "unknown") for m in data["data"]]
    if "models" in data:
        return [m.get("id") or m.get("name", "unknown") for m in data["models"]]
    return []


def display_detected_backends(results: list[dict], current_backend: str = None):
    """
    Display a nice table of detected backends.

    Args:
        results: Output from detect_backends()
        current_backend: The currently configured backend key (for highlighting)
    """
    table = Table(title="Detected AI Backends", border_style="cyan")
    table.add_column("Status", width=4)
    table.add_column("Backend", style="bold")
    table.add_column("URL")
    table.add_column("Models")
    table.add_column("Config Key", style="dim")

    for b in results:
        if b["available"]:
            status = "[green]OK[/green]"
            models_str = ", ".join(b["models"][:3])  # Show max 3 models
            if len(b["models"]) > 3:
                models_str += f" (+{len(b['models']) - 3} more)"
        else:
            status = "[red]--[/red]"
            models_str = "[dim]not detected[/dim]"

        # Highlight current backend
        name = b["name"]
        if current_backend and b["backend_key"] == current_backend:
            name = f"[bold yellow]{name} (current)[/bold yellow]"

        table.add_row(status, name, b["url"], models_str, b["backend_key"])

    console.print(table)
```

---

## TASK 7: Update `config.yaml`

Add the new backend options. Change the `model:` section to:

```yaml
# AI Model settings
model:
  # Backend options: ollama, lmstudio, llamacpp-server, llamacpp-python, vllm
  backend: ollama
  # Base URL — auto-detected from backend if not specified:
  #   ollama:          http://localhost:11434
  #   lmstudio:        http://localhost:1234
  #   llamacpp-server: http://localhost:8080
  #   vllm:            http://localhost:8000
  base_url: "http://localhost:11434"
  # Only for llamacpp-python: path to GGUF model file
  model_path: ""
  # Model used by Worker Bees for processing sub-tasks
  worker_model: "llama3.2:3b"
  # Model used by Queen Bee for splitting tasks and combining results
  queen_model: "llama3.2:3b"
  # Temperature: lower = more focused, higher = more creative
  temperature: 0.7
```

---

## TASK 8: Update `worker_bee.py` — Use AIBackend

Changes to `worker_bee.py`:

1. Replace `from ollama_client import OllamaClient` with `from ai_backend import AIBackend`
2. Change constructor to accept an `AIBackend` instance OR keep backward-compatible by accepting `ollama_url` and creating OllamaClient internally
3. Update display messages to show the backend name instead of hardcoded "Ollama"

**New constructor pattern** (backward compatible):

```python
def __init__(self, worker_id: str, model_name: str = "llama3.2:3b",
             ollama_url: str = "http://localhost:11434", temperature: float = 0.7,
             ai_backend: 'AIBackend' = None):
    self.worker_id = worker_id
    self.model_name = model_name
    self.temperature = temperature
    self.tasks_completed = 0

    if ai_backend is not None:
        self.ai = ai_backend
    else:
        # Backward compatibility: create OllamaClient if no backend provided
        from ollama_client import OllamaClient
        self.ai = OllamaClient(base_url=ollama_url)
```

4. In `start()`, change `"Connected to Ollama"` to `f"Connected to {self.ai.backend_name()}"` (same for the error message)

---

## TASK 9: Update `queen_bee.py` — Use AIBackend

Same pattern as worker_bee.py:

1. Replace `from ollama_client import OllamaClient` with `from ai_backend import AIBackend`
2. Change constructor to accept `ai_backend` parameter with backward compatibility:

```python
def __init__(self, model_name: str = "llama3.2:3b",
             ollama_url: str = "http://localhost:11434", temperature: float = 0.5,
             ai_backend: 'AIBackend' = None):
    self.model_name = model_name
    self.temperature = temperature
    self.workers: list[WorkerBee] = []

    if ai_backend is not None:
        self.ai = ai_backend
    else:
        from ollama_client import OllamaClient
        self.ai = OllamaClient(base_url=ollama_url)
```

3. In `start()`, change `"Connected to Ollama"` to `f"Connected to {self.ai.backend_name()}"` (same for the error message)

---

## TASK 10: Update `honeycomb.py` — Use Factory + Auto-Detection

Changes:

1. Replace `from ollama_client import OllamaClient` with:
   ```python
   from backend_factory import create_backend
   from backend_detector import detect_backends, display_detected_backends
   ```

2. After loading config and showing the banner, replace the Ollama connection check with:
   ```python
   # Detect and display available backends
   detected = detect_backends()
   display_detected_backends(detected, current_backend=config["model"].get("backend"))

   # Create the configured AI backend
   try:
       ai = create_backend(config)
   except ValueError as e:
       console.print(f"[bold red]Error: {e}[/]")
       sys.exit(1)

   if not ai.is_available():
       console.print(f"[bold red]Cannot connect to {ai.backend_name()}![/]")
       sys.exit(1)
   console.print(f"[green]Connected to {ai.backend_name()}[/]")
   ```

3. In the worker creation (mode == "worker"), pass the backend:
   ```python
   worker = WorkerBee(
       worker_id=worker_cfg.get("worker_id", "worker-001"),
       model_name=config["model"]["worker_model"],
       temperature=config["model"]["temperature"],
       ai_backend=ai,
   )
   ```

4. In the queen creation (mode == "queen"), pass the backend to queen AND workers:
   ```python
   queen = QueenBee(
       model_name=config["model"]["queen_model"],
       temperature=config["model"]["temperature"],
       ai_backend=ai,
   )
   # Workers also get the same backend
   for i in range(num_workers):
       worker = WorkerBee(
           worker_id=f"worker-{i+1:03d}",
           model_name=config["model"]["worker_model"],
           temperature=config["model"]["temperature"],
           ai_backend=ai,
       )
       queen.add_worker(worker)
   ```

---

## TASK 11: Update `demo_real.py` — Use Factory

Changes:

1. Replace `from ollama_client import OllamaClient` with:
   ```python
   from backend_factory import create_backend
   from backend_detector import detect_backends, display_detected_backends
   ```

2. Replace `check_ollama()` function with a new `check_ai_backend()`:
   ```python
   def check_ai_backend(config):
       """Verify the configured AI backend is available."""
       console.print(Rule("Checking AI Engine"))

       detected = detect_backends()
       display_detected_backends(detected)

       try:
           ai = create_backend(config)
       except ValueError as e:
           console.print(f"[bold red]Error: {e}[/]")
           return None

       if not ai.is_available():
           console.print(f"[bold red]Cannot connect to {ai.backend_name()}![/]")
           return None

       console.print(f"[green]Connected to {ai.backend_name()}[/]")
       models = ai.list_models()
       if models:
           console.print(f"[green]Available models: {', '.join(models[:5])}[/]")
       return ai
   ```

3. In `run_demo()`, load config and use the factory:
   ```python
   import yaml
   # Load config
   try:
       with open("config.yaml", "r") as f:
           config = yaml.safe_load(f)
   except FileNotFoundError:
       config = {"model": {"backend": "ollama", "worker_model": "llama3.2:3b", "queen_model": "llama3.2:3b", "temperature": 0.7}}

   ai = check_ai_backend(config)
   if ai is None:
       sys.exit(1)
   ```

4. Pass `ai_backend=ai` to QueenBee and WorkerBee constructors

---

## TASK 12: Update `demo_website.py` — Use Factory

Same pattern as demo_real.py:

1. Replace `from ollama_client import OllamaClient` with factory/detector imports
2. Use `create_backend(config)` instead of `OllamaClient()`
3. Pass `ai_backend=ai` to QueenBee and WorkerBee constructors
4. Load config from `config.yaml`

---

## TASK 13: Update `requirements.txt`

Add llama-cpp-python as an OPTIONAL dependency (comment explaining it's optional):

```
requests==2.32.3
pyyaml==6.0.2
rich==14.0.0
ollama==0.4.8
# Optional: only needed if using backend: llamacpp-python
# pip install llama-cpp-python
```

Do NOT add it as a hard requirement. Users who don't want it shouldn't need to install it.

---

## Verification Steps (Run After All Tasks)

1. **Test Ollama backend:**
   - Set `config.yaml` backend to `ollama`
   - Run `python demo_real.py` — should work exactly as before

2. **Test LM Studio backend:**
   - Set `config.yaml` backend to `lmstudio`, base_url to `http://localhost:1234`
   - Set worker_model and queen_model to `llama-3.2-3b-instruct`
   - Run `python demo_real.py`

3. **Test llama.cpp server backend:**
   - Set `config.yaml` backend to `llamacpp-server`, base_url to `http://localhost:8080`
   - Set worker_model and queen_model to `Llama-3.2-3B-Instruct-Q4_K_M.gguf`
   - Run `python demo_real.py`

4. **Test auto-detection:**
   - Run `python honeycomb.py` — should show the detection table

---

## File Summary

| File | Action | Description |
|------|--------|-------------|
| `ai_backend.py` | CREATE | Abstract base class |
| `openai_compat_backend.py` | CREATE | LM Studio / llama.cpp / vLLM |
| `llamacpp_python_backend.py` | CREATE | Direct Python llama.cpp |
| `backend_factory.py` | CREATE | Config → backend instance |
| `backend_detector.py` | CREATE | Auto-detect running backends |
| `ollama_client.py` | MODIFY | Extend AIBackend |
| `config.yaml` | MODIFY | Add backend options |
| `worker_bee.py` | MODIFY | Accept AIBackend |
| `queen_bee.py` | MODIFY | Accept AIBackend |
| `honeycomb.py` | MODIFY | Use factory + detection |
| `demo_real.py` | MODIFY | Use factory |
| `demo_website.py` | MODIFY | Use factory |
| `requirements.txt` | MODIFY | Note optional dependency |
