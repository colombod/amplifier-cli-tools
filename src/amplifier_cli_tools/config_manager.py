"""Configuration file management for amplifier-cli-tools.

Provides utilities for reading, writing, and modifying the user's config file.
"""

from pathlib import Path
import tomllib

from .config import DEFAULT_CONFIG_PATH


def get_config_path() -> Path:
    """Get the user's config file path."""
    return DEFAULT_CONFIG_PATH


def config_exists() -> bool:
    """Check if user config file exists."""
    return DEFAULT_CONFIG_PATH.exists()


def read_config_raw() -> dict:
    """Read raw config as dict, or empty dict if not exists."""
    if not DEFAULT_CONFIG_PATH.exists():
        return {}
    with open(DEFAULT_CONFIG_PATH, "rb") as f:
        return tomllib.load(f)


def write_config_raw(data: dict) -> None:
    """Write config dict to file in TOML format.
    
    Note: This is a simple writer that handles the common cases.
    For complex configs, consider using tomlkit for round-trip preservation.
    """
    lines = []
    
    # Write top-level sections
    for section, values in data.items():
        if isinstance(values, dict):
            # Check if this is a nested section (like [dev.windows])
            nested_sections = {}
            flat_values = {}
            
            for key, val in values.items():
                if isinstance(val, dict):
                    nested_sections[key] = val
                else:
                    flat_values[key] = val
            
            # Write section header and flat values
            lines.append(f"[{section}]")
            for key, val in flat_values.items():
                lines.append(f"{key} = {_toml_value(val)}")
            lines.append("")
            
            # Write nested sections
            for nested_name, nested_values in nested_sections.items():
                lines.append(f"[{section}.{nested_name}]")
                for key, val in nested_values.items():
                    lines.append(f"{key} = {_toml_value(val)}")
                lines.append("")
        else:
            # Top-level value (unusual but supported)
            lines.append(f"{section} = {_toml_value(values)}")
    
    DEFAULT_CONFIG_PATH.write_text("\n".join(lines))


def _toml_value(val) -> str:
    """Convert Python value to TOML string representation."""
    if isinstance(val, bool):
        return "true" if val else "false"
    elif isinstance(val, str):
        # Escape and quote strings
        escaped = val.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    elif isinstance(val, (int, float)):
        return str(val)
    elif isinstance(val, list):
        items = ", ".join(_toml_value(v) for v in val)
        return f"[{items}]"
    else:
        return str(val)


def get_setting(section: str, key: str, default=None):
    """Get a specific setting value.
    
    Args:
        section: Config section (e.g., "dev", "reset")
        key: Setting key within section
        default: Default value if not set
        
    Returns:
        Setting value or default
    """
    config = read_config_raw()
    return config.get(section, {}).get(key, default)


def set_setting(section: str, key: str, value) -> None:
    """Set a specific setting value.
    
    Creates the config file if it doesn't exist.
    
    Args:
        section: Config section (e.g., "dev", "reset")
        key: Setting key within section
        value: Value to set
    """
    from importlib import resources
    
    # If config doesn't exist, start with defaults
    if not config_exists():
        try:
            template_bytes = (
                resources.files("amplifier_cli_tools")
                .joinpath("templates", "default-config.toml")
                .read_bytes()
            )
            config = tomllib.loads(template_bytes.decode("utf-8"))
        except Exception:
            config = {}
    else:
        config = read_config_raw()
    
    # Ensure section exists
    if section not in config:
        config[section] = {}
    
    # Set the value
    config[section][key] = value
    
    # Write back
    write_config_raw(config)


def show_config() -> str:
    """Return formatted display of current configuration."""
    from .config import load_config, get_default_config
    
    config = load_config()
    defaults = get_default_config()
    
    lines = []
    lines.append(f"Config file: {DEFAULT_CONFIG_PATH}")
    lines.append(f"  Exists: {'yes' if config_exists() else 'no (using defaults)'}")
    lines.append("")
    
    # Dev settings
    lines.append("[dev]")
    use_tmux_default = defaults.dev.use_tmux
    use_tmux_current = config.dev.use_tmux
    marker = "" if use_tmux_current == use_tmux_default else " (customized)"
    lines.append(f"  use_tmux = {str(use_tmux_current).lower()}{marker}")
    lines.append(f"  main_command = \"{config.dev.main_command}\"")
    lines.append(f"  repos = [{len(config.dev.repos)} repos]")
    lines.append(f"  windows = [{len(config.dev.windows)} windows]")
    
    return "\n".join(lines)


__all__ = [
    "get_config_path",
    "config_exists",
    "read_config_raw",
    "write_config_raw",
    "get_setting",
    "set_setting",
    "show_config",
]
