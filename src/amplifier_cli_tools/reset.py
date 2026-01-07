"""Clean uninstall and reinstall of Amplifier.

This module implements the amplifier-reset workflow, which:
1. Cleans the UV cache
2. Uninstalls Amplifier via uv tool
3. Removes ~/.amplifier directory (preserving configured categories)
4. Reinstalls Amplifier from configured source
5. Optionally launches Amplifier

Example:
    >>> from amplifier_cli_tools.config import load_config
    >>> from amplifier_cli_tools.reset import run_reset
    >>> config = load_config()
    >>> run_reset(config.reset, preserve={"projects", "settings", "keys"})
"""

import os
import shutil
from pathlib import Path

from .config import ResetConfig
from .shell import run, ShellError


AMPLIFIER_DIR = Path.home() / ".amplifier"

# Category definitions: category name -> list of files/dirs in ~/.amplifier
RESET_CATEGORIES = {
    "projects": ["projects"],  # Session transcripts and history
    "settings": ["settings.yaml"],  # User configuration
    "keys": ["keys.env"],  # API keys
    "cache": ["cache"],  # Downloaded bundles (auto-regenerates)
    "registry": ["registry.json"],  # Bundle mappings (auto-regenerates)
}

# Categories that are safe to remove (auto-regenerate)
SAFE_CATEGORIES = {"cache", "registry"}

# Default categories to preserve
DEFAULT_PRESERVE = {"projects", "settings", "keys"}

# Descriptions for each category (used in UI)
CATEGORY_DESCRIPTIONS = {
    "projects": "Session transcripts and history",
    "settings": "User configuration (settings.yaml)",
    "keys": "API keys (keys.env)",
    "cache": "Downloaded bundles (auto-regenerates)",
    "registry": "Bundle mappings (auto-regenerates)",
}

# Display order for categories
CATEGORY_ORDER = ["projects", "settings", "keys", "cache", "registry"]


def get_preserve_paths(preserve: set[str]) -> set[str]:
    """Convert category names to actual file/directory names.

    Args:
        preserve: Set of category names to preserve

    Returns:
        Set of file/directory names that should be preserved
    """
    paths = set()
    for category in preserve:
        if category in RESET_CATEGORIES:
            paths.update(RESET_CATEGORIES[category])
    return paths


def get_remove_paths(preserve: set[str]) -> set[str]:
    """Get all paths that will be removed (not in preserve set).

    Args:
        preserve: Set of category names to preserve

    Returns:
        Set of file/directory names that will be removed
    """
    all_paths = set()
    for paths in RESET_CATEGORIES.values():
        all_paths.update(paths)

    preserve_paths = get_preserve_paths(preserve)
    return all_paths - preserve_paths


def show_plan(
    config: ResetConfig,
    preserve: set[str],
    no_install: bool,
    no_launch: bool,
    dry_run: bool = False,
) -> None:
    """Print the reset plan to stdout.

    Args:
        config: Reset configuration
        preserve: Set of category names to preserve
        no_install: Whether reinstall will be skipped
        no_launch: Whether launch will be skipped
        dry_run: Whether this is a dry run
    """
    if dry_run:
        print("DRY RUN - No changes will be made\n")

    print("Reset Plan:")
    print("  1. Clean UV cache")
    print("  2. Uninstall amplifier (if installed)")

    # Show what will be preserved/removed
    preserve_names = sorted(preserve) if preserve else []
    remove_names = sorted(set(RESET_CATEGORIES.keys()) - preserve)

    if not preserve:
        print(f"  3. Remove {AMPLIFIER_DIR} (ALL contents)")
    else:
        print(f"  3. Remove {AMPLIFIER_DIR}")
        print(f"       Preserving: {', '.join(preserve_names)}")
        print(f"       Removing: {', '.join(remove_names)}")

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


def clean_uv_cache(dry_run: bool = False) -> bool:
    """Run 'uv cache clean'.

    Args:
        dry_run: If True, only print what would be done

    Returns:
        True on success, False on failure.
    """
    print(">>> Cleaning UV cache...")
    if dry_run:
        print("    [dry-run] Would run: uv cache clean")
        return True

    try:
        run("uv cache clean", capture=False)
        return True
    except ShellError as e:
        print(f"Warning: Failed to clean UV cache: {e}")
        return False


def uninstall_amplifier(dry_run: bool = False) -> bool:
    """Uninstall amplifier via uv tool uninstall.

    Args:
        dry_run: If True, only print what would be done

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
    if dry_run:
        print("    [dry-run] Would run: uv tool uninstall amplifier")
        return True

    try:
        run("uv tool uninstall amplifier", capture=False)
        return True
    except ShellError as e:
        print(f"Warning: Failed to uninstall amplifier: {e}")
        return False


def remove_amplifier_dir(preserve: set[str], dry_run: bool = False) -> bool:
    """Remove ~/.amplifier directory contents based on category preservation.

    Args:
        preserve: Set of category names to preserve
        dry_run: If True, only print what would be done

    Returns:
        True on success.
    """
    print(f">>> Removing {AMPLIFIER_DIR}...")

    if not AMPLIFIER_DIR.exists():
        print("    Directory does not exist, skipping")
        return True

    # Convert categories to actual paths
    preserve_paths = get_preserve_paths(preserve)

    # If nothing to preserve, remove entire directory
    if not preserve_paths:
        if dry_run:
            print(f"    [dry-run] Would remove entire directory: {AMPLIFIER_DIR}")
            return True

        try:
            shutil.rmtree(AMPLIFIER_DIR)
            print("    Removed entire directory")
            return True
        except OSError as e:
            print(f"Warning: Failed to remove {AMPLIFIER_DIR}: {e}")
            return False

    # Selective removal - preserve specified paths
    removed_count = 0
    preserved_count = 0

    try:
        for item in AMPLIFIER_DIR.iterdir():
            if item.name in preserve_paths:
                print(f"    Preserving: {item.name}")
                preserved_count += 1
            else:
                if dry_run:
                    print(f"    [dry-run] Would remove: {item.name}")
                else:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                removed_count += 1

        action = "Would remove" if dry_run else "Removed"
        print(f"    {action} {removed_count} items, preserved {preserved_count}")
        return True
    except OSError as e:
        print(f"Warning: Error during cleanup: {e}")
        return False


def install_amplifier(install_source: str, dry_run: bool = False) -> bool:
    """Run 'uv tool install {source}'.

    Args:
        install_source: The pip install source for amplifier
        dry_run: If True, only print what would be done

    Returns:
        True on success, False on failure.
    """
    print(f">>> Installing amplifier from {install_source}...")
    if dry_run:
        print(f"    [dry-run] Would run: uv tool install {install_source}")
        return True

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
    preserve: set[str] | None = None,
    skip_confirm: bool = False,
    no_install: bool = False,
    no_launch: bool = False,
    dry_run: bool = False,
) -> bool:
    """Main entry point for amplifier-reset workflow.

    Args:
        config: Reset configuration
        preserve: Set of category names to preserve. If None, uses DEFAULT_PRESERVE.
        skip_confirm: Skip confirmation prompt
        no_install: Uninstall only, don't reinstall
        no_launch: Don't launch amplifier after install
        dry_run: Only show what would be done, don't actually do it

    Returns:
        True on success, False on failure.
    """
    # Use default preservation if not specified
    if preserve is None:
        preserve = DEFAULT_PRESERVE.copy()

    # Step 1: Show plan
    show_plan(config, preserve, no_install, no_launch, dry_run)

    # Step 2: Confirm unless skipped
    if not skip_confirm and not dry_run:
        if not confirm_reset():
            print("Aborted.")
            return False

    # Step 3: Clean UV cache
    clean_uv_cache(dry_run)

    # Step 4: Uninstall amplifier if installed
    uninstall_amplifier(dry_run)

    # Step 5: Remove ~/.amplifier
    remove_amplifier_dir(preserve, dry_run)

    if dry_run:
        print(">>> Dry run complete - no changes were made")
        return True

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
    "RESET_CATEGORIES",
    "SAFE_CATEGORIES",
    "DEFAULT_PRESERVE",
    "CATEGORY_DESCRIPTIONS",
    "CATEGORY_ORDER",
    "get_preserve_paths",
    "get_remove_paths",
    "run_reset",
    "show_plan",
    "confirm_reset",
    "clean_uv_cache",
    "uninstall_amplifier",
    "remove_amplifier_dir",
    "install_amplifier",
    "launch_amplifier",
]
