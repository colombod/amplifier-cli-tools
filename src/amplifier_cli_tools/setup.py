"""First-run setup for amplifier-cli-tools.

This module handles automatic installation of dependencies and configuration
to make the tool work out-of-the-box on fresh WSL/Ubuntu or macOS systems.
"""

from importlib import resources
from pathlib import Path

from .shell import command_exists, try_install_tool


# Tools required for full functionality
REQUIRED_TOOLS = ["git", "tmux"]
OPTIONAL_TOOLS = ["mosh", "lazygit", "mc"]


def check_and_install_tools(interactive: bool = True) -> dict[str, bool]:
    """Check for required tools and attempt to install missing ones.
    
    Args:
        interactive: If True, prompt user before installing.
        
    Returns:
        Dict mapping tool name to availability (True = available).
    """
    results = {}
    
    # Check required tools
    for tool in REQUIRED_TOOLS:
        if command_exists(tool):
            results[tool] = True
        else:
            print(f"Required tool '{tool}' not found.")
            if interactive:
                response = input(f"Install {tool}? [Y/n] ").strip().lower()
                if response in ("", "y", "yes"):
                    results[tool] = try_install_tool(tool)
                else:
                    results[tool] = False
            else:
                results[tool] = try_install_tool(tool)
    
    # Check optional tools
    for tool in OPTIONAL_TOOLS:
        if command_exists(tool):
            results[tool] = True
        else:
            print(f"Optional tool '{tool}' not found.")
            if interactive:
                response = input(f"Install {tool}? [Y/n] ").strip().lower()
                if response in ("", "y", "yes"):
                    results[tool] = try_install_tool(tool)
                else:
                    print(f"Skipping {tool} (window will show install instructions)")
                    results[tool] = False
            else:
                results[tool] = try_install_tool(tool)
    
    return results


def ensure_tmux_conf() -> bool:
    """Create minimal tmux.conf if none exists.
    
    Returns:
        True if tmux.conf exists or was created, False on error.
    """
    tmux_conf = Path.home() / ".tmux.conf"
    
    if tmux_conf.exists():
        print(f"tmux config exists: {tmux_conf}")
        return True
    
    print(f"No tmux config found at {tmux_conf}")
    response = input("Create minimal tmux config with mouse support and keybindings? [Y/n] ").strip().lower()
    
    if response not in ("", "y", "yes"):
        print("Skipping tmux config (tmux will use defaults)")
        return True
    
    try:
        template_bytes = (
            resources.files(__package__)
            .joinpath("templates", "minimal-tmux.conf")
            .read_bytes()
        )
        tmux_conf.write_bytes(template_bytes)
        print(f"Created {tmux_conf}")
        print("  - Mouse support enabled")
        print("  - Alt+arrow pane navigation")
        print("  - Shift+arrow window navigation")
        print("  - Clean status bar")
        return True
    except Exception as e:
        print(f"Failed to create tmux config: {e}")
        return False


def ensure_wezterm_conf(interactive: bool = True) -> bool:
    """Create WezTerm config if WezTerm is installed but no config exists.
    
    Args:
        interactive: If True, prompt user before creating.
    
    Returns:
        True if config exists, was created, or WezTerm not installed.
    """
    # Check if WezTerm is installed
    if not command_exists("wezterm"):
        # Not installed - skip silently
        return True
    
    # WezTerm config locations (check both)
    wezterm_lua = Path.home() / ".wezterm.lua"
    wezterm_xdg = Path.home() / ".config" / "wezterm" / "wezterm.lua"
    
    if wezterm_lua.exists() or wezterm_xdg.exists():
        config_path = wezterm_lua if wezterm_lua.exists() else wezterm_xdg
        print(f"WezTerm config exists: {config_path}")
        return True
    
    print("WezTerm detected but no config found.")
    
    if interactive:
        response = input("Create WezTerm config? (Catppuccin theme, WSL support, tmux-friendly keys) [Y/n] ").strip().lower()
        if response not in ("", "y", "yes"):
            print("Skipping WezTerm config")
            return True
    
    try:
        template_bytes = (
            resources.files(__package__)
            .joinpath("templates", "wezterm.lua")
            .read_bytes()
        )
        wezterm_lua.write_bytes(template_bytes)
        print(f"Created {wezterm_lua}")
        print("  - Catppuccin Mocha color scheme")
        print("  - JetBrains Mono font (with fallbacks)")
        print("  - WSL:Ubuntu as default on Windows")
        print("  - macOS Option key as Meta (for Alt+arrow in tmux)")
        print("  - tmux-friendly keybindings")
        return True
    except Exception as e:
        print(f"Failed to create WezTerm config: {e}")
        return False


def ensure_local_bin_in_path() -> None:
    """Check if ~/.local/bin is in PATH and warn if not."""
    local_bin = Path.home() / ".local" / "bin"
    path_dirs = (Path(p) for p in (Path.home().as_posix() + "/.local/bin",))
    
    # Simple check - look for ~/.local/bin in PATH
    import os
    path = os.environ.get("PATH", "")
    if str(local_bin) not in path and "/.local/bin" not in path:
        print(f"\nNote: {local_bin} may not be in your PATH.")
        print("Add this to your ~/.bashrc or ~/.zshrc:")
        print(f'  export PATH="$HOME/.local/bin:$PATH"')


def run_setup(interactive: bool = True, skip_tools: bool = False, skip_tmux: bool = False) -> bool:
    """Run full first-time setup.
    
    Args:
        interactive: If True, prompt for confirmations.
        skip_tools: If True, skip tool installation.
        skip_tmux: If True, skip tmux.conf creation.
        
    Returns:
        True if setup completed successfully.
    """
    print("=" * 60)
    print("amplifier-cli-tools setup")
    print("=" * 60)
    print()
    
    all_ok = True
    
    # Check and install tools
    if not skip_tools:
        print("Checking required tools...")
        print()
        results = check_and_install_tools(interactive)
        
        # Check if required tools are available
        for tool in REQUIRED_TOOLS:
            if not results.get(tool):
                print(f"ERROR: Required tool '{tool}' is not available.")
                all_ok = False
        
        print()
    
    # Setup tmux config
    if not skip_tmux:
        print("Checking tmux configuration...")
        ensure_tmux_conf()
        print()
    
    # Setup WezTerm config (if WezTerm is installed)
    print("Checking WezTerm configuration...")
    ensure_wezterm_conf(interactive)
    print()
    
    # PATH check
    ensure_local_bin_in_path()
    
    print()
    print("=" * 60)
    if all_ok:
        print("Setup complete! You can now run: amplifier-dev <workdir>")
    else:
        print("Setup completed with errors. Please install missing tools manually.")
    print("=" * 60)
    
    return all_ok


def quick_check() -> tuple[bool, list[str]]:
    """Quick check if essential tools are available.
    
    Returns:
        Tuple of (all_ok, list of missing tools).
    """
    missing = []
    for tool in REQUIRED_TOOLS:
        if not command_exists(tool):
            missing.append(tool)
    return len(missing) == 0, missing


__all__ = [
    "run_setup",
    "check_and_install_tools",
    "ensure_tmux_conf",
    "ensure_wezterm_conf",
    "quick_check",
    "REQUIRED_TOOLS",
    "OPTIONAL_TOOLS",
]
