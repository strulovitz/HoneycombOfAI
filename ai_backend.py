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
