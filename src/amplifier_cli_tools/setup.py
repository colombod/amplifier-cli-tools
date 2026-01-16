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
    """Create layered tmux config structure.

    Creates:
    - ~/.config/amplifier-cli-tools/tmux.conf (base, always updated)
    - ~/.config/amplifier-cli-tools/tmux.conf.local (user customizations, created once)
    - ~/.tmux.conf (wrapper that sources both, created once)

    Returns:
        True if config created successfully, False on error.
    """
    config_dir = Path.home() / ".config" / "amplifier-cli-tools"
    config_dir.mkdir(parents=True, exist_ok=True)

    base_conf = config_dir / "tmux.conf"
    local_conf = config_dir / "tmux.conf.local"
    wrapper_conf = Path.home() / ".tmux.conf"

    # Always overwrite base config (gets updates)
    try:
        template_bytes = (
            resources.files("amplifier_cli_tools")
            .joinpath("templates", "minimal-tmux.conf")
            .read_bytes()
        )
        base_conf.write_bytes(template_bytes)
        print(f"Updated base config: {base_conf}")
    except Exception as e:
        print(f"Failed to write base tmux config: {e}")
        return False

    # Create local config if it doesn't exist
    if not local_conf.exists():
        local_conf.write_text(
            "# Your personal tmux customizations\n# Add your tmux settings here\n"
        )
        print(f"Created local config: {local_conf}")
    else:
        print(f"Local config exists: {local_conf}")

    # Create wrapper if it doesn't exist
    if not wrapper_conf.exists():
        wrapper_content = """# Amplifier base config (updated by amplifier-dev setup)
source-file ~/.config/amplifier-cli-tools/tmux.conf

# Your local customizations (never touched by amplifier-dev)
if-shell "[ -f ~/.config/amplifier-cli-tools/tmux.conf.local ]" \\
    "source-file ~/.config/amplifier-cli-tools/tmux.conf.local"
"""
        wrapper_conf.write_text(wrapper_content)
        print(f"Created wrapper: {wrapper_conf}")
        print("  - Sources base config (gets updates)")
        print("  - Sources local config (your customizations)")
    else:
        print(f"Wrapper exists: {wrapper_conf}")

    return True


def ensure_wezterm_conf(interactive: bool = True) -> bool:
    """Create layered WezTerm config structure.

    Creates:
    - ~/.config/amplifier-cli-tools/wezterm.lua (base, always updated)
    - ~/.config/amplifier-cli-tools/wezterm.lua.local (user customizations, created once)
    - ~/.wezterm.lua (wrapper that loads both, created once)

    Args:
        interactive: If True, prompt user before creating.

    Returns:
        True if config created successfully, False on error.
    """
    # Check if WezTerm is installed
    if not command_exists("wezterm"):
        # Not installed - skip silently
        return True

    config_dir = Path.home() / ".config" / "amplifier-cli-tools"
    config_dir.mkdir(parents=True, exist_ok=True)

    base_conf = config_dir / "wezterm.lua"
    local_conf = config_dir / "wezterm.lua.local"
    wrapper_conf = Path.home() / ".wezterm.lua"

    # Check if wrapper exists - if so, just update base
    if wrapper_conf.exists():
        # Just update base config, skip interactive prompts
        try:
            template_bytes = (
                resources.files("amplifier_cli_tools")
                .joinpath("templates", "wezterm.lua")
                .read_bytes()
            )
            base_conf.write_bytes(template_bytes)
            print(f"Updated base config: {base_conf}")
            return True
        except Exception as e:
            print(f"Failed to write base WezTerm config: {e}")
            return False

    # No wrapper exists - offer to create full layered setup
    print("WezTerm detected but no config found.")

    if interactive:
        response = (
            input(
                "Create WezTerm config? (Catppuccin theme, WSL support, tmux-friendly keys) [Y/n] "
            )
            .strip()
            .lower()
        )
        if response not in ("", "y", "yes"):
            print("Skipping WezTerm config")
            return True

    # Always overwrite base config (gets updates)
    try:
        template_bytes = (
            resources.files("amplifier_cli_tools")
            .joinpath("templates", "wezterm.lua")
            .read_bytes()
        )
        base_conf.write_bytes(template_bytes)
        print(f"Updated base config: {base_conf}")
    except Exception as e:
        print(f"Failed to write base WezTerm config: {e}")
        return False

    # Create local config if it doesn't exist
    if not local_conf.exists():
        local_conf.write_text(
            "-- Your personal WezTerm customizations\n"
            "-- Return a table with settings to override base config\n"
            "-- Example: local config = {}\n"
            "--          config.font_size = 18.0\n"
            "--          return config\n"
            "return {}\n"
        )
        print(f"Created local config: {local_conf}")
    else:
        print(f"Local config exists: {local_conf}")

    # Create wrapper
    wrapper_content = """-- Amplifier base config (updated by amplifier-dev setup)
local config = dofile(os.getenv("HOME") .. "/.config/amplifier-cli-tools/wezterm.lua")

-- Merge your local customizations (never touched by amplifier-dev)
local local_config_path = os.getenv("HOME") .. "/.config/amplifier-cli-tools/wezterm.lua.local"
local ok, local_config = pcall(dofile, local_config_path)
if ok and local_config then
  for k, v in pairs(local_config) do
    config[k] = v
  end
end

return config
"""
    wrapper_conf.write_text(wrapper_content)
    print(f"Created wrapper: {wrapper_conf}")
    print("  - Loads base config (gets updates)")
    print("  - Merges local config (your customizations)")

    return True


def ensure_local_bin_in_path() -> None:
    """Check if ~/.local/bin is in PATH and warn if not."""
    local_bin = Path.home() / ".local" / "bin"

    # Simple check - look for ~/.local/bin in PATH
    import os

    path = os.environ.get("PATH", "")
    if str(local_bin) not in path and "/.local/bin" not in path:
        print(f"\nNote: {local_bin} may not be in your PATH.")
        print("Add this to your ~/.bashrc or ~/.zshrc:")
        print('  export PATH="$HOME/.local/bin:$PATH"')


def run_setup(
    interactive: bool = True, skip_tools: bool = False, skip_tmux: bool = False
) -> bool:
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
