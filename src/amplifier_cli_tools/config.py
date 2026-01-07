"""Configuration management for amplifier-cli-tools.

Loads TOML configuration from ~/.amplifier-cli-tools.toml with sensible defaults.

Config File Format
------------------
The configuration file uses TOML format:

```toml
[dev]
repos = [
    "https://github.com/microsoft/amplifier.git",
    "https://github.com/microsoft/amplifier-core.git",
    "https://github.com/microsoft/amplifier-foundation.git",
]
main_command = "amplifier run --mode chat"
default_prompt = ""
agents_template = ""  # Path to custom template, empty = use built-in

[dev.windows]
shell = ""        # Empty = shell only (no command)
git = "lazygit"
files = "mc"

[reset]
install_source = "git+https://github.com/microsoft/amplifier"
last_preserve = ["projects", "settings", "keys"]  # Last-used preserve selections
```

Usage
-----
    >>> from amplifier_cli_tools.config import load_config
    >>> config = load_config()
    >>> config.dev.repos
    ['https://github.com/microsoft/amplifier.git', ...]
"""

from dataclasses import dataclass
from importlib import resources
from pathlib import Path
import tomllib


DEFAULT_CONFIG_PATH = Path.home() / ".amplifier-cli-tools.toml"


@dataclass
class WindowConfig:
    """Configuration for a tmux window.

    Attributes:
        name: Window name (e.g., "shell", "git", "files")
        command: Command to run in window. Empty string = shell only (no command)
    """

    name: str
    command: str  # Empty string = shell only (no command)


@dataclass
class DevConfig:
    """Configuration for the 'dev' command.

    Attributes:
        use_tmux: Whether to use tmux (False = run amplifier directly)
        repos: List of git repository URLs to clone
        main_command: Command to run in the main window
        default_prompt: Default prompt to send after main_command starts
        agents_template: Path to custom AGENTS.md template, empty = use built-in
        windows: List of additional tmux windows to create
    """

    use_tmux: bool
    repos: list[str]
    main_command: str
    default_prompt: str
    agents_template: str  # Path to custom template, empty = use built-in
    windows: list[WindowConfig]


@dataclass
class ResetConfig:
    """Configuration for the 'reset' command.

    Attributes:
        install_source: pip install source for amplifier
        last_preserve: Last-used preserve selections (category names)
    """

    install_source: str
    last_preserve: list[str]


@dataclass
class Config:
    """Root configuration object.

    Attributes:
        dev: Configuration for the 'dev' command
        reset: Configuration for the 'reset' command
    """

    dev: DevConfig
    reset: ResetConfig


def _load_bundled_defaults() -> dict:
    """Load default configuration from bundled template file.

    Returns:
        Parsed TOML data as dict, or empty dict if template not found.
    """
    try:
        template_bytes = (
            resources.files(__package__)
            .joinpath("templates", "default-config.toml")
            .read_bytes()
        )
        return tomllib.loads(template_bytes.decode("utf-8"))
    except (FileNotFoundError, TypeError, tomllib.TOMLDecodeError):
        return {}


def _get_hardcoded_fallback() -> Config:
    """Absolute fallback if bundled template can't be loaded.

    This should rarely be needed - only if the package is corrupted.
    """
    return Config(
        dev=DevConfig(
            use_tmux=True,
            repos=[
                "https://github.com/microsoft/amplifier.git",
                "https://github.com/microsoft/amplifier-core.git",
                "https://github.com/microsoft/amplifier-foundation.git",
            ],
            main_command="amplifier run --mode chat",
            default_prompt="",
            agents_template="",
            windows=[
                WindowConfig(name="shell", command=""),
                WindowConfig(name="git", command="lazygit"),
                WindowConfig(name="files", command="mc"),
            ],
        ),
        reset=ResetConfig(
            install_source="git+https://github.com/microsoft/amplifier",
            last_preserve=["projects", "settings", "keys"],
        ),
    )


def get_default_config() -> Config:
    """Return default configuration from bundled template.

    Loads defaults from templates/default-config.toml. This file is the
    single source of truth for default values. Falls back to hardcoded
    values only if the template can't be loaded.

    Returns:
        Config with default settings from bundled template.
    """
    data = _load_bundled_defaults()

    # If template couldn't be loaded, use hardcoded fallback
    if not data:
        return _get_hardcoded_fallback()

    # Parse the template data into Config
    dev_data = data.get("dev", {})
    reset_data = data.get("reset", {})

    return Config(
        dev=DevConfig(
            use_tmux=dev_data.get("use_tmux", True),
            repos=dev_data.get("repos", []),
            main_command=dev_data.get("main_command", ""),
            default_prompt=dev_data.get("default_prompt", ""),
            agents_template=dev_data.get("agents_template", ""),
            windows=_parse_windows(dev_data.get("windows", {})),
        ),
        reset=ResetConfig(
            install_source=reset_data.get("install_source", ""),
            last_preserve=reset_data.get(
                "last_preserve", ["projects", "settings", "keys"]
            ),
        ),
    )


