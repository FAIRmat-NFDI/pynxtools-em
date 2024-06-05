#
# Copyright The NOMAD Authors.
#
# This file is part of NOMAD. See https://nomad-lab.eu for further info.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Pieces of information relevant for the parsing the ebsd_database use case.

We collected several EBSD datasets from the community. In these studies, names of the
phases used for indexing almost never documented the exact atomic coordinates values
of and all details to the atomic motif and crystal structures explicitly. Instead,
free-text, elements, mineral names, fragments of chemical formulas, names of
mineral groups or rocks are used. The dict maps from these NXcrystal_structure/phase_name
onto the set of NXem/ENTRY/sample/atom_types.
"""

# typical scan schemes used for EBSD
HEXAGONAL_FLAT_TOP_TILING = "hexagonal_flat_top_tiling"
SQUARE_TILING = "square_tiling"
REGULAR_TILING = "regular_tiling"

# most frequently this is the sequence of set scan positions with actual positions
# based on grid type, spacing, and tiling
FLIGHT_PLAN = "start_top_left_stack_x_left_to_right_stack_x_line_along_end_bottom_right"


FREE_TEXT_TO_CONCEPT = {
    "Actinolite": "Actinolite",
    "al": "Al",
    "Al2 O3": "Al2O3",
    "Albite_MS_DATA": "Albite",
    "Albite-Sodium Calcium Aluminum Silicate": "Albite",
    "Almandine": "Almandine",
    "Alumina (alpha)": "Al2O3",
    "Aluminium": "Aluminum",
    "Aluminum": "Aluminum",
    "Amphibole": "Amphibole",
    "Anorthite": "Anorthite",
    "Apatite": "Apatite",
    "Aragonit": "Aragonite",
    "Aragonite": "Aragonite",
    "Augite": "Augite",
    "Au hcp": "Au",
    "Austenite": "Fe",
    "Beta_Ti1023": "Ti",
    "Biotite": "Biotite",
    "Bytownite": "Bytownite",
    "BYTOWNITE An": "Bytownite",
    "Cantor FCC": "CantorAlloy",
    "calcite": "Calcite",
    "Calcite": "Calcite",
    "Chlorapatite": "Chlorapatite",
    "Chlorite": "Chlorite",
    "Chlorite Mg12(Si,Al)8": "Chlorite",
    "Chlorite Mg12(Si.Al)8": "Chlorite",
    "Chloritoid 2M": "Chloritoid",
    "Chromite": "Chromite",
    "Clinochlore 1MIa": "Clinochlore",
    "Clinochlore IIb-2": "Clinochlore",
    "Clinopyroxene": "Clinopyroxene",
    "Clinozoisite": "Clinozoisite",
    "Co FCC": "Co",
    "Co Hexagonal": "Co",
    "Cobalt": "Co",
    "Coesite": "Coesite",
    "Copper": "Cu",
    "Copper": "Cu",
    "Corderite": "Cordierite",
    "Cr2 Al C": "Cr2AlC",
    "Cu Ga Se2": "CuGaSe2",
    "Cu In S2": "CuInS2",
    "Cu In Se2": "CuInSe2",
    "Diopside": "Diopside",
    "Diopside   CaMgSi2O6": "Diopside",
    "Dolomite": "Dolomite",
    "Enstatite": "Enstatite",
    "Enstatite  Opx AV77": "Enstatite",
    "Epidote": "Epidote",
    "Epsilon_Martensite": "Fe",
    "Fe3C": "Fe3C",
    "Fe-BCC": "Fe",
    "Fe-FCC": "Fe",
    "Feldspar": "Feldspar",
    "Ferrite": "Fe",
    "Ferrite, bcc (New)": "Fe",
    "Ferrite, bcc 110 (old)": "Fe",
    "Ferrosilite, magnesian": "Ferrosilite",
    "Fluorapatite": "Fluorapatite",
    "Forsterite": "Forsterite",
    "Forsterite , 90%Mg": "Forsterite",
    "Ga N": "GaN",
    "Gallium nitride": "GaN",
    "gamma": "n/a",
    "Garnet": "Garnet",
    "Glaucophane": "Glaucophane",
    "Gold": "Au",
    "Graphite": "Graphite",
    "Grossular": "Grossular",
    "Halite": "Halite",
    "Halite": "Halite",
    "Hematite": "Hematite",
    "Hornblende": "Hornblende",
    "Hornblende  C2/m": "Hornblende",
    "Hortonolite": "Hortonolite",
    "Hydroxylapatite": "Hydroxylapatite",
    "Ice1h": "H2O",
    "Ice 1h": "H2O",
    "Ice Ih": "H2O",
    "Ilmenite": "Ilmenite",
    "Ilmenite - MgSiO3": "Ilmenite",
    "Ilmenite FeTiO3 trig": "Ilmenite",
    "Iron": "Fe",
    "Iron - Alpha": "Fe",
    "Iron (Alpha)": "Fe",
    "Iron (Gamma)": "Fe",
    "Iron bcc (old)": "Fe",
    "Iron fcc": "Fe",
    "Iron Oxide (C)": "Iron oxide",
    "Jadeite": "Jadeite",
    "K Fsp": "Orthoclase",
    "kamacite": "Kamacite",
    "Kyanite": "Kyanite",
    "Labradorite": "Labradorite",
    "Lawsonite": "Lawsonite",
    "lo-albite": "Albite",
    "Low albite": "Albite",
    "Magnesite": "Magnesite",
    "Magnesium": "Mg",
    "Magnetite": "Magnetite",
    "Magnetite low": "Magnetite",
    "MagnetiteFe3O4 Fd3m": "Magnetite",
    "martensite_Ti1023": "Ti",
    "Merrillite": "Merrillite",
    "Mg Zn2": "MgZn2",
    "Mg2 Zn11": "Mg2Zn11",
    "MgSiO3 pv (DY)": "Enstatite",
    "Microcline": "Microcline",
    "Mullite": "Mullite",
    "Muscovite": "Muscovite",
    "Muscovite - 2M1": "Muscovite",
    "Muscovite 2M1": "Muscovite",
    "N Ti": "TiN",
    "N Zr": "ZrN",
    "Ni3Al": "Ni3Al",
    "Nickel": "Ni",
    "Nickel": "Ni",
    "Ni-superalloy": "Ni",
    "Ni-superalloy": "Ni",
    "notIndexed": "notIndexed",
    "olivine": "Olivine",
    "Olivine": "Olivine",
    "Oligoclase": "Oligoclase",
    "ompaciteP2n": "Omphacite",
    "Omphacite": "Omphacite",
    "omphacite": "Omphacite",
    "OR X": "n/a",
    "Orthoclase": "Orthoclase",
    "Orthoclase inverted": "Orthoclase",
    "Orthopyroxene": "Orthopyroxene",
    "Pargasite": "Pargasite",
    "Pargasite C2/m": "Pargasite",
    "Pentlandite": "Pentlandite",
    "Periclase": "Periclase",
    "Phase_1": "n/a",
    "Pigeonite": "Pigeonite",
    "Plagioclase": "Plagioclase",
    "Prehnite": "Prehnite",
    "Pumpellyite": "Pumpellyite",
    "Pyrite": "Pyrite",
    "Pyrope": "Pyrope",
    "Quartz": "Quartz",
    "Quartz_mod": "Quartz",
    "Quartz low": "Quartz",
    "Quartz_hex": "Quartz",
    "Quartz-new": "Quartz",
    "Ringwoodite": "Ringwoodite",
    "Rutile": "Rutile",
    "Sanidine": "Sanidine",
    "Siderite": "Siderite",
    "Sigma Fe Cr Mo": "SigmaFeCrMo",
    "Silicon": "Si",
    "Silver": "Ag",
    "Spessartine, ferroan": "Spessartine",
    "Spinel": "Spinel",
    "Spinel - (Mg,Fe)2SiO4": "Spinel",
    "Stishovite": "Stishovite",
    "Sulfoapatite": "Sulfoapatite",
    "Superalloy-MC": "n/a",
    "Tantalum": "Ta",
    "taenite": "Taenite",
    "Ti-adp": "Ti",
    "Ti2448-adp": "Ti",
    "Ti2448-beta": "Ti",
    "Ti O": "TiO",
    "Ti O2": "TiO2",
    "TiC": "TiC",
    "Ti-Hex": "Ti",
    "Tin": "Sn",
    "Titanite": "Titanite",
    "Titanium": "Ti",
    "Titanium cubic": "Ti",
    "Titanium-beta": "Ti",
    "Tremolite": "Tremolite",
    "troilite": "Troilite",
    "Troilite": "Troilite",
    "Wadsleyite": "Wadsleyite",
    "Whitlockite": "Whitlockite",
    "Zeolite": "Zeolite",
    "Zinc": "Zn",
    "Zirc-alloy4": "Zirc-alloy4",
    "Zircon": "Zr",
    "Zirconia tetragonal": "Zirconia",
    "Zirconium": "Zr",
    "Zirconium - alpha": "Zr",
    "Zoisite": "Zoisite",
    "Zr02 monoclinic": "ZrO",
    "ZrFeCr2_hex": "ZrFeCr2",
    "ZrH-_fcc": "ZrH",
    "Zr_hex": "Zr",
    "": "n/a",
}


CONCEPT_TO_ATOM_TYPES = {
    "Actinolite": "Ca;Mg;Fe;Si;O;H",
    "Al2O3": "Al;O",
    "Albite": "Na;Al;Si;O",
    "Almandine": "Fe;Si;Al;O",
    "Aluminum": "Al",
    "Amphibole": "Si;O;H",
    "Anorthite": "Ca;Al;Si;O",
    "Apatite": "P;O",
    "Aragonite": "Ca;C;O",
    "Augite": "Ca;Mg;Fe;Si;O",
    "Biotite": "K;Si;O",
    "Bytownite": "Ca;Na;Si;Al;O",
    "Calcite": "Ca;C;O",
    "CantorAlloy": "Cr;Mn;Fe;Co;Ni",
    "Chlorite": "Fe;Mg;Al;Si;Al;O;H",
    "Chlorapatite": "Ca;P;O;Cl",
    "Chloritoid": "Fe;Al;O;Si;H",
    "Chromite": "Fe;Cr;O",
    "Clinochlore": "Mg;Al;Si;O;H",
    "Clinopyroxene": "Si;O",
    "Clinozoisite": "Ca;Al;Si;O;H",
    "Coesite": "Si;O",
    "Cordierite": "Mg;Al;Si;O",
    "Cr2AlC": "Cr;Al;C",
    "CuGaSe2": "Cu;Ga;Se",
    "CuInS2": "Cu;In;S",
    "CuInSe2": "Cu;In;Se",
    "Diopside": "Ca;Mg;Si;O",
    "Dolomite": "Ca;Mg;C;O",
    "Enstatite": "Mg;Si;O",
    "Epidote": "Ca;Al;Fe;Si;O;H",
    "Fe3C": "Fe;C",
    "Feldspar": "Si;O",
    "Ferrosilite": "Fe;Si;O",
    "Forsterite": "Mg;Si;O",
    "GaN": "Ga;N",
    "GaN": "Ga;N",
    "Garnet": "Si;O",
    "Glaucophane": "Na;Mg;Al;Si;O;H",
    "Graphite": "C",
    "H2O": "H;O",
    "Halite": "Na;Cl",
    "Halite": "Na;Cl",
    "Hematite": "Fe;O",
    "Hornblende": "Al;Si;O",
    "Hortonolite": "Fe;Si;O",
    "Hydroxylapatite": "Ca;P;O;H",
    "Ilmenite": "Fe;Ti;O",
    "Iron oxide": "Fe;O",
    "Jadeite": "Na;Al;Si;O",
    "Kamacite": "Fe;Ni",
    "Kyanite": "Al;O;Si",
    "Labradorite": "Ca;Na;Si;Al;O",
    "Lawsonite": "Ca;Al;Si;O;H",
    "Magnesite": "Mg;C;O",
    "Magnetite": "Fe;O",
    "Merrillite": "Ca;Na;Mg;P;O",
    "Microcline": "K;Al;Si;O",
    "Mg2Zn11": "Mg;Zn",
    "MgZn2": "Mg;Zn",
    "Mullite": "Al;Si;O",
    "Muscovite": "K;Al;Si;O;H",
    "Ni3Al": "Ni;Al",
    "notIndexed": "",
    "n/a": "",
    "Oligoclase": "Na;Ca;Si;Al;O",
    "Olivine": "Mg;Fe;Si;O",
    "Omphacite": "Ca;Na;Mg;Fe;Al;Si;O",
    "Orthoclase": "K;Al;Si;O",
    "Orthopyroxene": "Mg;Si;O",
    "Pargasite": "Na;Ca;Mg;Al;Si;O;H",
    "Pentlandite": "Ni;Fe;S",
    "Periclase": "Mg;O",
    "Pigeonite": "Mg;Fe;Ca;Si;O",
    "Plagioclase": "Al;Si;O",
    "Prehnite": "Ca;Al;Si;O;H",
    "Pumpellyite": "Ca;Si;O;H",
    "Pyrite": "Fe;S",
    "Pyrope": "Mg;Al;Si;O",
    "Quartz": "Si;O",
    "Ringwoodite": "Si;Mg;O",
    "Rutile": "Ti;O",
    "Sanidine": "K;Al;Si;O",
    "Siderite": "Fe;C;O",
    "SigmaFeCrMo": "Fe;Cr;Mo",
    "Spessartine": "Mn;Al;Si;O",
    "Spinel": "Mg;Al;O",
    "Stishovite": "Si;O",
    "Sulfoapatite": "S;P;O",
    "Taenite": "Ni;Fe",
    "TiC": "Ti;C",
    "TiN": "Ti;N",
    "TiO": "Ti;O",
    "TiO2": "Ti;O",
    "Titanite": "Ca;Ti;Si;O",
    "Tremolite": "Ca;Mg;Fe;Si;O;H",
    "Troilite": "Fe;S",
    "Wadsleyite": "Mg;Si;O",
    "Whitlockite": "Ca;Mg;P;O;H",
    "Zeolite": "",
    "Zirc-alloy4": "Zr;Sn;Fe;Cr",
    "Zircon": "Zr;Si;O",
    "Zirconia": "Zr;O",
    "Zoisite": "Ca;Al;Si;O;H",
    "ZrN": "Zr;N",
    "ZrO": "Zr;O",
    "ZrFeCr2": "Zr;Fe;Cr",
    "ZrH": "Zr;H",
}


ASSUME_PHASE_NAME_TO_SPACE_GROUP = {
    "Silver": 225,
    "Copper": 225,
    "Ni (Nickel)": 225,
    "Face Centered Cubic": 225,
    "Ge (Germanium)": 225,
}  # Ge (Germanium), really?
