"""Rate-limiting strategies for multi-dimensional request control.

Each strategy maps an *identity key* (user ID, API key, endpoint, …) to a
shared limiter instance, creating isolated per-identity budgets from a single
reusable strategy object.

Strategies
----------
* :class:`PerUserStrategy`     — one limiter bucket per user identifier.
* :class:`PerApiKeyStrategy`   — one limiter bucket per API key string.
* :class:`PerEndpointStrategy` — one limiter bucket per endpoint / route name.
* :class:`GlobalStrategy`      — a single shared limiter for all callers.
* :class:`CompositeStrategy`   — applies multiple strategies in sequence;
                                  *all* must allow the request.

All strategies share the same four-method contract identical to the underlying
limiter classes, enabling transparent substitution.

Thread safety
-------------
Identity-to-limiter mappings are protected by a single :class:`threading.RLock`
per strategy.  Individual limiter operations are protected by their own internal
locks (see ``limiters.py``).

Example::

    from rate_limit.limiters import FixedWindowLimiter
    from rate_limit.strategies import PerUserStrategy, GlobalStrategy, CompositeStrategy

    # 10 req / 60 s per user, plus a global 100 req / 60 s ceiling
    per_user = PerUserStrategy(lambda: FixedWindowLimiter(10, 60))
    global_  = GlobalStrategy(FixedWindowLimiter(100, 60))
    strategy = CompositeStrategy([per_user, global_])

    strategy.acquire("alice")
"""

from __future__ import annotations

import threading
from typing import Callable, Protocol, Sequence, runtime_checkable

from .exceptions import LimiterConfigurationError, RateLimitExceededError


# ---------------------------------------------------------------------------
# Limiter protocol (structural)
# ---------------------------------------------------------------------------

@runtime_checkable
class Limiter(Protocol):
    """Structural protocol that all limiter classes satisfy."""

    def allow(self) -> bool: ...          # pragma: no cover
    def acquire(self) -> None: ...        # pragma: no cover
    def remaining(self) -> int: ...       # pragma: no cover
    def reset(self) -> None: ...          # pragma: no cover


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class _KeyedStrategy:
    """Internal base for per-identity strategies backed by a limiter factory.

    Subclasses only need to call :meth:`_acquire_for` / :meth:`_allow_for` /
    :meth:`_remaining_for` with the appropriate key derived from their own
    ``acquire()`` signature.
    """

    def __init__(self, factory: Callable[[], Limiter]) -> None:
        """Initializes _KeyedStrategy.

        Args:
            factory: Zero-argument callable that returns a fresh ``Limiter``
                instance for each new identity key encountered.

        Raises:
            LimiterConfigurationError: If ``factory`` is not callable.
        """
        if not callable(factory):
            raise LimiterConfigurationError("factory must be a callable that returns a Limiter.")
        self._factory = factory
        self._limiters: dict[str, Limiter] = {}
        self._lock = threading.RLock()

    def _get_or_create(self, key: str) -> Limiter:
        with self._lock:
            if key not in self._limiters:
                self._limiters[key] = self._factory()
            return self._limiters[key]

    def _allow_for(self, key: str) -> bool:
        return self._get_or_create(key).allow()

    def _acquire_for(self, key: str) -> None:
        self._get_or_create(key).acquire()

    def _remaining_for(self, key: str) -> int:
        return self._get_or_create(key).remaining()

    def _reset_for(self, key: str) -> None:
        self._get_or_create(key).reset()

    def reset_all(self) -> None:
        """Resets limiters for **all** known identity keys.

        Useful for test teardown or end-of-period administrative resets.
        """
        with self._lock:
            for limiter in self._limiters.values():
                limiter.reset()

    def known_keys(self) -> list[str]:
        """Returns a snapshot of all identity keys that have a limiter.

        Returns:
            A list of key strings; order is insertion order.
        """
        with self._lock:
            return list(self._limiters)


# ---------------------------------------------------------------------------
# Per-User Strategy
# ---------------------------------------------------------------------------

