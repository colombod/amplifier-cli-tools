"""amplifier-cli-tools: CLI tools for Amplifier development workflows.

This package provides command-line utilities for setting up Amplifier
development environments and managing installations.

Commands
--------
amplifier-dev
    Create and launch an Amplifier development workspace with tmux.

amplifier-reset
    Reset the Amplifier installation (uninstall, clean, reinstall).

Configuration
-------------
Configuration is loaded from ~/.amplifier-cli-tools.toml

See config.py for configuration options and defaults.
"""

__version__ = "0.1.0"
__author__ = "Brian Krabach"

from .config import Config, DevConfig, ResetConfig, WindowConfig, load_config
from .cli import main_dev, main_reset

__all__ = [
    "__version__",
    "Config",
    "DevConfig",
    "ResetConfig",
    "WindowConfig",
    "load_config",
    "main_dev",
    "main_reset",
]
