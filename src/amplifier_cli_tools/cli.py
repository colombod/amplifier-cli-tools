"""CLI entry points for amplifier-cli-tools.

Thin layer that parses arguments and calls business logic modules.
All business logic is in dev.py, reset.py, and setup.py - this module only handles:
- Argument parsing via argparse
- Error handling and exit codes
- User confirmation prompts

Entry Points
------------
- main_dev(): amplifier-dev command (with setup/config subcommands)
- main_reset(): amplifier-reset command
"""

import argparse
import sys
from pathlib import Path

from .config import load_config, save_reset_preserve
from . import dev
from . import reset
from . import tmux
from .interactive import ChecklistItem, run_checklist


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


def _cmd_run(args: argparse.Namespace) -> int:
    """Handle the default run command (create/attach workspace)."""
    try:
        config = load_config(args.config)
        workdir = args.workdir.resolve()

        # Determine tmux mode: CLI flag overrides config
        use_tmux = args.use_tmux if args.use_tmux is not None else config.dev.use_tmux

        # Handle --kill or --fresh: kill session only, don't delete files
        # --fresh implies --kill but continues to create new session
        if args.kill or args.fresh:
            session_name = dev.get_session_name(workdir)
            if tmux.session_exists(session_name):
                print(f"Killing tmux session: {session_name}")
                tmux.kill_session(session_name)
                print("Session killed.")
            else:
                print(f"No session '{session_name}' to kill.")

            # If --fresh, continue to create new session; otherwise exit
            if not args.fresh:
                return 0

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


def _cmd_setup(args: argparse.Namespace) -> int:
    """Handle the setup subcommand."""
    from . import setup

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


def _cmd_config(args: argparse.Namespace) -> int:
    """Handle the config subcommand."""
    from . import config_manager

    try:
        if args.config_command is None or args.config_command == "show":
            print(config_manager.show_config())
            return 0

        elif args.config_command == "get":
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

        elif args.config_command == "set":
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

        elif args.config_command == "tmux-on":
            config_manager.set_setting("dev", "use_tmux", True)
            print("Enabled tmux mode (dev.use_tmux = true)")
            print(f"Config saved to: {config_manager.get_config_path()}")
            return 0

        elif args.config_command == "tmux-off":
            config_manager.set_setting("dev", "use_tmux", False)
            print("Disabled tmux mode (dev.use_tmux = false)")
            print("amplifier-dev will now run amplifier directly without tmux")
            print(f"Config saved to: {config_manager.get_config_path()}")
            return 0

        else:
            return 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main_dev() -> int:
    """Entry point for amplifier-dev command.

    Supports subcommands:
    - (default): Create and launch workspace
    - setup: First-time setup
    - config: View/modify configuration

    Returns:
        Exit code (0 success, 1 error, 130 keyboard interrupt)
    """
    # Check if first arg is a subcommand
    if len(sys.argv) > 1 and sys.argv[1] in ("setup", "config"):
        return _main_dev_subcommands()

    # Default: workspace mode
    return _main_dev_workspace()


def _main_dev_subcommands() -> int:
    """Handle setup and config subcommands."""
    parser = argparse.ArgumentParser(
        prog="amplifier-dev",
        description="Amplifier development workspace manager.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Setup subcommand
    setup_parser = subparsers.add_parser(
        "setup",
        help="First-time setup: install dependencies and create configs",
    )
    setup_parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Non-interactive mode (auto-accept all prompts)",
    )
    setup_parser.add_argument(
        "--skip-tools",
        action="store_true",
        help="Skip tool installation",
    )
    setup_parser.add_argument(
        "--skip-tmux",
        action="store_true",
        help="Skip tmux.conf creation",
    )

    # Config subcommand
    config_parser = subparsers.add_parser(
        "config",
        help="View and modify configuration",
    )
    config_subparsers = config_parser.add_subparsers(
        dest="config_command", help="Config commands"
    )

    config_subparsers.add_parser("show", help="Show current configuration")
    config_subparsers.add_parser("tmux-on", help="Enable tmux mode")
    config_subparsers.add_parser(
        "tmux-off", help="Disable tmux mode (run amplifier directly)"
    )

    get_parser = config_subparsers.add_parser("get", help="Get a configuration value")
    get_parser.add_argument("key", help="Setting key (e.g., dev.use_tmux)")

    set_parser = config_subparsers.add_parser("set", help="Set a configuration value")
    set_parser.add_argument("key", help="Setting key (e.g., dev.use_tmux)")
    set_parser.add_argument("value", help="Value to set")

    args = parser.parse_args()

    if args.command == "setup":
        return _cmd_setup(args)
    elif args.command == "config":
        return _cmd_config(args)
    else:
        parser.print_help()
        return 0


