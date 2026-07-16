"""providers — Provider-agnostic abstraction layer for LLM adapters.

This package defines the contracts, request/response models, and registry that
allow the rest of the toolkit to call any AI provider without importing vendor
SDKs.

Public API
----------
Exceptions::

    ProviderError
    ProviderNotFoundError
    ProviderRegistrationError
    ProviderConfigurationError
    UnsupportedModelError

Protocols (interfaces)::

    ChatProvider
    EmbeddingProvider
    ImageProvider
    SpeechProvider
    ModelCapabilityProvider
    Provider                    ← composite of all mandatory protocols

Request models::

    Role
    ChatMessage
    GenerationOptions
    ChatRequest
    EmbeddingRequest
    ImageRequest

Response models::

    FinishReason
    Usage
    ChatResponse
    EmbeddingResponse
    ImageData
    ImageResponse

Registry::

    ProviderRegistry
    registry                    ← module-level default instance
"""

from __future__ import annotations

# --- Exceptions ---
from .exceptions import (
    ProviderConfigurationError,
    ProviderError,
    ProviderNotFoundError,
    ProviderRegistrationError,
    UnsupportedModelError,
)

# --- Protocols ---
from .protocols import (
    ChatProvider,
    EmbeddingProvider,
    ImageProvider,
    ModelCapabilityProvider,
    Provider,
    SpeechProvider,
)

# --- Request models ---
from .models import (
    ChatMessage,
    ChatRequest,
    EmbeddingRequest,
    GenerationOptions,
    ImageRequest,
    Role,
)

# --- Response models ---
from .responses import (
    ChatResponse,
    EmbeddingResponse,
    FinishReason,
    ImageData,
    ImageResponse,
    Usage,
)

# --- Registry ---
from .registry import ProviderRegistry, registry

__all__ = [
    # Exceptions
    "ProviderError",
    "ProviderNotFoundError",
    "ProviderRegistrationError",
    "ProviderConfigurationError",
    "UnsupportedModelError",
    # Protocols
    "ChatProvider",
    "EmbeddingProvider",
    "ImageProvider",
    "SpeechProvider",
    "ModelCapabilityProvider",
    "Provider",
    # Request models
    "Role",
    "ChatMessage",
    "GenerationOptions",
    "ChatRequest",
    "EmbeddingRequest",
    "ImageRequest",
    # Response models
    "FinishReason",
    "Usage",
    "ChatResponse",
    "EmbeddingResponse",
    "ImageData",
    "ImageResponse",
    # Registry
    "ProviderRegistry",
    "registry",
]
