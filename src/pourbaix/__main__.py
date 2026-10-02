"""Pourbaix Diagram Generator

This script allows the user to generate a Pourbaix diagram for a single 
or multi element system in water.

Adjust the list of elements defined in main() to your needs.

A requirements.txt file can be found in the GitHub repo.
"""
import glob
import sys
import os
from dotenv import load_dotenv
import json
import matplotlib.pyplot as plt
# Import necessary tools from pymatgen
from pymatgen.analysis.pourbaix_diagram import (  # type: ignore
    PourbaixDiagram, PourbaixPlotter, PourbaixEntry
)
from mp_api.client import MPRester  # type: ignore

# Paths to save and retrieve
JSON_ENTRIES_DIR: str = 'pourbaix_entries'
DIAGRAMS_DIR: str = 'pourbaix_diagrams'


def main() -> int:
    """Orchestrates the creation of a Pourbaix diagram for element(s)
    that are contained in the compounds list. Adjust the compounds list
    to your needs using the abbreviation for elements as listed in the 
    periodic table of the elements:
    compounds: list[str] = ['Fe']

    :return: exit status
    """
    compounds: list[str] = []

    if len(compounds) == 0:
        print('Add at least one element to the compounds list!')
        return 1

    # Save the retrieved entries if not already on disk, might
    # helpful for next time to not bother the MP API with requests
    compounds_entries_to_disk(compounds)

    # Now that all entries are on disk, load them
    all_entries = list()
    for compound in compounds:
        all_entries.extend(get_stored_pourbaix_entries(compound))

    # Create a compounds and concentration dict
    n_compounds = len(compounds)
    if n_compounds > 1:
        comp_dct = {compound: 1 / n_compounds for compound in compounds}
        conc_dct = {compound: 1e-8 for compound in compounds}
    else:
        comp_dct = {compounds[0]: 1.0}
        conc_dct = {compounds[0]: 1e-8}

    plot_pourbaix_diagram(compounds, all_entries, comp_dct, conc_dct)
    # plot_pourbaix_diagram(compounds, all_entries)

    return 0


def compounds_entries_to_disk(compounds: list[str]) -> None:
    """Given a list of elements, requests the Pourbaix entries from the 
    Materials Project API via retrieve_pourbaix_entries() if not already
    on disk. Entries that are not on disk are saved to disk by calling 
    save_pourbaix_entries().
    Returns nothing.

    :param compounds: List of elements to retrieve
    """
    for compound in compounds:
        if len(glob.glob(f'{JSON_ENTRIES_DIR}/{compound}.json')) > 0:
            continue
        else:
            entries = retrieve_pourbaix_entries(compound)
            save_pourbaix_entries(compound, entries)


def retrieve_pourbaix_entries(compound: str) -> list[PourbaixEntry]:
    """Retrieves by requesting Pourbaix entries for an element from the 
    Materials Project API.

    :param compound: Element to retrieve Pourbaix entries for
    :return: List of Pourbaix entry objects
    """
    # Materials project needs API key, obtain one yourself at 
    # https://next-gen.materialsproject.org/api
    load_dotenv(override=True)
    api_key = os.getenv('MP_API_KEY_KAREL')

    # Initialize the MP Rester
    mpr = MPRester(api_key)

    # Get Pourbaix entries for compound-O-H chemical system
    entries = mpr.get_pourbaix_entries([compound])

    return entries


def save_pourbaix_entries(compound: str, entries: list[PourbaixEntry]) -> None:
    """Saves the Pourbaix entries for an element as a JSON file in the 
    directory defined in JSON_ENTRIES_DIR.
    Returns nothing.

    :param compound: Element for which entries have to be saved
    :param entries: List of Pourbaix entry objects
    """
    # Serialize list of Pourbaix entries to save as JSON
    entries_dct = [entry.as_dict() for entry in entries]

    # Save list of Pourbaix entries to disk
    with open(
        f'{JSON_ENTRIES_DIR}/{compound}.json', 'w', encoding='utf-8'
    ) as out_file:
        out_file.write(json.dumps(entries_dct))


def get_stored_pourbaix_entries(compound: str) -> list[PourbaixEntry]:
    """Loads JSON files containing Pourbaix entries for en element.

    :param compound: Element to load Pourbaix entries for
    :return: List of Pourbaix entry objects
    """
    # Retrieve list of Pourbaix entries from JSON file on disk
    with open(
        f'{JSON_ENTRIES_DIR}/{compound}.json', 'r', encoding='utf-8'
    ) as in_file:
        entries_dct = json.loads(in_file.read())

    # Populate list with PourbaixEntry objects from dictionaries
    entries = [PourbaixEntry.from_dict(entry_dct) for entry_dct in entries_dct]

    return entries


def plot_pourbaix_diagram(
        compounds: list[str],
        entries: list[PourbaixEntry],
        comp_dict: dict[str, float],
        conc_dct: dict[str, float]
) -> None:
    """Creates, saves and shows a Pourbaix diagram for element(s).

    :param compounds: List of elements
    :param entries: List of Pourbaix entry objects for element(s)
    :param comp_dict: Relative system composition of elements
    :param conc_dct: Concentration of ions
    """
    # Filename to save png
    filename = ''.join(compound for compound in compounds)

    # Construct the PourbaixDiagram object
    pbx = PourbaixDiagram(entries, comp_dict, conc_dct, filter_solids=True)
    # pbx = PourbaixDiagram(entries, filter_solids=True)

    # Initialize a PourbaixPlotter object using a PourbaixDiagram object
    # instance
    plotter = PourbaixPlotter(pbx)

    # Value for uniform font size on plot
    fontsize = 20

    # Get the diagram as plt.Axes object
    ax = plotter.get_pourbaix_plot(
        limits=((0, 14), (-3, 3)),
        # title="Title for Diagram",
        label_domains=True,
        label_fontsize=fontsize,
        show_water_lines=True,
        show_neutral_axes=True
    )

    # Set ticks and labels fontsize for axes
    ax.set_xlabel(ax.get_xlabel(), size=fontsize)
    ax.set_ylabel(ax.get_ylabel(), size=fontsize)
    plt.xticks(fontsize=fontsize)
    plt.yticks(fontsize=fontsize)
    plt.tight_layout()

    # Save and display the plot using plt.show()
    plt.savefig(
        f'{DIAGRAMS_DIR}/{filename}.png',
        dpi='figure',
        format='png'
    )
    plt.show()


if __name__ == '__main__':
    # If script is run via in shell then main is called
    sys.exit(main())
