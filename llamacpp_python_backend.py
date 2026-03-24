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
