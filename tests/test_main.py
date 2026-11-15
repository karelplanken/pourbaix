"""Tests for the Pourbaix entry cache in pourbaix.__main__."""

from pathlib import Path
from typing import TYPE_CHECKING

from pourbaix.__main__ import get_stored_pourbaix_entries, save_pourbaix_entries

if TYPE_CHECKING:
    import pytest

ENTRIES_DIR = Path(__file__).parents[1] / 'pourbaix-entries'


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
