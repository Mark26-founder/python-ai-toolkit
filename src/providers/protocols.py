"""Provider interface contracts defined as structural ``typing.Protocol`` classes.

Each protocol represents a distinct AI capability.  Concrete provider adapters
(e.g. ``openai_provider``, ``anthropic_provider``) implement one or more of
these protocols without subclassing — pure structural (duck-typing) conformance
is sufficient and is verified at runtime via ``isinstance`` when needed.

Protocols
---------
* :class:`ChatProvider`        — text chat/completion generation.
* :class:`EmbeddingProvider`   — vector embedding generation.
* :class:`ImageProvider`       — image generation from text prompts.
* :class:`SpeechProvider`      — text-to-speech synthesis (optional).
* :class:`ModelCapabilityProvider` — model introspection / feature queries.
* :class:`Provider`            — union sentinel; inherits all of the above
                                  as a convenience for full-capability adapters.

Design notes
------------
* All protocols are ``@runtime_checkable`` so callers can use
  ``isinstance(obj, ChatProvider)`` to verify capability at runtime.
* Methods accept and return *only* types defined in :mod:`providers.models`
  and :mod:`providers.responses` — no SDK-specific types leak through.
* Async variants are deliberately excluded; async adapters should wrap these
  interfaces in ``asyncio.to_thread`` or their own async layer.
"""

from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable

# Forward-declared via TYPE_CHECKING to avoid circular imports at runtime;
# the actual classes live in models.py and responses.py.
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .models import ChatRequest, EmbeddingRequest, ImageRequest
    from .responses import ChatResponse, EmbeddingResponse, ImageResponse


# ---------------------------------------------------------------------------
# ChatProvider
# ---------------------------------------------------------------------------

@runtime_checkable
class ChatProvider(Protocol):
    """Interface for providers that support text chat / completion generation.

    Any object that implements :meth:`chat` with the expected signature
    satisfies this protocol without explicit inheritance.

    Example adapter skeleton::

        class MyOpenAIAdapter:
            def chat(self, request: ChatRequest) -> ChatResponse:
                ...  # call OpenAI SDK, map to ChatResponse
    """

    def chat(self, request: ChatRequest) -> ChatResponse:
        """Generates a chat completion for the given request.

        Args:
            request: A fully populated :class:`~providers.models.ChatRequest`.

        Returns:
            A :class:`~providers.responses.ChatResponse` containing the
            generated content and usage metadata.

        Raises:
            providers.exceptions.ProviderError: On any provider-level failure.
        """
        ...  # pragma: no cover


# ---------------------------------------------------------------------------
# EmbeddingProvider
# ---------------------------------------------------------------------------

