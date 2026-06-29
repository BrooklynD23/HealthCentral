"""
core.llm — Model-agnostic LLM provider layer.

Public surface:
    ProviderProtocol   – structural interface every provider must satisfy
    InferenceResult    – shared result datatype (re-exported from model_runner for compat)
    InferenceConfig    – shared config datatype (re-exported from model_runner for compat)
    CapabilityFlags    – provider capability descriptor
    LlamaCppProvider   – wraps llama-cpp-python (default, local)
    OllamaProvider     – talks to a local Ollama daemon (optional)
    get_provider       – factory: returns the provider configured in settings
"""

from .provider import (
    CapabilityFlags,
    ProviderProtocol,
    ProviderUnavailableError,
)
from .llama_cpp_provider import LlamaCppProvider
from .ollama_provider import OllamaProvider
from .factory import get_provider, reset_provider

__all__ = [
    "CapabilityFlags",
    "ProviderProtocol",
    "ProviderUnavailableError",
    "LlamaCppProvider",
    "OllamaProvider",
    "get_provider",
    "reset_provider",
]
