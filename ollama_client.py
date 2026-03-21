"""
ollama_client.py — The AI Connection Layer
==========================================
This module handles all communication with Ollama (the local AI engine).
Every bee in the hive uses this to think.
"""

import ollama
import json
import re
from typing import Optional


class OllamaClient:
    """Connects to Ollama and sends prompts to the AI model."""

    def __init__(self, base_url: str = "http://localhost:11434"):
        """
        Initialize connection to Ollama.

        Args:
            base_url: The URL where Ollama is running (default: localhost:11434)
        """
        self.client = ollama.Client(host=base_url)

    def ask(self, prompt: str, model: str = "llama3.2:3b", temperature: float = 0.7) -> str:
        """
        Send a prompt to the AI model and get a text response.

        Args:
            prompt: The text to send to the AI
            model: Which model to use
            temperature: Creativity level (0.0 = focused, 1.0 = creative)

        Returns:
            The AI's response as a string
        """
        try:
            response = self.client.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": temperature}
            )
            return response["message"]["content"].strip()
        except Exception as e:
            return f"[ERROR] Failed to get AI response: {str(e)}"

    def ask_for_json_list(self, prompt: str, model: str = "llama3.2:3b", temperature: float = 0.3) -> list:
        """
        Send a prompt and expect a JSON list back.
        Uses low temperature for more structured output.
        Tries to extract a JSON array even if the model adds extra text.

        Args:
            prompt: The prompt that should produce a JSON list
            model: Which model to use
            temperature: Creativity level (low for structured output)

        Returns:
            A Python list parsed from the AI's JSON response
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
            # Remove numbering like "1.", "2.", "- ", "* "
            cleaned = re.sub(r'^[\d]+[\.\)]\s*', '', line)
            cleaned = re.sub(r'^[-\*]\s*', '', cleaned)
            cleaned = cleaned.strip().strip('"').strip("'")
            if len(cleaned) > 10:  # Skip very short lines
                tasks.append(cleaned)

        if tasks:
            return tasks

        # Absolute last resort: return the raw response as single item
        return [raw_response]

    def is_available(self) -> bool:
        """Check if Ollama is running and accessible."""
        try:
            self.client.list()
            return True
        except Exception:
            return False

    def list_models(self) -> list:
        """Get list of models installed in Ollama."""
        try:
            models = self.client.list()
            return [m.model for m in models.models] if hasattr(models, 'models') else []
        except Exception:
            return []
