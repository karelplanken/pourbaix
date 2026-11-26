"""Tests for the Pourbaix entry cache in pourbaix.__main__."""

import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, NotRequired, TypedDict, cast
from unittest.mock import Mock, create_autospec, sentinel

import pytest
from emmet.core.types.pymatgen_types.computed_entries_adapter import EntryID
from mp_api.client import MPRester
from pre_commit_hooks.pretty_format_json import main as pretty_format_json

from pourbaix.__main__ import (
    compounds_entries_to_disk,
    get_stored_pourbaix_entries,
    main,
    plot_pourbaix_diagram,
    retrieve_pourbaix_entries,
    save_pourbaix_entries,
)

if TYPE_CHECKING:
    from pymatgen.analysis.pourbaix_diagram import PourbaixEntry

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


@pytest.fixture
def fe_entries() -> list[PourbaixEntry]:
    """The Fe entries from the repo's cache, loaded fresh for each test.

    Returns:
        The Pourbaix entries stored in pourbaix-entries/Fe.json.
    """
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr('pourbaix.__main__.JSON_ENTRIES_DIR', ENTRIES_DIR)
        return get_stored_pourbaix_entries('Fe')


def _hook_args(hook_id: str) -> list[str]:
    """Returns a hook's args from prek.toml, without --autofix.

    Args:
        hook_id: The hook id to look for in prek.toml.

    Returns:
        The hook's args, without --autofix.

    Raises:
        LookupError: If the hook id is not found in prek.toml.
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
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fe_entries: list[PourbaixEntry]
) -> None:
    """Entries saved to disk pass the pretty-format-json hook unchanged."""
    monkeypatch.setattr('pourbaix.__main__.JSON_ENTRIES_DIR', tmp_path)
    save_pourbaix_entries('Fe', fe_entries)

    saved = tmp_path / 'Fe.json'
    assert pretty_format_json([*_hook_args('pretty-format-json'), str(saved)]) == 0


def test_saved_entries_load_back_unchanged(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fe_entries: list[PourbaixEntry]
) -> None:
    """Entries saved to disk load back with the same names and energies."""
    monkeypatch.setattr('pourbaix.__main__.JSON_ENTRIES_DIR', tmp_path)
    save_pourbaix_entries('Fe', fe_entries)
    loaded = get_stored_pourbaix_entries('Fe')

    assert len(loaded) == len(fe_entries)
    assert [e.name for e in loaded] == [e.name for e in fe_entries]
    assert [e.energy for e in loaded] == [e.energy for e in fe_entries]


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


def test_uncached_compound_is_fetched_and_saved(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A compound whose JSON file does not exist is fetched and saved."""
    monkeypatch.setattr('pourbaix.__main__.JSON_ENTRIES_DIR', tmp_path)

    retrieve = Mock(return_value=sentinel.entries)
    monkeypatch.setattr('pourbaix.__main__.retrieve_pourbaix_entries', retrieve)

    save = Mock()
    monkeypatch.setattr('pourbaix.__main__.save_pourbaix_entries', save)

    compounds_entries_to_disk(['Fe'])

    retrieve.assert_called_once_with('Fe')
    save.assert_called_once_with('Fe', sentinel.entries)


def test_entries_are_fetched_with_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Entries are fetched with the MP_API_KEY key, for the compound's system."""
    monkeypatch.setattr('pourbaix.__main__.load_dotenv', Mock())
    monkeypatch.setenv('MP_API_KEY', 'test-key')
    mp_rester = create_autospec(MPRester)
    mp_rester.return_value.get_pourbaix_entries.return_value = sentinel.entries
    monkeypatch.setattr('pourbaix.__main__.MPRester', mp_rester)

    entries = retrieve_pourbaix_entries('Fe')

    mp_rester.assert_called_once_with('test-key')
    mp_rester.return_value.get_pourbaix_entries.assert_called_once_with(['Fe'])
    assert entries is sentinel.entries


def test_diagram_is_saved_as_png_and_shown(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fe_entries: list[PourbaixEntry]
) -> None:
    """plot_pourbaix_diagram saves a PNG and calls plt.show() once."""
    monkeypatch.setattr('pourbaix.__main__.DIAGRAMS_DIR', tmp_path)

    show = Mock()
    monkeypatch.setattr('pourbaix.__main__.plt.show', show)

    plot_pourbaix_diagram(['Fe'], fe_entries, {'Fe': 1.0}, {'Fe': 1e-8})

    assert (tmp_path / 'Fe.png').read_bytes().startswith(b'\x89PNG')
    show.assert_called_once()


def test_main_plots_iron_diagram(monkeypatch: pytest.MonkeyPatch) -> None:
    """The main function connects the steps of fetching entries and plotting."""
    to_disk = Mock()
    monkeypatch.setattr('pourbaix.__main__.compounds_entries_to_disk', to_disk)

    get_stored = Mock(return_value=[sentinel.fe_entry])
    monkeypatch.setattr('pourbaix.__main__.get_stored_pourbaix_entries', get_stored)

    plot = Mock()
    monkeypatch.setattr('pourbaix.__main__.plot_pourbaix_diagram', plot)

    exit_code = main()

    assert exit_code == 0
    to_disk.assert_called_once_with(['Fe'])
    get_stored.assert_called_once_with('Fe')
    plot.assert_called_once_with(['Fe'], [sentinel.fe_entry], {'Fe': 1.0}, {'Fe': 1e-8})


def test_entry_ids_are_saved_as_strings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fe_entries: list[PourbaixEntry]
) -> None:
    """Emmet EntryID objects from fresh API data are cached as plain strings."""
    solid = next(e for e in fe_entries if e.phase_type == 'Solid')
    solid.entry.entry_id = EntryID.model_validate('mp-13-GGA')  # type: ignore[assignment]
    monkeypatch.setattr('pourbaix.__main__.JSON_ENTRIES_DIR', tmp_path)

    save_pourbaix_entries('Fe', fe_entries)
    loaded = get_stored_pourbaix_entries('Fe')

    loaded_solid = next(e for e in loaded if e.phase_type == 'Solid')
    assert loaded_solid.entry.entry_id == 'mp-13-GGA'
