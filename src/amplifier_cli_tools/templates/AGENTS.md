# Development Workspace

This is a **temporary workspace** for multi-repo development work.

## Workspace Pattern

This workspace was created for a **specific task** and can be destroyed when complete:
1. Spin up fresh workspace via `amplifier-dev ~/work/my-task`
2. Work on the task, committing/pushing changes to submodule repos
3. Destroy workspace when done via `amplifier-dev --destroy ~/work/my-task`

Each task gets a clean slate. Submodule changes persist (they're pushed to their repos), but this workspace directory is disposable.

## Repository Structure

This git repo exists locally only (not pushed anywhere) and contains submodules:

```
./
├── AGENTS.md           # This file - workspace context
├── amplifier/          # submodule
├── amplifier-core/     # submodule
└── amplifier-foundation/  # submodule
```

## Working with Submodules

**This workspace repo:**
- Local only, never pushed anywhere
- Use however you see fit (commits, branches, whatever helps)
- Will be destroyed at task end

**Submodule repos:**
- These ARE real repos pushed to GitHub
- Commit and push your work to these
- Changes here persist beyond the session

### Making Changes

```bash
# Work in a submodule
cd amplifier
git checkout -b my-feature
# ... make changes ...
git add . && git commit -m "feat: my changes"
git push origin my-feature

# Update workspace to track new commit (optional)
cd ..
git add amplifier
git commit -m "Update amplifier submodule"
```

### Adding New Repos

When you need content from another repo, add it as a submodule:
```bash
git submodule add https://github.com/org/another-repo.git
```

## Project Notes

Add your task-specific notes here:
