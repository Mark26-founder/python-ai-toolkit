"""Deterministic cache key generation from arbitrary arguments."""

from dataclasses import asdict, is_dataclass
import hashlib
import json
from typing import Any
from .exceptions import CacheKeyError


def make_deterministic(val: Any) -> Any:
    """Recursively converts structures to a sorted, deterministic representation.

    Supports primitives, lists, tuples, dictionaries, sets, and dataclasses.
    """
    if isinstance(val, (str, int, float, bool, type(None))):
        return val
    if is_dataclass(val):
        return make_deterministic(asdict(val))
    if isinstance(val, dict):
        return {str(k): make_deterministic(v) for k, v in sorted(val.items())}
    if isinstance(val, (list, tuple, set)):
        return [make_deterministic(item) for item in val]

    # Fallback to string representation for complex or unhandled types
    return str(val)


def generate_key(*args: Any, **kwargs: Any) -> str:
    """Generates a stable, deterministic SHA-256 hash from function inputs.

    Args:
        *args: Positional arguments.
        **kwargs: Keyword arguments.

    Returns:
        A deterministic hex string key.

    Raises:
        CacheKeyError: If generation fails.
    """
    try:
        det_args = make_deterministic(args)
        det_kwargs = make_deterministic(kwargs)

        serialized = json.dumps(
            {"args": det_args, "kwargs": det_kwargs},
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    except Exception as e:
        raise CacheKeyError(f"Failed to generate cache key: {e}") from e
