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


def detect_backends() -> list:
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


def display_detected_backends(results: list, current_backend: str = None):
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
