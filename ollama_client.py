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
