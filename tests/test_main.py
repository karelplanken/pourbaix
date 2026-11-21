"""Tests for the Pourbaix entry cache in pourbaix.__main__."""

import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, NotRequired, TypedDict, cast
from unittest.mock import Mock

from pre_commit_hooks.pretty_format_json import main as pretty_format_json

from pourbaix.__main__ import (
    compounds_entries_to_disk,
    get_stored_pourbaix_entries,
    save_pourbaix_entries,
)

if TYPE_CHECKING:
    import pytest

PROJECT_ROOT = Path(__file__).parents[1]

ENTRIES_DIR = PROJECT_ROOT / 'pourbaix-entries'


class HookConfig(TypedDict):
    """A hook config in prek.toml."""

    id: str
    args: NotRequired[list[str]]


class RepoConfig(TypedDict):
    """A repo config in prek.toml."""

    repo: str
    hooks: NotRequired[list[HookConfig]]


class PrekConfig(TypedDict):
    """The config in prek.toml."""

    repos: list[RepoConfig]


def _hook_args(hook_id: str) -> list[str]:
    """Returns a hook's args from prek.toml, without --autofix.

    Args:
        hook_id: The hook id to look for in prek.toml

    Returns:
        The hook's args, without --autofix

    Raises:
        LookupError: If the hook id is not found in prek.toml
    """
    text = (PROJECT_ROOT / 'prek.toml').read_text(encoding='utf-8')
    config = cast('PrekConfig', tomllib.loads(text))
    for repo in config['repos']:
        for hook in repo.get('hooks', []):
            if hook['id'] == hook_id:
                return [arg for arg in hook.get('args', []) if arg != '--autofix']
    msg = f'Hook {hook_id!r} not found in prek.toml'
    raise LookupError(msg)


def test_saved_entries_pass_pretty_format_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Entries saved to disk pass the pretty-format-json hook unchanged."""
    monkeypatch.setattr('pourbaix.__main__.JSON_ENTRIES_DIR', ENTRIES_DIR)
    entries = get_stored_pourbaix_entries('Fe')

    monkeypatch.setattr('pourbaix.__main__.JSON_ENTRIES_DIR', tmp_path)
    save_pourbaix_entries('Fe', entries)

    saved = tmp_path / 'Fe.json'
    assert pretty_format_json([*_hook_args('pretty-format-json'), str(saved)]) == 0


def test_saved_entries_load_back_unchanged(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Entries saved to disk load back with the same names and energies."""
    monkeypatch.setattr('pourbaix.__main__.JSON_ENTRIES_DIR', ENTRIES_DIR)
    original = get_stored_pourbaix_entries('Fe')

    monkeypatch.setattr('pourbaix.__main__.JSON_ENTRIES_DIR', tmp_path)
    save_pourbaix_entries('Fe', original)
    loaded = get_stored_pourbaix_entries('Fe')

    assert len(loaded) == len(original)
    assert [e.name for e in loaded] == [e.name for e in original]
    assert [e.energy for e in loaded] == [e.energy for e in original]


def test_cached_compound_is_not_fetched(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A compound whose JSON file already exists is not fetched again."""
    cached = tmp_path / 'Fe.json'
    cached.touch()
    monkeypatch.setattr('pourbaix.__main__.JSON_ENTRIES_DIR', tmp_path)

    # replacement for retrieve_pourbaix_entries, the mock should not be called
    retrieve = Mock()
    monkeypatch.setattr('pourbaix.__main__.retrieve_pourbaix_entries', retrieve)
    compounds_entries_to_disk(['Fe'])

    retrieve.assert_not_called()
    assert cached.stat().st_size == 0
