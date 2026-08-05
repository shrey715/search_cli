import sys
from dataclasses import dataclass, fields
from pathlib import Path
from typing import List, Optional

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


def save_config(config: Config, path: Path = CONFIG_PATH) -> None:
    """Write `config` out as TOML, one key per line. This rewrites the whole
    file, so hand-added comments won't survive a `terch config set`."""
    lines = []
    for f in fields(config):
        value = getattr(config, f.name)
        if value is None:
            continue
        lines.append(f"{f.name} = {_toml_literal(value)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def _toml_literal(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    raise TypeError(f"Unsupported config value type: {type(value)!r}")


def config_field_names() -> List[str]:
    return [f.name for f in fields(Config)]


def _parse_bool(value: str) -> bool:
    lowered = value.strip().lower()
    if lowered in ("true", "1", "yes", "on"):
        return True
    if lowered in ("false", "0", "no", "off"):
        return False
    raise ValueError(f"expected a boolean (true/false), got {value!r}")


def _parse_positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise ValueError("must be a positive integer")
    return parsed


def _parse_nonneg_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise ValueError("must be zero or a positive integer")
    return parsed


def _parse_optional_str(value: str) -> Optional[str]:
    stripped = value.strip()
    return None if stripped.lower() in ("", "none", "unset") else stripped


FIELD_PARSERS = {
    "default_provider": _parse_optional_str,
    "max_results": _parse_positive_int,
    "cache_enabled": _parse_bool,
    "cache_ttl": _parse_nonneg_int,
    "history_enabled": _parse_bool,
}


def set_config_value(key: str, raw_value: str, path: Path = CONFIG_PATH) -> Config:
    if key not in FIELD_PARSERS:
        raise KeyError(key)
    config = load_config(path)
    setattr(config, key, FIELD_PARSERS[key](raw_value))
    save_config(config, path)
    return config


def unset_config_value(key: str, path: Path = CONFIG_PATH) -> Config:
    if key not in FIELD_PARSERS:
        raise KeyError(key)
    config = load_config(path)
    setattr(config, key, getattr(Config(), key))
    save_config(config, path)
    return config
