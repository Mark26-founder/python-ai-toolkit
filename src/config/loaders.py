"""Configuration loaders to import config data from various inputs."""

from typing import Any, Dict, List
from .sources import ConfigSource, DictSource, EnvSource, JsonSource, TomlSource


def merge_configs(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merges the override dictionary into the base dictionary.

    Args:
        base: The base configuration dictionary.
        override: The overriding configuration dictionary.

    Returns:
        A new merged dictionary.
    """
    result = dict(base)
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = merge_configs(result[key], val)
        else:
            result[key] = val
    return result


def load_sources(sources: List[ConfigSource]) -> Dict[str, Any]:
    """Loads and merges configuration data from multiple ConfigSource objects.

    Sources later in the list take precedence and override values from earlier sources.

    Args:
        sources: A list of ConfigSource instances.

    Returns:
        A merged configuration dictionary.
    """
    result: Dict[str, Any] = {}
    for source in sources:
        data = source.load()
        result = merge_configs(result, data)
    return result


def load_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to load configuration from a dictionary.

    Args:
        data: The input configuration dictionary.

    Returns:
        The loaded dictionary.
    """
    return DictSource(data).load()


def load_env(prefix: str = "", strip_prefix: bool = True) -> Dict[str, Any]:
    """Helper to load configuration from environment variables.

    Args:
        prefix: Env variable prefix filter.
        strip_prefix: Whether to strip prefix from keys.

    Returns:
        A dictionary of matching environment variables.
    """
    return EnvSource(prefix, strip_prefix).load()


def load_json(filepath: str, ignore_missing: bool = False) -> Dict[str, Any]:
    """Helper to load configuration from a JSON file.

    Args:
        filepath: Path to the JSON file.
        ignore_missing: If True, returns empty dict if file does not exist.

    Returns:
        A dictionary of the loaded JSON.
    """
    return JsonSource(filepath, ignore_missing).load()


def load_toml(filepath: str, ignore_missing: bool = False) -> Dict[str, Any]:
    """Helper to load configuration from a TOML file.

    Args:
        filepath: Path to the TOML file.
        ignore_missing: If True, returns empty dict if file does not exist.

    Returns:
        A dictionary of the loaded TOML.
    """
    return TomlSource(filepath, ignore_missing).load()