@runtime_checkable
class EmbeddingProvider(Protocol):
    """Interface for providers that support vector embedding generation.

    Example adapter skeleton::

        class MyEmbeddingAdapter:
            def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
                ...
    """

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Generates vector embeddings for the given request.

        Args:
            request: A fully populated
                :class:`~providers.models.EmbeddingRequest`.

        Returns:
            A :class:`~providers.responses.EmbeddingResponse` containing one
            or more embedding vectors and usage metadata.

        Raises:
            providers.exceptions.ProviderError: On any provider-level failure.
        """
        ...  # pragma: no cover


# ---------------------------------------------------------------------------
# ImageProvider
# ---------------------------------------------------------------------------

@runtime_checkable
class ImageProvider(Protocol):
    """Interface for providers that support image generation from text prompts.

    Example adapter skeleton::

        class MyImageAdapter:
            def generate_image(self, request: ImageRequest) -> ImageResponse:
                ...
    """

    def generate_image(self, request: ImageRequest) -> ImageResponse:
        """Generates one or more images for the given request.

        Args:
            request: A fully populated :class:`~providers.models.ImageRequest`.

        Returns:
            A :class:`~providers.responses.ImageResponse` containing URLs or
            binary data for generated images.

        Raises:
            providers.exceptions.ProviderError: On any provider-level failure.
        """
        ...  # pragma: no cover


# ---------------------------------------------------------------------------
# SpeechProvider (optional capability)
# ---------------------------------------------------------------------------

@runtime_checkable
class SpeechProvider(Protocol):
    """Optional interface for providers that support text-to-speech synthesis.

    Providers that do not support speech synthesis simply omit this method;
    callers should check ``isinstance(provider, SpeechProvider)`` before use.

    Example adapter skeleton::

        class MyTTSAdapter:
            def synthesize(self, text: str, *, voice: str = "default") -> bytes:
                ...
    """

    def synthesize(self, text: str, *, voice: str = "default") -> bytes:
        """Synthesizes speech audio from ``text``.

        Args:
            text: The input text to convert to speech.
            voice: An optional provider-specific voice identifier.

        Returns:
            Raw audio bytes in a provider-defined format (e.g. MP3, WAV,
            or Opus).  Callers should consult the adapter documentation for
            the specific encoding.

        Raises:
            providers.exceptions.ProviderError: On any provider-level failure.
        """
        ...  # pragma: no cover


# ---------------------------------------------------------------------------
# ModelCapabilityProvider
# ---------------------------------------------------------------------------

@runtime_checkable
class ModelCapabilityProvider(Protocol):
    """Interface for providers that expose model introspection capabilities.

    Adapters implementing this protocol allow the toolkit to query which
    models are available and what features they support, enabling dynamic
    model selection strategies.

    Example adapter skeleton::

        class MyCapabilityAdapter:
            def list_models(self) -> list[str]: ...
            def supports_capability(self, model_id: str, capability: str) -> bool: ...
            def context_window(self, model_id: str) -> int: ...
    """

    def list_models(self) -> list[str]:
        """Returns a list of model identifiers available from this provider.

        Returns:
            A list of opaque model ID strings (e.g. ``["gpt-4o", "gpt-4o-mini"]``).

        Raises:
            providers.exceptions.ProviderError: On any provider-level failure.
        """
        ...  # pragma: no cover

    def supports_capability(self, model_id: str, capability: str) -> bool:
        """Returns whether ``model_id`` supports a named capability.

        Capability strings are provider-agnostic conventions, for example:

        * ``"chat"`` — chat completion
        * ``"embeddings"`` — vector embeddings
        * ``"vision"`` — image-in-context support
        * ``"function_calling"`` — structured tool/function calling
        * ``"json_mode"`` — guaranteed JSON output

        Args:
            model_id: A model identifier returned by :meth:`list_models`.
            capability: A capability string to query.

        Returns:
            ``True`` if the model supports the requested capability.

        Raises:
            providers.exceptions.UnsupportedModelError: If ``model_id`` is
                unknown to the provider.
        """
        ...  # pragma: no cover

    def context_window(self, model_id: str) -> int:
        """Returns the token context-window size for ``model_id``.

        Args:
            model_id: A model identifier returned by :meth:`list_models`.

        Returns:
            Maximum context length in tokens.

        Raises:
            providers.exceptions.UnsupportedModelError: If ``model_id`` is
                unknown to the provider.
        """
        ...  # pragma: no cover


# ---------------------------------------------------------------------------
# Provider — composite sentinel for full-capability adapters
# ---------------------------------------------------------------------------

@runtime_checkable
class Provider(
    ChatProvider,
    EmbeddingProvider,
    ImageProvider,
    ModelCapabilityProvider,
    Protocol,
):
    """Full-capability provider protocol.

    An object satisfies :class:`Provider` only when it implements *all* of:

    * :class:`ChatProvider`
    * :class:`EmbeddingProvider`
    * :class:`ImageProvider`
    * :class:`ModelCapabilityProvider`

    :class:`SpeechProvider` is intentionally excluded because speech is an
    optional capability.  Check ``isinstance(p, SpeechProvider)`` separately.

    Most registry entries will satisfy one of the narrower protocols rather
    than this composite one; prefer the specific protocol as the type hint
    wherever possible.
    """
    ...  # pragma: no cover