class PerUserStrategy(_KeyedStrategy):
    """Applies independent rate limits to each user identifier.

    Each unique ``user_id`` gets its own limiter created on first use via
    the supplied ``factory``.  This allows heterogeneous limits (e.g. premium
    vs. free-tier) by using different factories for different instances.

    Example::

        strategy = PerUserStrategy(lambda: FixedWindowLimiter(10, 60))
        strategy.acquire("user-42")
    """

    def __init__(self, factory: Callable[[], Limiter]) -> None:
        """Initializes PerUserStrategy.

        Args:
            factory: Returns a new ``Limiter`` for each unseen ``user_id``.

        Raises:
            LimiterConfigurationError: If ``factory`` is not callable.
        """
        super().__init__(factory)

    def allow(self, user_id: str) -> bool:
        """Returns ``True`` if ``user_id`` has remaining capacity.

        Args:
            user_id: Unique identifier for the user.

        Returns:
            ``True`` when the user's limiter has at least one slot available.
        """
        return self._allow_for(user_id)

    def acquire(self, user_id: str) -> None:
        """Consumes one slot for ``user_id``.

        Args:
            user_id: Unique identifier for the user.

        Raises:
            RateLimitExceededError: When the user's limit is exhausted.
        """
        self._acquire_for(user_id)

    def remaining(self, user_id: str) -> int:
        """Returns remaining slots for ``user_id``.

        Args:
            user_id: Unique identifier for the user.

        Returns:
            Non-negative integer count of available slots.
        """
        return self._remaining_for(user_id)

    def reset(self, user_id: str) -> None:
        """Resets the limiter for a specific ``user_id``.

        Args:
            user_id: Unique identifier for the user.
        """
        self._reset_for(user_id)

    def __repr__(self) -> str:  # noqa: D105
        return f"PerUserStrategy(known_users={len(self._limiters)})"


# ---------------------------------------------------------------------------
# Per-API-Key Strategy
# ---------------------------------------------------------------------------

class PerApiKeyStrategy(_KeyedStrategy):
    """Applies independent rate limits to each API key string.

    Structurally identical to :class:`PerUserStrategy` but semantically
    oriented toward API-key-based throttling, making intent explicit at the
    call site.

    Example::

        strategy = PerApiKeyStrategy(lambda: TokenBucketLimiter(20, 5.0))
        strategy.acquire("sk-abc123")
    """

    def __init__(self, factory: Callable[[], Limiter]) -> None:
        """Initializes PerApiKeyStrategy.

        Args:
            factory: Returns a new ``Limiter`` for each unseen ``api_key``.

        Raises:
            LimiterConfigurationError: If ``factory`` is not callable.
        """
        super().__init__(factory)

    def allow(self, api_key: str) -> bool:
        """Returns ``True`` if ``api_key`` has remaining capacity.

        Args:
            api_key: The API key string to check.

        Returns:
            ``True`` when the key's limiter has capacity.
        """
        return self._allow_for(api_key)

    def acquire(self, api_key: str) -> None:
        """Consumes one slot for ``api_key``.

        Args:
            api_key: The API key string to consume a slot for.

        Raises:
            RateLimitExceededError: When the key's limit is exhausted.
        """
        self._acquire_for(api_key)

    def remaining(self, api_key: str) -> int:
        """Returns remaining slots for ``api_key``.

        Args:
            api_key: The API key string to query.

        Returns:
            Non-negative integer count of available slots.
        """
        return self._remaining_for(api_key)

    def reset(self, api_key: str) -> None:
        """Resets the limiter for a specific ``api_key``.

        Args:
            api_key: The API key string to reset.
        """
        self._reset_for(api_key)

    def __repr__(self) -> str:  # noqa: D105
        return f"PerApiKeyStrategy(known_keys={len(self._limiters)})"


# ---------------------------------------------------------------------------
# Per-Endpoint Strategy
# ---------------------------------------------------------------------------

