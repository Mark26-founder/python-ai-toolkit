"""Thread-safe in-memory cache implementation."""

from typing import Any, Dict, NamedTuple, Optional
import threading
import time
from .exceptions import CacheConfigurationError, CacheMissError
from .policies import EvictionPolicy, LRUPolicy


class CacheEntry(NamedTuple):
    """Represents a value and its expiration time in the cache."""

    value: Any
    expires_at: Optional[float]

    def is_expired(self) -> bool:
        """Determines if the entry's TTL has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


class Cache:
    """Thread-safe in-memory cache with TTL and custom eviction support."""

    def __init__(
        self,
        max_size: Optional[int] = None,
        policy: Optional[EvictionPolicy] = None,
        default_ttl: Optional[float] = None,
    ) -> None:
        """Initializes the Cache.

        Args:
            max_size: Maximum cache capacity.
            policy: Eviction policy. Defaults to LRUPolicy if max_size is set.
            default_ttl: Default TTL in seconds.

        Raises:
            CacheConfigurationError: If configuration boundaries are violated.
        """
        if max_size is not None and max_size <= 0:
            raise CacheConfigurationError("max_size must be a positive integer.")

        self._max_size = max_size
        self._policy = policy or (LRUPolicy() if max_size is not None else None)
        self._default_ttl = default_ttl

        self._store: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> Any:
        """Retrieves a value from the cache.

        Args:
            key: Target cache key.

        Returns:
            The cached value.

        Raises:
            CacheMissError: If key is missing or expired.
        """
        with self._lock:
            if key not in self._store:
                raise CacheMissError(f"Key '{key}' not found in cache.")

            entry = self._store[key]
            if entry.is_expired():
                self.delete(key)
                raise CacheMissError(f"Key '{key}' has expired.")

            if self._policy:
                self._policy.record_access(key)

            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Inserts or updates a value in the cache.

        Args:
            key: Target cache key.
            value: Value to store.
            ttl: Custom TTL in seconds. Defaults to instance default_ttl.
        """
        with self._lock:
            # 1. Prune expired entries to reclaim space
            now = time.time()
            expired_keys = [k for k, v in self._store.items() if v.is_expired()]
            for k in expired_keys:
                self.delete(k)

            # 2. Determine expiration time
            actual_ttl = ttl if ttl is not None else self._default_ttl
            expires_at = now + actual_ttl if actual_ttl is not None else None
            entry = CacheEntry(value=value, expires_at=expires_at)

            # 3. Handle updates
            if key in self._store:
                self._store[key] = entry
                if self._policy:
                    self._policy.record_insert(key)
                return

            # 4. Handle size limits and eviction
            if self._max_size is not None and len(self._store) >= self._max_size:
                if self._policy:
                    evicted_key = self._policy.evict()
                    if evicted_key and evicted_key in self._store:
                        del self._store[evicted_key]

            # 5. Insert new key
            self._store[key] = entry
            if self._policy:
                self._policy.record_insert(key)

    def delete(self, key: str) -> None:
        """Removes a value from the cache if it exists."""
        with self._lock:
            if key in self._store:
                del self._store[key]
                if self._policy:
                    self._policy.record_delete(key)

    def clear(self) -> None:
        """Clears all entries from the cache."""
        with self._lock:
            self._store.clear()
            if self._policy:
                # Reset eviction policy state by re-instantiating
                self._policy = type(self._policy)()

    def contains(self, key: str) -> bool:
        """Checks if a key exists and is not expired."""
        with self._lock:
            if key not in self._store:
                return False
            entry = self._store[key]
            if entry.is_expired():
                self.delete(key)
                return False
            return True

    def size(self) -> int:
        """Returns the number of non-expired cache entries."""
        with self._lock:
            expired_keys = [k for k, v in self._store.items() if v.is_expired()]
            for k in expired_keys:
                self.delete(k)
            return len(self._store)