def _main_dev_workspace() -> int:
    """Handle the default workspace creation command."""
    parser = argparse.ArgumentParser(
        prog="amplifier-dev",
        description="Amplifier development workspace manager.",
        epilog="""
Subcommands:
  setup              First-time setup: install dependencies and create configs
  config             View and modify configuration

Examples:
  amplifier-dev ~/myproject            Create/attach to workspace
  amplifier-dev -k ~/myproject         Kill session (keep files)
  amplifier-dev -f ~/myproject         Kill session and start fresh
  amplifier-dev -d ~/myproject         Destroy workspace (with confirmation)
  amplifier-dev --no-tmux ~/myproject  Run without tmux
  amplifier-dev setup                  First-time setup
  amplifier-dev config show            Show configuration
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "workdir",
        metavar="WORKDIR",
        type=Path,
        nargs="?",
        help="Directory for workspace (required for create/destroy)",
    )
    parser.add_argument(
        "-k",
        "--kill",
        action="store_true",
        help="Kill tmux session only (preserve workspace files)",
    )
    parser.add_argument(
        "-f",
        "--fresh",
        action="store_true",
        help="Kill session and start fresh (implies --kill, then creates new session)",
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

    # If no workdir provided, show help
    if args.workdir is None:
        parser.print_help()
        return 0

    return _cmd_run(args)


def _parse_category_list(value: str) -> set[str]:
    """Parse a comma-separated list of category names.

    Args:
        value: Comma-separated string like "projects,settings,keys"

    Returns:
        Set of valid category names

    Raises:
        argparse.ArgumentTypeError: If any category name is invalid
    """
    categories = {c.strip() for c in value.split(",") if c.strip()}
    valid = set(reset.RESET_CATEGORIES.keys())
    invalid = categories - valid

    if invalid:
        raise argparse.ArgumentTypeError(
            f"Invalid categories: {', '.join(sorted(invalid))}. "
            f"Valid categories: {', '.join(sorted(valid))}"
        )

    return categories


def _run_interactive_reset(config) -> set[str] | None:
    """Run the interactive checklist for reset category selection.

    Args:
        config: Loaded configuration

    Returns:
        Set of category names to preserve, or None if cancelled
    """
    # Build checklist items from categories
    last_preserve = set(config.reset.last_preserve)
    items = []

    for category in reset.CATEGORY_ORDER:
        description = reset.CATEGORY_DESCRIPTIONS.get(category, "")
        selected = category in last_preserve
        items.append(ChecklistItem(key=category, description=description, selected=selected))

    # Run interactive selection
    return run_checklist(items, title="Amplifier Reset")


def main_reset() -> int:
    """Entry point for amplifier-reset command.

    Resets the Amplifier installation by removing ~/.amplifier and reinstalling.

    Returns:
        Exit code (0 success, 1 error, 130 keyboard interrupt)
    """
    parser = argparse.ArgumentParser(
        prog="amplifier-reset",
        description="Reset Amplifier installation.",
        epilog=f"""
Categories: {', '.join(reset.CATEGORY_ORDER)}

Examples:
  amplifier-reset                      Interactive mode (default)
  amplifier-reset --cache-only         Clear only cache (safest)
  amplifier-reset --preserve projects,settings,keys -y
                                       Scripted: preserve specific categories
  amplifier-reset --remove cache,registry -y
                                       Scripted: remove specific categories
  amplifier-reset --full -y            Remove everything (nuclear option)
  amplifier-reset --dry-run            Preview what would be removed
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Category selection (mutually exclusive group)
    category_group = parser.add_mutually_exclusive_group()
    category_group.add_argument(
        "--preserve",
        metavar="LIST",
        type=_parse_category_list,
        help="Comma-separated categories to preserve (e.g., projects,settings,keys)",
    )
    category_group.add_argument(
        "--remove",
        metavar="LIST",
        type=_parse_category_list,
        help="Comma-separated categories to remove (e.g., cache,registry)",
    )
    category_group.add_argument(
        "--cache-only",
        action="store_true",
        help="Only clear cache (safest option, shortcut for --remove cache)",
    )
    category_group.add_argument(
        "--full",
        action="store_true",
        help="Remove everything including projects (nuclear option)",
    )

    # Other options
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Skip interactive prompt (required with --preserve/--remove/--cache-only/--full)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be removed without making changes",
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

        # Determine preserve set based on arguments
        preserve: set[str] | None = None

        if args.full:
            # Full reset - preserve nothing
            preserve = set()
        elif args.cache_only:
            # Only remove cache - preserve everything else
            preserve = set(reset.RESET_CATEGORIES.keys()) - {"cache"}
        elif args.remove is not None:
            # Remove specified categories - preserve everything else
            preserve = set(reset.RESET_CATEGORIES.keys()) - args.remove
        elif args.preserve is not None:
            # Preserve specified categories
            preserve = args.preserve
        elif args.yes:
            # Non-interactive with -y but no category flags: use last_preserve
            preserve = set(config.reset.last_preserve)
        else:
            # Interactive mode
            preserve = _run_interactive_reset(config)
            if preserve is None:
                print("Aborted.")
                return 0

            # Save selections for next time
            save_reset_preserve(sorted(preserve))

        # For scripted mode without -y, require confirmation
        if not args.yes and not args.dry_run:
            # Show what will happen
            preserve_names = sorted(preserve) if preserve else []
            remove_names = sorted(set(reset.RESET_CATEGORIES.keys()) - preserve)

            if not preserve:
                message = "This will remove ~/.amplifier entirely (ALL contents)."
            else:
                message = f"This will reset ~/.amplifier.\n"
                message += f"  Preserving: {', '.join(preserve_names)}\n"
                message += f"  Removing: {', '.join(remove_names)}"

            if not args.no_install:
                message += "\nAmplifier will be reinstalled afterward."

            if not _confirm(message):
                print("Aborted.")
                return 0

        # Run reset workflow
        success = reset.run_reset(
            config=config.reset,
            preserve=preserve,
            skip_confirm=True,  # We already confirmed above or user passed -y
            no_install=args.no_install,
            no_launch=args.no_launch,
            dry_run=args.dry_run,
        )
        return 0 if success else 1

    except KeyboardInterrupt:
        print("\nAborted.")
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