def _parse_windows(windows_dict: dict[str, str]) -> list[WindowConfig]:
    """Convert windows dict from TOML to list of WindowConfig.

    Args:
        windows_dict: Dict mapping window name to command

    Returns:
        List of WindowConfig objects
    """
    return [WindowConfig(name=name, command=cmd) for name, cmd in windows_dict.items()]


def _expand_path(path_str: str) -> str:
    """Expand ~ in path strings.

    Args:
        path_str: Path string potentially containing ~

    Returns:
        Expanded path string, or empty string if input was empty
    """
    if not path_str:
        return path_str
    return str(Path(path_str).expanduser())


def load_config(config_path: Path | None = None) -> Config:
    """Load config from file, merging with defaults.

    Args:
        config_path: Optional path to config file. If None, uses
            ~/.amplifier-cli-tools.toml

    Returns:
        Config object with file values overriding defaults.
        If config file doesn't exist, returns defaults.
    """
    defaults = get_default_config()

    # Determine config file path
    path = config_path if config_path is not None else DEFAULT_CONFIG_PATH

    # If file doesn't exist, return defaults
    if not path.exists():
        return defaults

    # Load TOML file
    with open(path, "rb") as f:
        data = tomllib.load(f)

    # Merge dev section
    dev_data = data.get("dev", {})
    dev_config = DevConfig(
        use_tmux=dev_data.get("use_tmux", defaults.dev.use_tmux),
        repos=dev_data.get("repos", defaults.dev.repos),
        main_command=dev_data.get("main_command", defaults.dev.main_command),
        default_prompt=dev_data.get("default_prompt", defaults.dev.default_prompt),
        agents_template=_expand_path(
            dev_data.get("agents_template", defaults.dev.agents_template)
        ),
        windows=(
            _parse_windows(dev_data["windows"])
            if "windows" in dev_data
            else defaults.dev.windows
        ),
    )

    # Merge reset section
    reset_data = data.get("reset", {})
    reset_config = ResetConfig(
        install_source=reset_data.get("install_source", defaults.reset.install_source),
        last_preserve=reset_data.get("last_preserve", defaults.reset.last_preserve),
    )

    return Config(dev=dev_config, reset=reset_config)


def save_reset_preserve(preserve: list[str], config_path: Path | None = None) -> None:
    """Save the last-used preserve selections to config file.

    Updates only the reset.last_preserve field, preserving all other settings.

    Args:
        preserve: List of category names that were preserved
        config_path: Optional path to config file. If None, uses default.
    """
    path = config_path if config_path is not None else DEFAULT_CONFIG_PATH

    # Load existing config or start fresh
    if path.exists():
        with open(path, "rb") as f:
            data = tomllib.load(f)
    else:
        data = {}

    # Update reset.last_preserve
    if "reset" not in data:
        data["reset"] = {}
    data["reset"]["last_preserve"] = preserve

    # Write back as TOML
    _write_toml(path, data)


def _write_toml(path: Path, data: dict) -> None:
    """Write a dict to a TOML file.

    Note: This is a simple implementation that handles our specific config
    structure. For complex TOML, consider using tomli-w.

    Args:
        path: Path to write to
        data: Dict to serialize
    """
    lines = []

    for section, values in data.items():
        if isinstance(values, dict):
            # Check if this section has nested dicts (like dev.windows)
            simple_values = {}
            nested_sections = {}

            for key, value in values.items():
                if isinstance(value, dict):
                    nested_sections[key] = value
                else:
                    simple_values[key] = value

            # Write section header and simple values
            lines.append(f"[{section}]")
            for key, value in simple_values.items():
                lines.append(f"{key} = {_toml_value(value)}")
            lines.append("")

            # Write nested sections
            for nested_key, nested_values in nested_sections.items():
                lines.append(f"[{section}.{nested_key}]")
                for key, value in nested_values.items():
                    lines.append(f"{key} = {_toml_value(value)}")
                lines.append("")
        else:
            # Top-level value (unusual in our config, but handle it)
            lines.append(f"{section} = {_toml_value(values)}")

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write("\n".join(lines))


def _toml_value(value) -> str:
    """Convert a Python value to TOML string representation.

    Args:
        value: Python value to convert

    Returns:
        TOML string representation
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, str):
        # Escape quotes and backslashes
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, list):
        items = [_toml_value(item) for item in value]
        return "[" + ", ".join(items) + "]"
    else:
        return f'"{value}"'
