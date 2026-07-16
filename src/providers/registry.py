"""Thread-safe provider registry.

The registry maps string names to provider objects that conform to one or more
of the :mod:`providers.protocols` interfaces.  It deliberately operates against
structural (duck-typed) interfaces rather than concrete classes, preserving
complete provider-agnosticism.

Classes
-------
* :class:`ProviderRegistry` — the core registry implementation.

Module-level helpers
--------------------
A default global registry instance is exposed as :data:`registry` so callers
can start registering providers without instantiating their own object.

Example::

    from providers.registry import registry
    from providers.protocols import ChatProvider

    registry.register("openai", openai_adapter)
    registry.register("anthropic", anthropic_adapter)

    provider = registry.get("openai", ChatProvider)
    response = provider.chat(request)
"""

from __future__ import annotations

import threading
from typing import Any, Type, TypeVar

from .exceptions import (
    ProviderNotFoundError,
    ProviderRegistrationError,
)

T = TypeVar("T")


class ProviderRegistry:
    """A thread-safe registry mapping names to provider objects.

    Providers are stored as plain Python objects; the registry does not impose
    any inheritance requirement.  Callers may optionally validate a capability
    interface at retrieval time using the ``as_type`` parameter of
    :meth:`get`.

    Attributes are intentionally private; the public API consists solely of
    :meth:`register`, :meth:`get`, :meth:`remove`, :meth:`list_providers`,
    :meth:`has`, and :meth:`clear`.

    Thread safety
    -------------
    All mutations and reads are protected by a single :class:`threading.RLock`
    so the registry can be safely shared across threads (e.g. a web server's
    request handlers sharing a module-level registry).

    Example::

        registry = ProviderRegistry()
        registry.register("openai", my_openai_adapter)

        provider = registry.get("openai")
        chat_provider = registry.get("openai", ChatProvider)
    """

    def __init__(self, *, allow_override: bool = False) -> None:
        """Initializes ProviderRegistry.

        Args:
            allow_override: When ``True``, calling :meth:`register` with an
                already-registered name silently replaces the existing entry.
                When ``False`` (default), such calls raise
                :class:`~providers.exceptions.ProviderRegistrationError`.
        """
        self._providers: dict[str, Any] = {}
        self._lock = threading.RLock()
        self._allow_override = allow_override

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, name: str, provider: Any) -> None:
        """Registers a provider under ``name``.

        Args:
            name: A non-empty string identifier.  By convention, use the
                provider's canonical name in lowercase (e.g. ``"openai"``).
            provider: Any object.  The registry does not enforce a specific
                type at registration time.

        Raises:
            ProviderRegistrationError: If ``name`` is empty, ``provider`` is
                ``None``, or ``name`` is already registered and
                ``allow_override=False``.

        Example::

            registry.register("gemini", gemini_adapter)
        """
        if not name:
            raise ProviderRegistrationError(
                "Provider name must be a non-empty string.",
                provider_name=name,
            )
        if provider is None:
            raise ProviderRegistrationError(
                "provider must not be None.",
                provider_name=name,
            )
        with self._lock:
            if name in self._providers and not self._allow_override:
                raise ProviderRegistrationError(
                    f"A provider is already registered under {name!r}. "
                    "Pass allow_override=True to the registry to permit "
                    "replacement.",
                    provider_name=name,
                )
            self._providers[name] = provider

    def register_many(self, providers: dict[str, Any]) -> None:
        """Registers multiple providers from a mapping in one call.

        Args:
            providers: Dict mapping name strings to provider objects.

        Raises:
            ProviderRegistrationError: On the first entry that fails
                :meth:`register` validation.

        Example::

            registry.register_many({
                "openai": openai_adapter,
                "anthropic": anthropic_adapter,
            })
        """
        for name, provider in providers.items():
            self.register(name, provider)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get(self, name: str, as_type: Type[T] | None = None) -> Any:
        """Retrieves the provider registered under ``name``.

        Args:
            name: The registered provider name.
            as_type: An optional type (typically a :class:`typing.Protocol`)
                to validate the provider against.  When supplied, an
                ``isinstance`` check is performed and
                :class:`~providers.exceptions.ProviderRegistrationError` is
                raised if the check fails.

        Returns:
            The registered provider object.  When ``as_type`` is given the
            return type is narrowed to ``as_type``.

        Raises:
            ProviderNotFoundError: If ``name`` is not registered.
            ProviderRegistrationError: If ``as_type`` is given and the
                provider does not satisfy the interface.

        Example::

            provider = registry.get("openai")
            chat  = registry.get("openai", ChatProvider)
        """
        with self._lock:
            if name not in self._providers:
                available = ", ".join(sorted(self._providers)) or "<none>"
                raise ProviderNotFoundError(
                    f"No provider registered under {name!r}. "
                    f"Available providers: {available}.",
                    provider_name=name,
                )
            provider = self._providers[name]

        if as_type is not None and not isinstance(provider, as_type):
            raise ProviderRegistrationError(
                f"Provider {name!r} does not implement {as_type.__name__}.",
                provider_name=name,
            )
        return provider

    def get_or_none(self, name: str) -> Any | None:
        """Returns the provider for ``name``, or ``None`` if not registered.

        Args:
            name: The registered provider name.

        Returns:
            The registered provider object or ``None``.
        """
        with self._lock:
            return self._providers.get(name)

    # ------------------------------------------------------------------
    # Removal
    # ------------------------------------------------------------------

    def remove(self, name: str) -> None:
        """Removes the provider registered under ``name``.

        Args:
            name: The registered provider name to remove.

        Raises:
            ProviderNotFoundError: If ``name`` is not registered.
        """
        with self._lock:
            if name not in self._providers:
                raise ProviderNotFoundError(
                    f"Cannot remove {name!r}: no such provider is registered.",
                    provider_name=name,
                )
            del self._providers[name]

    def remove_if_present(self, name: str) -> bool:
        """Removes ``name`` if registered; does nothing otherwise.

        Args:
            name: The registered provider name.

        Returns:
            ``True`` if the provider was removed, ``False`` if it was absent.
        """
        with self._lock:
            if name in self._providers:
                del self._providers[name]
                return True
            return False

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def has(self, name: str) -> bool:
        """Returns ``True`` if ``name`` is registered.

        Args:
            name: The provider name to check.

        Returns:
            Boolean indicating presence.
        """
        with self._lock:
            return name in self._providers

    def list_providers(self) -> list[str]:
        """Returns a sorted list of all registered provider names.

        Returns:
            Alphabetically sorted list of name strings.
        """
        with self._lock:
            return sorted(self._providers)

    def providers_by_capability(self, capability_type: type) -> list[str]:
        """Returns names of all providers that satisfy ``capability_type``.

        Uses ``isinstance`` (structural checking via ``@runtime_checkable``
        protocols) to identify conforming providers.

        Args:
            capability_type: A ``@runtime_checkable`` Protocol or class to
                test against.

        Returns:
            Sorted list of provider names whose objects satisfy the check.

        Example::

            chat_providers = registry.providers_by_capability(ChatProvider)
        """
        with self._lock:
            return sorted(
                name
                for name, provider in self._providers.items()
                if isinstance(provider, capability_type)
            )

    def clear(self) -> None:
        """Removes **all** registered providers.

        Intended for use in tests or application teardown.
        """
        with self._lock:
            self._providers.clear()

    def __len__(self) -> int:  # noqa: D105
        with self._lock:
            return len(self._providers)

    def __contains__(self, name: object) -> bool:  # noqa: D105
        with self._lock:
            return name in self._providers

    def __repr__(self) -> str:  # noqa: D105
        with self._lock:
            names = sorted(self._providers)
        return f"ProviderRegistry(providers={names!r})"


# ---------------------------------------------------------------------------
# Module-level default registry
# ---------------------------------------------------------------------------

#: A shared :class:`ProviderRegistry` instance for applications that do not
#: need to manage their own registry.  Import and use directly::
#:
#:     from providers.registry import registry
#:     registry.register("openai", openai_adapter)
registry: ProviderRegistry = ProviderRegistry()
