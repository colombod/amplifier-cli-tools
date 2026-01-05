"""Clean uninstall and reinstall of Amplifier.

This module implements the amplifier-reset workflow, which:
1. Cleans the UV cache
2. Uninstalls Amplifier via uv tool
3. Removes ~/.amplifier directory (preserving configured dirs)
4. Reinstalls Amplifier from configured source
5. Optionally launches Amplifier

Example:
    >>> from amplifier_cli_tools.config import load_config
    >>> from amplifier_cli_tools.reset import run_reset
    >>> config = load_config()
    >>> run_reset(config.reset)
"""

import os
import shutil
from pathlib import Path

from .config import ResetConfig
from .shell import run, command_exists, ShellError


AMPLIFIER_DIR = Path.home() / ".amplifier"


def show_plan(
    config: ResetConfig, remove_all: bool, no_install: bool, no_launch: bool
) -> None:
    """Print the reset plan to stdout.

    Args:
        config: Reset configuration
        remove_all: Whether all dirs will be removed (including preserved)
        no_install: Whether reinstall will be skipped
        no_launch: Whether launch will be skipped
    """
    print("Reset Plan:")
    print("  1. Clean UV cache")
    print("  2. Uninstall amplifier (if installed)")

    if remove_all:
        print(f"  3. Remove {AMPLIFIER_DIR} (ALL contents)")
    else:
        preserved = ", ".join(config.preserve) if config.preserve else "(none)"
        print(f"  3. Remove {AMPLIFIER_DIR} (preserving: {preserved})")

    if no_install:
        print("  4. Skip reinstall (--no-install)")
    else:
        print(f"  4. Install amplifier from: {config.install_source}")

    if no_install:
        print("  5. Skip launch (no install)")
    elif no_launch:
        print("  5. Skip launch (--no-launch)")
    else:
        print("  5. Launch amplifier")

    print()


def confirm_reset() -> bool:
    """Prompt user for confirmation.

    Returns:
        True if user confirms (y/Y), False otherwise.
    """
    try:
        response = input("Proceed? [y/N] ").strip().lower()
        return response == "y"
    except (EOFError, KeyboardInterrupt):
        print()
        return False


def clean_uv_cache() -> bool:
    """Run 'uv cache clean'.

    Returns:
        True on success, False on failure.
    """
    print(">>> Cleaning UV cache...")
    try:
        run("uv cache clean", capture=False)
        return True
    except ShellError as e:
        print(f"Warning: Failed to clean UV cache: {e}")
        return False


def uninstall_amplifier() -> bool:
    """Uninstall amplifier via uv tool uninstall.

    Returns:
        True if uninstalled successfully, False if not installed.
    """
    print(">>> Checking if amplifier is installed...")

    # Check if amplifier is installed via uv tool list
    try:
        result = run("uv tool list", capture=True, quiet=True)
        if "amplifier" not in result.stdout:
            print("    Amplifier is not installed via uv tool")
            return False
    except ShellError:
        print("    Could not check uv tool list")
        return False

    print(">>> Uninstalling amplifier...")
    try:
        run("uv tool uninstall amplifier", capture=False)
        return True
    except ShellError as e:
        print(f"Warning: Failed to uninstall amplifier: {e}")
        return False


def remove_amplifier_dir(preserve: list[str], remove_all: bool) -> bool:
    """Remove ~/.amplifier directory.

    Args:
        preserve: List of directory names to preserve
        remove_all: If True, remove everything including preserved dirs

    Returns:
        True on success.
    """
    print(f">>> Removing {AMPLIFIER_DIR}...")

    if not AMPLIFIER_DIR.exists():
        print("    Directory does not exist, skipping")
        return True

    if remove_all:
        # Remove entire directory
        try:
            shutil.rmtree(AMPLIFIER_DIR)
            print("    Removed entire directory")
            return True
        except OSError as e:
            print(f"Warning: Failed to remove {AMPLIFIER_DIR}: {e}")
            return False

    # Selective removal - preserve specified dirs
    preserve_set = set(preserve)
    removed_count = 0
    preserved_count = 0

    try:
        for item in AMPLIFIER_DIR.iterdir():
            if item.name in preserve_set:
                print(f"    Preserving: {item.name}")
                preserved_count += 1
            else:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
                removed_count += 1

        print(f"    Removed {removed_count} items, preserved {preserved_count}")
        return True
    except OSError as e:
        print(f"Warning: Error during cleanup: {e}")
        return False


def install_amplifier(install_source: str) -> bool:
    """Run 'uv tool install {source}'.

    Args:
        install_source: The pip install source for amplifier

    Returns:
        True on success, False on failure.
    """
    print(f">>> Installing amplifier from {install_source}...")
    try:
        run(f"uv tool install {install_source}", capture=False)
        return True
    except ShellError as e:
        print(f"Error: Failed to install amplifier: {e}")
        return False


def launch_amplifier() -> None:
    """Launch amplifier CLI (replaces current process)."""
    print(">>> Launching amplifier...")
    os.execvp("amplifier", ["amplifier"])


def run_reset(
    config: ResetConfig,
    remove_all: bool = False,
    skip_confirm: bool = False,
    no_install: bool = False,
    no_launch: bool = False,
) -> bool:
    """Main entry point for amplifier-reset workflow.

    Args:
        config: Reset configuration
        remove_all: Remove entire ~/.amplifier including preserved dirs
        skip_confirm: Skip confirmation prompt
        no_install: Uninstall only, don't reinstall
        no_launch: Don't launch amplifier after install

    Returns:
        True on success, False on failure.
    """
    # Step 1: Show plan
    show_plan(config, remove_all, no_install, no_launch)

    # Step 2: Confirm unless skipped
    if not skip_confirm:
        if not confirm_reset():
            print("Aborted.")
            return False

    # Step 3: Clean UV cache
    clean_uv_cache()

    # Step 4: Uninstall amplifier if installed
    uninstall_amplifier()

    # Step 5: Remove ~/.amplifier
    remove_amplifier_dir(config.preserve, remove_all)

    # Step 6: Reinstall if not skipped
    if not no_install:
        if not install_amplifier(config.install_source):
            return False

    # Step 7: Launch if not skipped
    if not no_install and not no_launch:
        launch_amplifier()
        # Note: execvp replaces the process, so we won't reach here

    print(">>> Reset complete!")
    return True


__all__ = [
    "run_reset",
    "show_plan",
    "confirm_reset",
    "clean_uv_cache",
    "uninstall_amplifier",
    "remove_amplifier_dir",
    "install_amplifier",
    "launch_amplifier",
]