class PerEndpointStrategy(_KeyedStrategy):
    """Applies independent rate limits to each named endpoint or route.

    The ``endpoint`` string is arbitrary — use URL paths, route names, or any
    other identifier that distinguishes one call site from another.

    Example::

        strategy = PerEndpointStrategy(lambda: SlidingWindowLimiter(50, 10))
        strategy.acquire("/api/v1/completions")
        strategy.acquire("/api/v1/embeddings")
    """

    def __init__(self, factory: Callable[[], Limiter]) -> None:
        """Initializes PerEndpointStrategy.

        Args:
            factory: Returns a new ``Limiter`` for each unseen ``endpoint``.

        Raises:
            LimiterConfigurationError: If ``factory`` is not callable.
        """
        super().__init__(factory)

    def allow(self, endpoint: str) -> bool:
        """Returns ``True`` if ``endpoint`` has remaining capacity.

        Args:
            endpoint: Endpoint identifier string (e.g. a URL path).

        Returns:
            ``True`` when the endpoint's limiter has capacity.
        """
        return self._allow_for(endpoint)

    def acquire(self, endpoint: str) -> None:
        """Consumes one slot for ``endpoint``.

        Args:
            endpoint: Endpoint identifier string.

        Raises:
            RateLimitExceededError: When the endpoint's limit is exhausted.
        """
        self._acquire_for(endpoint)

    def remaining(self, endpoint: str) -> int:
        """Returns remaining slots for ``endpoint``.

        Args:
            endpoint: Endpoint identifier string.

        Returns:
            Non-negative integer count of available slots.
        """
        return self._remaining_for(endpoint)

    def reset(self, endpoint: str) -> None:
        """Resets the limiter for a specific ``endpoint``.

        Args:
            endpoint: Endpoint identifier string.
        """
        self._reset_for(endpoint)

    def __repr__(self) -> str:  # noqa: D105
        return f"PerEndpointStrategy(known_endpoints={len(self._limiters)})"


# ---------------------------------------------------------------------------
# Global Strategy
# ---------------------------------------------------------------------------

class GlobalStrategy:
    """Wraps a single shared limiter applied uniformly to all callers.

    Unlike the keyed strategies, ``GlobalStrategy`` exposes the same four-method
    interface but without an identity parameter — every call competes for the
    same shared budget.

    Use as a top-level ceiling in a :class:`CompositeStrategy`, or alone when
    all callers share a single resource budget.

    Example::

        strategy = GlobalStrategy(FixedWindowLimiter(1000, 60))
        strategy.acquire()
    """

    def __init__(self, limiter: Limiter) -> None:
        """Initializes GlobalStrategy.

        Args:
            limiter: A ``Limiter`` instance to share across all callers.

        Raises:
            LimiterConfigurationError: If ``limiter`` does not satisfy the
                ``Limiter`` protocol.
        """
        if not isinstance(limiter, Limiter):
            raise LimiterConfigurationError(
                "limiter must implement the Limiter protocol "
                "(allow, acquire, remaining, reset)."
            )
        self._limiter = limiter

    def allow(self) -> bool:
        """Returns ``True`` if the global limiter has remaining capacity.

        Returns:
            ``True`` when at least one slot is available.
        """
        return self._limiter.allow()

    def acquire(self) -> None:
        """Consumes one slot from the global limiter.

        Raises:
            RateLimitExceededError: When the global limit is exhausted.
        """
        self._limiter.acquire()

    def remaining(self) -> int:
        """Returns the number of remaining global slots.

        Returns:
            Non-negative integer count of available slots.
        """
        return self._limiter.remaining()

    def reset(self) -> None:
        """Resets the global limiter."""
        self._limiter.reset()

    def __repr__(self) -> str:  # noqa: D105
        return f"GlobalStrategy(limiter={self._limiter!r})"


# ---------------------------------------------------------------------------
# Composite Strategy
# ---------------------------------------------------------------------------

