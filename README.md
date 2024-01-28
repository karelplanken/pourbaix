# Pourbaix Diagram Generator

Welcome to the Pourbaix Diagram Generator (PDG), a [Python](https://www.python.org/) (3.12.1) tool utilizing the [pymatgen](https://pymatgen.org/) (2024.1.26) ([A Robust,
Open-Source Python Library for Materials Analysis. Computational Materials
Science, 2013, 68, 314–319.](https://doi.org/10.1016/j.commatsci.2012.10.028)) package to create Pourbaix diagrams for elements of your choice. This project serves as my initial exploration into pymatgen, making it perfect for those taking their first steps with the package.

The PDG is used in the water electrolysis and electroreduction of carbondioxide projects, conducted by the Solar Fuels SF/E4F group (lector: Peter Thüne) at the Fontys University of Applied Science - Applied Natural Science Lectorate ([SIA grant for RAAK/PRO - ALMA](https://regieorgaan-sia.nl/praktijkgericht-onderzoek/uitgelichte-projecten/pionieren-als-lint-lector/) and [RELEASE](https://smartport.nl/project/release-reversible-large-scale-energy-storage/)).

## Getting Started

1. Clone the repository:

        git clone https://github.com/kplanken/pourbaix.git
        cd pourbaix

2. Install the required packages:

        pip install -r requirements.txt

3. Enter element(s) to your liking in main() in main.py

        def main() -> int:
            ...
            compounds: list[str] = [<elements go here>]
            ...
            return 0

4. Run the main script to generate Pourbaix diagrams for elements ():

        python main.py

Explore the docstrings in main.py for detailed information on available functions.

## Sample Pourbaix Diagrams

Check out the 📁 *diagrams* directory for pre-generated Pourbaix diagrams. Below is an example:

![Pourbaix diagram for Nickel](/diagrams/Ni.png)
Figure: Pourbaix diagram for Nickel

## Pourbaix Entries

The pourbaix_entries folder contains Pourbaix entries for various elements saved as JSON files. Feel free to modify or add your own entries.

## Contributing

If you have suggestions, improvements, or bug reports, please feel free to open an issue or submit a pull request. Your contributions are highly appreciated!

Happy Pourbaix diagram generating! 🧪📊