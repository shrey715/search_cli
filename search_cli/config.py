import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

CONFIG_PATH = Path.home() / ".config" / "terch" / "config.toml"


@dataclass
class Config:
    default_provider: Optional[str] = None
    max_results: int = 10
    cache_enabled: bool = True
    cache_ttl: int = 900  # seconds
    history_enabled: bool = True


def load_config(path: Path = CONFIG_PATH) -> Config:
    """Read ~/.config/terch/config.toml if present, falling back to defaults
    for any key that's missing or if the file doesn't exist."""
    config = Config()
    if not path.exists():
        return config

    with path.open("rb") as f:
        data = tomllib.load(f)

    config.default_provider = data.get("default_provider", config.default_provider)
    config.max_results = int(data.get("max_results", config.max_results))
    config.cache_enabled = bool(data.get("cache_enabled", config.cache_enabled))
    config.cache_ttl = int(data.get("cache_ttl", config.cache_ttl))
    config.history_enabled = bool(data.get("history_enabled", config.history_enabled))
    return config
