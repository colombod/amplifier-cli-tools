"""CLI entry points for amplifier-cli-tools.

Thin layer that parses arguments and calls business logic modules.
All business logic is in dev.py, reset.py, and setup.py - this module only handles:
- Argument parsing via argparse
- Error handling and exit codes
- User confirmation prompts

Entry Points
------------
- main_dev(): amplifier-dev command
- main_reset(): amplifier-reset command
- main_setup(): amplifier-setup command
- main_config(): amplifier-config command
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
    # Tmux mode options (mutually exclusive)
    tmux_group = parser.add_mutually_exclusive_group()
    tmux_group.add_argument(
        "--tmux",
        action="store_true",
        dest="use_tmux",
        default=None,
        help="Use tmux (override config)",
    )
    tmux_group.add_argument(
        "--no-tmux",
        action="store_false",
        dest="use_tmux",
        help="Run amplifier directly without tmux (override config)",
    )

    args = parser.parse_args()

    try:
        config = load_config(args.config)
        workdir = args.workdir.resolve()

        # Determine tmux mode: CLI flag overrides config
        use_tmux = args.use_tmux if args.use_tmux is not None else config.dev.use_tmux

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
            no_tmux=not use_tmux,
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


def main_setup() -> int:
    """Entry point for amplifier-setup command.

    Runs first-time setup: installs dependencies and creates tmux config.

    Returns:
        Exit code (0 success, 1 error, 130 keyboard interrupt)
    """
    from . import setup

    parser = argparse.ArgumentParser(
        prog="amplifier-setup",
        description="First-time setup for amplifier-cli-tools. Installs dependencies and creates config.",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Non-interactive mode (auto-accept all prompts)",
    )
    parser.add_argument(
        "--skip-tools",
        action="store_true",
        help="Skip tool installation",
    )
    parser.add_argument(
        "--skip-tmux",
        action="store_true",
        help="Skip tmux.conf creation",
    )

    args = parser.parse_args()

    try:
        success = setup.run_setup(
            interactive=not args.yes,
            skip_tools=args.skip_tools,
            skip_tmux=args.skip_tmux,
        )
        return 0 if success else 1

    except KeyboardInterrupt:
        print("\nAborted.")
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main_config() -> int:
    """Entry point for amplifier-config command.

    View and modify amplifier-cli-tools configuration.

    Returns:
        Exit code (0 success, 1 error)
    """
    from . import config_manager

    parser = argparse.ArgumentParser(
        prog="amplifier-config",
        description="View and modify amplifier-cli-tools configuration.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Show command
    subparsers.add_parser("show", help="Show current configuration")

    # Set command
    set_parser = subparsers.add_parser("set", help="Set a configuration value")
    set_parser.add_argument("key", help="Setting key (e.g., dev.use_tmux)")
    set_parser.add_argument("value", help="Value to set")

    # Get command
    get_parser = subparsers.add_parser("get", help="Get a configuration value")
    get_parser.add_argument("key", help="Setting key (e.g., dev.use_tmux)")

    # Convenience toggles
    subparsers.add_parser("tmux-on", help="Enable tmux mode (shortcut for 'set dev.use_tmux true')")
    subparsers.add_parser("tmux-off", help="Disable tmux mode (shortcut for 'set dev.use_tmux false')")

    args = parser.parse_args()

    try:
        if args.command is None or args.command == "show":
            print(config_manager.show_config())
            return 0

        elif args.command == "get":
            parts = args.key.split(".", 1)
            if len(parts) != 2:
                print("Error: Key must be in format 'section.key' (e.g., dev.use_tmux)")
                return 1
            section, key = parts
            value = config_manager.get_setting(section, key)
            if value is None:
                print(f"{args.key}: (not set)")
            else:
                print(f"{args.key} = {value}")
            return 0

        elif args.command == "set":
            parts = args.key.split(".", 1)
            if len(parts) != 2:
                print("Error: Key must be in format 'section.key' (e.g., dev.use_tmux)")
                return 1
            section, key = parts

            # Parse value
            value_str = args.value.lower()
            if value_str in ("true", "yes", "on", "1"):
                value = True
            elif value_str in ("false", "no", "off", "0"):
                value = False
            else:
                # Try as number, else string
                try:
                    value = int(args.value)
                except ValueError:
                    try:
                        value = float(args.value)
                    except ValueError:
                        value = args.value

            config_manager.set_setting(section, key, value)
            print(f"Set {args.key} = {value}")
            print(f"Config saved to: {config_manager.get_config_path()}")
            return 0

        elif args.command == "tmux-on":
            config_manager.set_setting("dev", "use_tmux", True)
            print("Enabled tmux mode (dev.use_tmux = true)")
            print(f"Config saved to: {config_manager.get_config_path()}")
            return 0

        elif args.command == "tmux-off":
            config_manager.set_setting("dev", "use_tmux", False)
            print("Disabled tmux mode (dev.use_tmux = false)")
            print("amplifier-dev will now run amplifier directly without tmux")
            print(f"Config saved to: {config_manager.get_config_path()}")
            return 0

        else:
            parser.print_help()
            return 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
