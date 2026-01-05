# Amplifier Development Workspace

This is a **temporary working repository** for cross-repo Amplifier development.

## Session Approach

This workspace was created for a **specific task** and will be **destroyed when complete**. The pattern:
1. User spins up fresh workspace via dev scripts (already done)
2. Agent works on the task, committing/pushing to submodule repos
3. User destroys workspace when done (nothing persists here)

This is intentional - each task gets a clean slate. Don't store anything important in this root directory.

## Working Memory

@SCRATCH.md

Once the user establishes the session's intent, create `SCRATCH.md` in this directory as your working memory:
- **What it is**: A scratchpad for plans, important facts, decisions, and current state
- **Purpose**: Drives what to do next, not just a log of what was done
- **Loaded every turn**: The @-mention above injects it into every request
- **Keep it bounded**: Actively prune outdated info, remove completed items, consolidate redundant notes
- **Keep it focused**: Only retain what's needed for remaining work - this is working memory, not an archive

## Workspace Structure

This git repo exists locally only (not pushed anywhere) and contains:

```
./                           # Temporary workspace (local git, throwaway)
├── AGENTS.md                # This file - workspace context
├── SCRATCH.md               # Working memory (create after intent established)
├── amplifier/               # submodule: microsoft/amplifier
├── amplifier-app-cli/       # submodule: microsoft/amplifier-app-cli
├── amplifier-core/          # submodule: microsoft/amplifier-core
├── amplifier-foundation/    # submodule: microsoft/amplifier-foundation
└── [additional submodules]  # Added as needed during work
```

**Base submodules** (installed by setup script):
- `amplifier/` - Entry point repo, docs, getting started
- `amplifier-app-cli/` - CLI application implementation  
- `amplifier-core/` - Kernel (tiny, stable, boring)
- `amplifier-foundation/` - Bundles, behaviors, libraries

**Additional submodules** are added as needed during work (e.g., `amplifier-module-tool-filesystem/`).

## Git Workflow

**This workspace repo:**
- Local only, never pushed anywhere
- Use however you see fit (commits, branches, whatever helps)
- Will be destroyed at session end

**Submodule repos:**
- These ARE real repos pushed to GitHub
- Commit and push your work to these
- Changes here persist beyond the session

**Adding new repos:** When you need content from another Amplifier repo, add it as a submodule:
```bash
git submodule add https://github.com/microsoft/amplifier-module-xyz.git
```
This ensures git tools (lazygit, etc.) properly track status across all repos.

## Key Repos Reference

| Directory | Repo | Purpose |
|-----------|------|---------|
| @amplifier/ | [microsoft/amplifier](https://github.com/microsoft/amplifier) | Entry point, docs, getting started |
| @amplifier-app-cli/ | [microsoft/amplifier-app-cli](https://github.com/microsoft/amplifier-app-cli) | CLI application |
| @amplifier-core/ | [microsoft/amplifier-core](https://github.com/microsoft/amplifier-core) | Kernel - tiny, stable, boring |
| @amplifier-foundation/ | [microsoft/amplifier-foundation](https://github.com/microsoft/amplifier-foundation) | Bundles, behaviors, libraries |

## For More Context

- @amplifier/docs/MODULES.md - Full module ecosystem and repo locations
- @amplifier/docs/REPOSITORY_RULES.md - Repo boundaries and conventions
