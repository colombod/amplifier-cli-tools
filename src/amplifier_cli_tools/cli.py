"""CLI entry points for amplifier-cli-tools.

Thin layer that parses arguments and calls business logic modules.
All business logic is in dev.py and reset.py - this module only handles:
- Argument parsing via argparse
- Error handling and exit codes
- User confirmation prompts

Entry Points
------------
- main_dev(): amplifier-dev command
- main_reset(): amplifier-reset command
"""

import argparse
import sys
from pathlib import Path

from .config import load_config
from . import dev
from . import reset
from . import tmux


def _confirm(message: str) -> bool:
    """Prompt user for confirmation.

    Args:
        message: Message to display before [y/N] prompt.

    Returns:
        True if user confirms with 'y' or 'Y', False otherwise.
    """
    try:
        response = input(f"{message}\n\nAre you sure? [y/N] ")
        return response.lower() == "y"
    except EOFError:
        return False


def main_dev() -> int:
    """Entry point for amplifier-dev command.

    Creates and launches an Amplifier development workspace with tmux.

    Returns:
        Exit code (0 success, 1 error, 130 keyboard interrupt)
    """
    parser = argparse.ArgumentParser(
        prog="amplifier-dev",
        description="Create and launch an Amplifier development workspace.",
    )
    parser.add_argument(
        "workdir",
        metavar="WORKDIR",
        type=Path,
        help="Directory for workspace",
    )
    parser.add_argument(
        "-d",
        "--destroy",
        action="store_true",
        help="Destroy session and delete workspace (with confirmation)",
    )
    parser.add_argument(
        "-p",
        "--prompt",
        metavar="TEXT",
        help="Override default prompt",
    )
    parser.add_argument(
        "-e",
        "--extra",
        metavar="TEXT",
        help="Append to prompt",
    )
    parser.add_argument(
        "-c",
        "--config",
        metavar="FILE",
        type=Path,
        help="Use specific config file",
    )
    parser.add_argument(
        "--no-tmux",
        action="store_true",
        help="Setup workspace only, don't launch tmux",
    )

    args = parser.parse_args()

    try:
        config = load_config(args.config)
        workdir = args.workdir.resolve()

        if args.destroy:
            # Derive session name from workdir
            session_name = dev.get_session_name(workdir)

            # Build confirmation message
            message = "This will:"
            if tmux.session_exists(session_name):
                message += f"\n  1. Kill tmux session '{session_name}'"
                message += f"\n  2. Delete directory '{workdir}'"
            else:
                message += f"\n  1. Delete directory '{workdir}'"

            if not _confirm(message):
                print("Aborted.")
                return 0

            dev.destroy_workspace(workdir, session_name)
            return 0

        # Run dev workflow
        success = dev.run_dev(
            config=config.dev,
            workdir=workdir,
            prompt=args.prompt,
            extra=args.extra,
            no_tmux=args.no_tmux,
        )
        return 0 if success else 1

    except KeyboardInterrupt:
        print("\nAborted.")
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main_reset() -> int:
    """Entry point for amplifier-reset command.

    Resets the Amplifier installation by removing ~/.amplifier and reinstalling.

    Returns:
        Exit code (0 success, 1 error, 130 keyboard interrupt)
    """
    parser = argparse.ArgumentParser(
        prog="amplifier-reset",
        description="Reset Amplifier installation.",
    )
    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Remove entire ~/.amplifier including preserved dirs",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Skip confirmation prompt",
    )
    parser.add_argument(
        "--no-install",
        action="store_true",
        help="Uninstall only, don't reinstall",
    )
    parser.add_argument(
        "--no-launch",
        action="store_true",
        help="Don't launch amplifier after install",
    )

    args = parser.parse_args()

    try:
        config = load_config()

        # Confirmation unless --yes
        if not args.yes:
            if args.all:
                message = "This will remove ~/.amplifier entirely (including preserved directories)."
            else:
                preserved = ", ".join(config.reset.preserve) if config.reset.preserve else "none"
                message = f"This will reset ~/.amplifier (preserving: {preserved})."

            if not args.no_install:
                message += "\nAmplifier will be reinstalled afterward."

            if not _confirm(message):
                print("Aborted.")
                return 0

        # Run reset workflow
        success = reset.run_reset(
            config=config.reset,
            remove_all=args.all,
            skip_confirm=True,  # We already confirmed above
            no_install=args.no_install,
            no_launch=args.no_launch,
        )
        return 0 if success else 1

    except KeyboardInterrupt:
        print("\nAborted.")
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
