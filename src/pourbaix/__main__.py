"""Pourbaix Diagram Generator.

This script allows the user to generate a Pourbaix diagram for a single
or multi element system in water.

Adjust the list of elements defined in main() to your needs.

Entry point for Pourbaix Diagram Generator.

Toolkit-agnostic stub — see README.md for how to wire up a CLI (Typer
recommended) or a GUI (tkinter, pygame, etc.) here. Whatever you pick,
`[project.scripts]` in pyproject.toml already points at `main` below.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
from dotenv import load_dotenv
from mp_api.client import MPRester

# Import necessary tools from pymatgen
from pymatgen.analysis.pourbaix_diagram import (
    PourbaixDiagram,
    PourbaixEntry,
    PourbaixPlotter,
)

# Paths to save and retrieve
JSON_ENTRIES_DIR = Path('pourbaix-entries')
DIAGRAMS_DIR = Path('pourbaix-diagrams')


def main() -> int:
    """Main function to generate a Pourbaix diagram.

    This function orchestrates the creation of a Pourbaix diagram for element(s)
    that are contained in the compounds list. Adjust the compounds list
    to your needs using the abbreviation for elements as listed in the
    periodic table of the elements.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    compounds: list[str] = ['Fe']

    if len(compounds) == 0:
        print(  # ruff: ignore[print]
            'Add at least one element to the compounds list!', file=sys.stderr
        )
        return 1

    # Save the retrieved entries if not already on disk, might
    # helpful for next time to not bother the MP API with requests
    compounds_entries_to_disk(compounds)

    # Now that all entries are on disk, load them
    all_entries: list[PourbaixEntry] = []
    for compound in compounds:
        all_entries.extend(get_stored_pourbaix_entries(compound))

    # Create a compounds and concentration dict
    comp_dct = dict.fromkeys(compounds, 1 / len(compounds))
    conc_dct = dict.fromkeys(compounds, 1e-8)

    plot_pourbaix_diagram(compounds, all_entries, comp_dct, conc_dct)

    return 0


def _entries_path(compound: str) -> Path:
    """Returns the path of the cached entries file for a compound.

    Args:
        compound: Abbreviated name of the compound.

    Returns:
        Path where the cached entries file lives.
    """
    return JSON_ENTRIES_DIR / f'{compound}.json'


def compounds_entries_to_disk(compounds: list[str]) -> None:
    """Retrieves Pourbaix entries for the given compounds and saves them to disk.

    If the entries are not already on disk, they are retrieved from the Materials
    Project API and saved to disk.

    Args:
        compounds: Elements for which to retrieve Pourbaix entries
    """
    for compound in compounds:
        if _entries_path(compound).exists():
            continue
        entries = retrieve_pourbaix_entries(compound)
        save_pourbaix_entries(compound, entries)


def retrieve_pourbaix_entries(compound: str) -> list[PourbaixEntry]:
    """Retrieves Pourbaix entries for a given compound from the Materials Project API.

    Args:
        compound: Element for which to retrieve Pourbaix entries

    Returns:
        List of Pourbaix entry objects
    """
    # Materials project needs API key, obtain one yourself at
    # https://next-gen.materialsproject.org/api
    load_dotenv(override=True)
    api_key = os.getenv('MP_API_KEY')

    # Initialize the MP Rester
    mpr = MPRester(api_key)

    # Get Pourbaix entries for compound-O-H chemical system
    return mpr.get_pourbaix_entries([compound])


def save_pourbaix_entries(compound: str, entries: list[PourbaixEntry]) -> None:
    """Saves Pourbaix entries for a given compound to disk as JSON.

    Args:
        compound: Element for which to save Pourbaix entries
        entries: List of Pourbaix entry objects to save
    """
    # Serialize list of Pourbaix entries to save as JSON
    entries_dct: list[dict[str, Any]] = [entry.as_dict() for entry in entries]

    # Save list of Pourbaix entries to disk
    _entries_path(compound).write_text(
        json.dumps(entries_dct, indent=4, sort_keys=True, ensure_ascii=False) + '\n',
        encoding='utf-8',
    )


def get_stored_pourbaix_entries(compound: str) -> list[PourbaixEntry]:
    """Retrieves stored Pourbaix entries for a given compound from disk.

    Args:
        compound: Element for which to retrieve stored Pourbaix entries

    Returns:
        List of Pourbaix entry objects
    """
    # Retrieve list of Pourbaix entries from JSON file on disk
    entries_dct: list[dict[str, Any]] = json.loads(
        _entries_path(compound).read_text(encoding='utf-8')
    )

    # Populate list with PourbaixEntry objects from dictionaries
    return [PourbaixEntry.from_dict(entry_dct) for entry_dct in entries_dct]


def plot_pourbaix_diagram(
    compounds: list[str],
    entries: list[PourbaixEntry],
    comp_dict: dict[str, float],
    conc_dct: dict[str, float],
) -> None:
    """Plots a Pourbaix diagram for the given compounds and entries.

    comp_dict and conc_dct are passed on to pymatgen's PourbaixDiagram,
    where both are optional: without them, pymatgen uses equal parts of
    each element and an ion concentration of 1e-6 M.

    The same holds for optional arguments as plot title, limits (xlim, ylim), and
    others. See pymatgen.analysis.pourbaix_diagram.PourbaixPlotter.get_pourbaix_plot().

    Args:
        compounds: List of elements for which to plot the Pourbaix diagram
        entries: List of Pourbaix entry objects to use for plotting
        comp_dict: Relative system composition of elements
        conc_dct: Concentration of ions
    """
    # Filename to save png
    filename = ''.join(compound for compound in compounds)

    # Construct the PourbaixDiagram object
    pbx = PourbaixDiagram(entries, comp_dict, conc_dct, filter_solids=True)

    # Initialize a PourbaixPlotter object using a PourbaixDiagram object
    plotter = PourbaixPlotter(pbx)

    # Value for uniform font size on plot
    fontsize = 20

    # Get the diagram as plt.Axes object
    ax = plotter.get_pourbaix_plot(
        limits=((0, 14), (-3, 3)),
        label_domains=True,
        label_fontsize=fontsize,
        show_water_lines=True,
        show_neutral_axes=True,
    )

    # Set ticks and labels fontsize for axes
    ax.set_xlabel(ax.get_xlabel(), size=fontsize)
    ax.set_ylabel(ax.get_ylabel(), size=fontsize)
    plt.xticks(fontsize=fontsize)
    plt.yticks(fontsize=fontsize)
    plt.tight_layout()

    # Save and display the plot using plt.show()
    plt.savefig(DIAGRAMS_DIR / f'{filename}.png', dpi='figure', format='png')
    plt.show()


if __name__ == '__main__':
    # If script is run via in shell then main is called
    sys.exit(main())
