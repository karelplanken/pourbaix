set dotenv-load := true

# Python environment ------------------------------------------------------------------

# Install from the lockfile.
install:
    uv sync --all-extras --all-groups

# Refresh the lockfile and sync (use when you intentionally want newer deps).
upgrade:
    uv lock --upgrade
    uv sync --all-extras --all-groups

# Git hooks -----------------------------------------------------------------------------

# Install prek's git hook shims (reads hook types from prek.toml).
# Initializes a git repo first if this project isn't inside one yet.
install-hooks:
    git rev-parse --is-inside-work-tree >/dev/null 2>&1 || git init
    uv run --frozen prek install

# Code quality ------------------------------------------------------------------------
format *paths=".":
    uv run --frozen ruff check --fix {{ paths }}
    uv run --frozen ruff format {{ paths }}

check-ruff *paths=".":
    uv run --frozen ruff check {{ paths }}

# Non-mutating — fails if `just format` would change something.
check-format *paths=".":
    uv run --frozen ruff format --check {{ paths }}

check-types *paths=".":
    uv run --frozen mypy {{ paths }}

check-complexity *paths=".":
    uv run --frozen complexipy {{ paths }}

check-spelling *paths=".":
    uv run --frozen codespell {{ paths }}

# Fast check of what you're about to commit - run this routinely.
check-secrets:
    gitleaks protect --staged --source . --verbose

# Slower full commit-history audit - run occasionally, or before making a repo public.
check-secrets-history:
    gitleaks detect --source . --verbose

# Catches drift between prek.toml's gitleaks pin and the installed binary.
check-versions-sync:
    #!/usr/bin/env -S uv run --frozen python3
    import subprocess
    import sys
    import tomllib
    from pathlib import Path

    config = tomllib.loads(Path("prek.toml").read_text())
    pin = next(
        repo["rev"].lstrip("v")
        for repo in config["repos"]
        if repo.get("repo", "").endswith("gitleaks/gitleaks")
    )

    installed = subprocess.run(
        ["gitleaks", "version"], capture_output=True, text=True, check=True,
    ).stdout.strip().lstrip("v")

    if installed != pin:
        print(f"Version drift: gitleaks installed {installed}, prek.toml pins {pin}")
        sys.exit(1)

    print("gitleaks version matches its prek.toml pin.")

# Test --------------------------------------------------------------------------------
test target="":
    uv run --frozen pytest {{ target }} --cov --cov-report=term-missing

# Convenience bundle without test
check-no-test *paths=".": (check-ruff paths) (check-format paths) (check-types paths) (check-complexity paths) (check-spelling paths) check-versions-sync
    @echo "format + types + complexity + spelling + version-sync OK"

# Convenience bundle: what you'd run before committing.
check *paths=".": (check-ruff paths) (check-format paths) (check-types paths) (check-complexity paths) (check-spelling paths) check-versions-sync (test paths)
    @echo "format + types + complexity + spelling + version-sync + tests OK"

# Project specific commands -----------------------------------------------------------

# One-off sanity check, not for routine use--------------------------------------------
check-types-verify:
    @uv run mypy -vv . 2>&1 | grep -E "Config File|'strict_equality'|'disallow_untyped_defs'"