class CompositeStrategy:
    """Composes multiple strategies so that *all* must pass for a request.

    Strategies are checked in list order.  The first strategy to raise
    :class:`~rate_limit.exceptions.RateLimitExceededError` stops evaluation
    immediately — subsequent strategies are not consulted and no further slots
    are consumed.  This ensures atomicity: a request either clears every gate
    or none.

    Typical composition pattern::

        per_user   = PerUserStrategy(lambda: FixedWindowLimiter(10, 60))
        per_key    = PerApiKeyStrategy(lambda: FixedWindowLimiter(100, 60))
        global_cap = GlobalStrategy(FixedWindowLimiter(500, 60))

        composite = CompositeStrategy([per_user, per_key, global_cap])
        composite.acquire("user-7", "sk-xyz", "/completions")

    The ``*keys`` positional arguments to :meth:`acquire`, :meth:`allow`, and
    :meth:`remaining` are forwarded positionally to the underlying strategies.
    Pass ``None`` or omit a key to skip calling that strategy with a key
    (for :class:`GlobalStrategy` members, which take no key argument).

    Note:
        ``CompositeStrategy`` does **not** enforce which strategies you combine
        or which keys you supply — you own the mapping between argument
        positions and strategy members.
    """

    def __init__(self, strategies: Sequence[object]) -> None:
        """Initializes CompositeStrategy.

        Args:
            strategies: Ordered sequence of strategy or limiter objects.  Each
                must expose at minimum an ``acquire()`` method.  The list must
                not be empty.

        Raises:
            LimiterConfigurationError: If ``strategies`` is empty or any member
                lacks an ``acquire`` callable.
        """
        if not strategies:
            raise LimiterConfigurationError("strategies must not be empty.")
        for i, s in enumerate(strategies):
            if not callable(getattr(s, "acquire", None)):
                raise LimiterConfigurationError(
                    f"strategies[{i}] ({s!r}) does not have a callable acquire()."
                )
        self._strategies: list[object] = list(strategies)

    def acquire(self, *keys: str | None) -> None:
        """Attempts to consume one slot across all composed strategies.

        Each strategy's ``acquire()`` is called with the corresponding element
        of ``*keys`` (if the strategy's ``acquire`` accepts arguments) or with
        no arguments (for :class:`GlobalStrategy`-style objects).

        Args:
            *keys: One key per positional strategy that requires one.

        Raises:
            RateLimitExceededError: On the first strategy that rejects the
                request.
        """
        padded = list(keys) + [None] * (len(self._strategies) - len(keys))
        for strategy, key in zip(self._strategies, padded):
            acq = getattr(strategy, "acquire")
            if key is not None:
                acq(key)
            else:
                acq()

    def allow(self, *keys: str | None) -> bool:
        """Returns ``True`` only if every strategy permits the request.

        Non-consuming; does not decrement any counter.

        Args:
            *keys: One key per positional strategy that requires one.

        Returns:
            ``True`` when all strategies report capacity.
        """
        padded = list(keys) + [None] * (len(self._strategies) - len(keys))
        for strategy, key in zip(self._strategies, padded):
            fn = getattr(strategy, "allow")
            if key is not None:
                result: bool = fn(key)
            else:
                result = fn()
            if not result:
                return False
        return True

    def remaining(self, *keys: str | None) -> list[int]:
        """Returns a list of remaining counts, one per strategy.

        Args:
            *keys: One key per positional strategy that requires one.

        Returns:
            List of non-negative integers aligned with ``self._strategies``.
        """
        padded = list(keys) + [None] * (len(self._strategies) - len(keys))
        results: list[int] = []
        for strategy, key in zip(self._strategies, padded):
            fn = getattr(strategy, "remaining")
            if key is not None:
                results.append(fn(key))
            else:
                results.append(fn())
        return results

    def reset(self, *keys: str | None) -> None:
        """Resets all composed strategies.

        Args:
            *keys: One key per positional strategy that requires one.
        """
        padded = list(keys) + [None] * (len(self._strategies) - len(keys))
        for strategy, key in zip(self._strategies, padded):
            fn = getattr(strategy, "reset")
            if key is not None:
                fn(key)
            else:
                fn()

    def __repr__(self) -> str:  # noqa: D105
        return f"CompositeStrategy(strategies={self._strategies!r})"
