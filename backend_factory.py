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
