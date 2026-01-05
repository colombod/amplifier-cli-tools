"""Git repository and submodule operations for workspace setup."""

from pathlib import Path

from .shell import ShellError, run


def repo_name_from_url(url: str) -> str:
    """Extract repository name from URL.

    Handles both HTTPS and SSH URLs, stripping .git suffix.

    Args:
        url: Git repository URL (HTTPS or SSH format)

    Returns:
        Repository name without .git suffix

    Examples:
        >>> repo_name_from_url("https://github.com/org/repo.git")
        'repo'
        >>> repo_name_from_url("git@github.com:org/repo.git")
        'repo'
        >>> repo_name_from_url("https://github.com/org/repo")
        'repo'
    """
    # Handle SSH format: git@host:org/repo.git
    if ":" in url and not url.startswith(("http://", "https://")):
        url = url.split(":")[-1]

    # Get basename and strip .git suffix
    name = Path(url).name
    if name.endswith(".git"):
        name = name[:-4]

    return name


def is_git_repo(path: Path) -> bool:
    """Check if path is a git repository.

    Args:
        path: Directory path to check

    Returns:
        True if path contains a .git directory or file, False otherwise
    """
    git_path = path / ".git"
    return git_path.exists()


def init_repo(workdir: Path) -> None:
    """Initialize git repository.

    Creates the directory if it doesn't exist. Skips initialization
    if already a git repository.

    Args:
        workdir: Directory to initialize as git repository

    Raises:
        ShellError: If git init fails
    """
    # Create directory if needed
    workdir.mkdir(parents=True, exist_ok=True)

    # Skip if already a git repo
    if is_git_repo(workdir):
        print(f"Directory {workdir} is already a git repository")
        return

    print(f"Initializing git repository in {workdir}")
    run(["git", "init"], cwd=workdir)


def add_submodule(workdir: Path, repo_url: str) -> None:
    """Add git submodule.

    Extracts repository name from URL and adds as submodule.
    Skips if submodule directory already exists.

    Args:
        workdir: Working directory (must be a git repository)
        repo_url: Git repository URL to add as submodule

    Raises:
        ShellError: If git submodule add fails
    """
    repo_name = repo_name_from_url(repo_url)
    submodule_path = workdir / repo_name

    # Skip if submodule directory already exists
    if submodule_path.exists():
        print(f"Submodule {repo_name} already exists, skipping")
        return

    print(f"Adding submodule {repo_name}...")
    run(["git", "submodule", "add", repo_url], cwd=workdir)


def checkout_submodules_to_main(workdir: Path) -> None:
    """Checkout all submodules to main branch and pull latest.

    Uses git submodule foreach to iterate over all submodules,
    checkout main branch, and pull latest changes.

    Args:
        workdir: Working directory containing submodules

    Raises:
        ShellError: If git operations fail
    """
    print("Checking out submodules to main branch...")
    run(
        ["git", "submodule", "foreach", "git checkout main && git pull"],
        cwd=workdir,
    )


def initial_commit(workdir: Path, message: str) -> None:
    """Stage all files and create commit.

    Args:
        workdir: Working directory (must be a git repository)
        message: Commit message

    Raises:
        ShellError: If git add or commit fails
    """
    print(f"Creating initial commit: {message}")
    run(["git", "add", "."], cwd=workdir)
    run(["git", "commit", "-m", message], cwd=workdir)
