"""Provider-agnostic request models.

All request types are implemented as frozen :func:`dataclasses.dataclass`
instances so they are immutable, hashable, and safe to share across threads.

Classes
-------
* :class:`Role`               — enumeration of chat participant roles.
* :class:`ChatMessage`        — a single turn in a conversation.
* :class:`GenerationOptions`  — common generation hyper-parameters.
* :class:`ChatRequest`        — full chat-completion request payload.
* :class:`EmbeddingRequest`   — embedding generation request.
* :class:`ImageRequest`       — image generation request.

Design notes
------------
* Fields with ``None`` defaults represent optional provider capabilities;
  adapters MUST ignore ``None`` values rather than forwarding them.
* ``GenerationOptions`` is composed into ``ChatRequest`` so that hyper-
  parameters can be reused across different call sites.
* No vendor-specific fields.  Provider adapters are responsible for mapping
  these generic types to their SDK's request objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Role
# ---------------------------------------------------------------------------

class Role(str, Enum):
    """Roles that a message participant can occupy in a conversation.

    Inherits from ``str`` so role values compare equal to plain strings,
    which simplifies serialisation and provider-side mapping.
    """

    SYSTEM = "system"
    """Instructions / persona injected before the conversation begins."""

    USER = "user"
    """A turn produced by the human participant."""

    ASSISTANT = "assistant"
    """A turn produced by the AI model."""

    TOOL = "tool"
    """A turn carrying the result of a tool / function call."""


# ---------------------------------------------------------------------------
# ChatMessage
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ChatMessage:
    """A single turn in a multi-turn conversation.

    Attributes:
        role: The participant role for this message.
        content: The textual content of the message.
        name: An optional participant name used to distinguish multiple users
            or tool identities within the same conversation.
        tool_call_id: The ID of the tool call this message responds to.
            Only meaningful when ``role`` is :attr:`Role.TOOL`.
        metadata: An arbitrary mapping for provider-specific extensions.
            Adapters should document which keys they consume.

    Example::

        msg = ChatMessage(role=Role.USER, content="Hello, how are you?")
    """

    role: Role
    content: str
    name: str | None = None
    tool_call_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.content and self.role is not Role.TOOL:
            raise ValueError(
                f"ChatMessage.content must not be empty for role {self.role!r}."
            )


# ---------------------------------------------------------------------------
# GenerationOptions
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GenerationOptions:
    """Common hyper-parameters controlling model generation behaviour.

    All fields are optional (``None`` means "use provider default").
    Adapters MUST silently ignore any option that the target provider does
    not support.

    Attributes:
        temperature: Sampling temperature in the range ``[0.0, 2.0]``.
            Lower values produce more deterministic output.
        top_p: Nucleus sampling probability mass.  Mutually exclusive with
            ``temperature`` on most providers.
        top_k: Limits the vocabulary to the top-*k* tokens at each step.
        max_tokens: Maximum number of tokens to generate.
        stop_sequences: List of strings that halt generation when encountered.
        frequency_penalty: Penalises repeated tokens by frequency.
        presence_penalty: Penalises tokens that have appeared at all.
        seed: Optional integer seed for deterministic sampling (where
            supported).
        extra: Provider-specific overrides that do not fit a generic field.
            Keys and values are forwarded to the adapter verbatim.
    """

    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    max_tokens: int | None = None
    stop_sequences: tuple[str, ...] = field(default_factory=tuple)
    frequency_penalty: float | None = None
    presence_penalty: float | None = None
    seed: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.temperature is not None and not (0.0 <= self.temperature <= 2.0):
            raise ValueError(
                f"temperature must be in [0.0, 2.0], got {self.temperature!r}."
            )
        if self.top_p is not None and not (0.0 <= self.top_p <= 1.0):
            raise ValueError(
                f"top_p must be in [0.0, 1.0], got {self.top_p!r}."
            )
        if self.top_k is not None and self.top_k < 1:
            raise ValueError(
                f"top_k must be >= 1, got {self.top_k!r}."
            )
        if self.max_tokens is not None and self.max_tokens < 1:
            raise ValueError(
                f"max_tokens must be >= 1, got {self.max_tokens!r}."
            )


# ---------------------------------------------------------------------------
# ChatRequest
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ChatRequest:
    """A complete chat-completion request payload.

    Attributes:
        model: Provider-specific model identifier (e.g. ``"gpt-4o"``).
        messages: Ordered conversation history.  Must contain at least one
            message.
        options: Generation hyper-parameters.  Defaults to provider defaults
            when ``None``.
        stream: Whether to request a streaming response.  Adapters that do
            not support streaming should ignore this field or raise.
        user_id: An optional opaque identifier for the end user.  Forwarded
            to providers that support it for abuse detection.
        metadata: Arbitrary caller-supplied metadata forwarded to the adapter.

    Example::

        request = ChatRequest(
            model="claude-3-5-sonnet",
            messages=[
                ChatMessage(role=Role.SYSTEM, content="You are helpful."),
                ChatMessage(role=Role.USER, content="Explain rate limiting."),
            ],
            options=GenerationOptions(temperature=0.2, max_tokens=512),
        )
    """

    model: str
    messages: tuple[ChatMessage, ...]
    options: GenerationOptions = field(default_factory=GenerationOptions)
    stream: bool = False
    user_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.model:
            raise ValueError("ChatRequest.model must not be empty.")
        if not self.messages:
            raise ValueError("ChatRequest.messages must contain at least one message.")


# ---------------------------------------------------------------------------
# EmbeddingRequest
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EmbeddingRequest:
    """A request to generate vector embeddings for one or more text inputs.

    Attributes:
        model: Provider-specific embedding model identifier.
        inputs: One or more texts to embed.  Must not be empty.
        dimensions: Optional override for the output vector dimensionality.
            Only supported by some providers.
        encoding_format: Requested encoding format, e.g. ``"float"`` or
            ``"base64"``.  Adapters that do not support this option ignore it.
        user_id: Optional opaque end-user identifier.
        metadata: Arbitrary caller-supplied metadata.

    Example::

        request = EmbeddingRequest(
            model="text-embedding-3-small",
            inputs=["Hello world", "Rate limiting explained"],
        )
    """

    model: str
    inputs: tuple[str, ...]
    dimensions: int | None = None
    encoding_format: str = "float"
    user_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.model:
            raise ValueError("EmbeddingRequest.model must not be empty.")
        if not self.inputs:
            raise ValueError("EmbeddingRequest.inputs must contain at least one string.")
        if self.dimensions is not None and self.dimensions < 1:
            raise ValueError(
                f"EmbeddingRequest.dimensions must be >= 1, got {self.dimensions!r}."
            )


# ---------------------------------------------------------------------------
# ImageRequest
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ImageRequest:
    """A request to generate one or more images from a text prompt.

    Attributes:
        model: Provider-specific image model identifier.
        prompt: The text description of the image to generate.
        n: Number of images to generate.  Defaults to 1.
        size: Desired output resolution as ``"WIDTHxHEIGHT"`` (e.g.
            ``"1024x1024"``).  Adapters default to the provider standard.
        quality: Provider-specific quality preset, e.g. ``"standard"`` or
            ``"hd"``.
        style: Provider-specific style hint, e.g. ``"natural"`` or ``"vivid"``.
        response_format: How images should be returned: ``"url"`` (default)
            or ``"b64_json"``.
        user_id: Optional opaque end-user identifier.
        metadata: Arbitrary caller-supplied metadata.

    Example::

        request = ImageRequest(
            model="dall-e-3",
            prompt="A serene mountain lake at sunrise, photorealistic.",
            size="1024x1024",
        )
    """

    model: str
    prompt: str
    n: int = 1
    size: str | None = None
    quality: str | None = None
    style: str | None = None
    response_format: str = "url"
    user_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.model:
            raise ValueError("ImageRequest.model must not be empty.")
        if not self.prompt:
            raise ValueError("ImageRequest.prompt must not be empty.")
        if self.n < 1:
            raise ValueError(f"ImageRequest.n must be >= 1, got {self.n!r}.")
        if self.response_format not in {"url", "b64_json"}:
            raise ValueError(
                f"ImageRequest.response_format must be 'url' or 'b64_json', "
                f"got {self.response_format!r}."
            )
