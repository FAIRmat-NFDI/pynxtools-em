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
"""Standardized functionalities and visualization used when working with microstructures."""

from typing import Any, Dict, List, Set

import numpy as np
from ase.data import chemical_symbols

from pynxtools_em.utils.pint_custom_unit_registry import ureg


class Crystal:
    def __init__(self):
        self.id: np.uint32 = np.iinfo(np.uint32).max
        # maximum value of the range means not assigned, valid ids start at 0
        self.props: Dict[str, Any] = {}


class Microstructure:
    """Cache for storing a single indexed EBSD point cloud with mark data."""

    def __init__(self):
        self.dimensionality: int = 0
        self.crystal: List[Crystal] = []


def microstructure_to_template(
    ms: Microstructure, id_mgn: Dict[str, int], template: dict
) -> dict:
    """Write cached microstructure into template according to NXmicrostructure."""
    # TODO::generalize

    # inspect for each crystal if all required pieces of information are available
    # crystals typically have been collected with IDs that must not be assumed to be
    # contiguous or starting with some starting index, hence we relabel all ids.
    elements: Set[str] = set()
    ids: Set[np.uint32] = set()
    disjoint = True
    for cryst in ms.crystal:
        if "area" in cryst.props and "composition" in cryst.props:
            for symbol in cryst.props["composition"]:
                if symbol in chemical_symbols[1:]:
                    if symbol not in elements:
                        elements.add(symbol)
            if cryst.id not in ids:
                ids.add(cryst.id)
            else:
                disjoint = False
    if not disjoint:
        print(f"At least one crystal identifier is not disjoint !")
        return template
    print(elements)

    # ms.crystal is a contigous array of crystal class instances, ut their ids might not be contiguous
    # in Vitesh's example the "crystals" are of a second-phase in order to characterize
    # these we need to assure that we have values for all relevant descriptors for all
    # the crystal we report, as the analysis from AZTec can yield results that one
    # might not wish to include, the following logic handles such cases
    is_consistent = np.zeros((len(ms.crystal),), bool)
    # check for crystals we do have all required values
    for idx, cryst in enumerate(ms.crystal):
        if "area" in cryst.props and "composition" in cryst.props:
            is_consistent[idx] = True
    print(
        f"{len(ms.crystal)} crystals in total, {np.sum(is_consistent)} of these values for all desired descriptors."
    )

    # reindex
    n_cryst = np.sum(is_consistent)
    area = np.empty((n_cryst,), dtype=np.float32)
    ctable = {}
    for symbol in elements:
        ctable[symbol] = {
            "value": np.full((n_cryst,), np.nan, dtype=np.float32),
            "sigma": np.full((n_cryst,), np.nan, dtype=np.float32),
        }
    old_ids = np.empty((n_cryst,), dtype=np.uint32)
    new_idx = 0
    for idx, state in enumerate(is_consistent):
        if state:  # for all crystal that we have all information relabel the crystal id
            old_ids[new_idx] = ms.crystal[idx].id
            area[new_idx] = ms.crystal[idx].props["area"].magnitude
            for symbol in ms.crystal[idx].props["composition"]:
                if symbol in ctable:
                    for qnt in ["value", "sigma"]:
                        ctable[symbol][qnt][new_idx] = ms.crystal[idx].props[
                            "composition"
                        ][symbol][qnt]
            new_idx += 1
    del is_consistent

    trg = f"/ENTRY[entry{id_mgn['entry_id']}]/roiID[roi{id_mgn['roi_id']}]/img/imageID[image{id_mgn['img_id']}]"
    template[f"{trg}/imaging_mode"] = f"secondary_electron"

    trg += f"/microstructureID[microstructure1]/crystals/chemical_composition"
    inform_about_atom_types = set()
    for symbol in ctable:
        if (
            np.sum(np.isnan(ctable[symbol]["value"])) > 0
            or np.sum(np.isnan(ctable[symbol]["sigma"])) > 0
        ):
            print(
                f"Element {symbol} not reported because some descriptor values NaN for some crystals!"
            )
            continue
        for qnt in ["value", "sigma"]:
            template[f"{trg}/ELEMENT[{symbol}]/{qnt}"] = {
                "compress": ctable[symbol][qnt],
                "strength": 1,
            }
            template[f"{trg}/ELEMENT[{symbol}]/{qnt}/@units"] = "wt%"
            inform_about_atom_types.add(symbol)
    if len(inform_about_atom_types) > 0:
        template[f"{trg}/normalization"] = "weight_percent"

    abbrev = f"/ENTRY[entry{id_mgn['entry_id']}]/sampleID[sample]/atom_types"
    if abbrev not in template:
        template[abbrev] = ", ".join(list(inform_about_atom_types))

    trg = f"/ENTRY[entry{id_mgn['entry_id']}]/roiID[roi{id_mgn['roi_id']}]/img/imageID[image{id_mgn['img_id']}]/microstructureID[microstructure1]/crystals"
    template[f"{trg}/number_of_crystals"] = np.uint32(n_cryst)
    template[f"{trg}/number_of_phases"] = np.uint32(1)
    # TODO::generally wrong, only for Vitesh's example!
    template[f"{trg}/indices_crystal"] = {
        "compress": np.asarray(
            np.linspace(0, n_cryst - 1, num=n_cryst, endpoint=True), dtype=np.uint32
        ),
        "strength": 1,
    }
    template[f"{trg}/indices_crystal_h5oina_feature"] = {
        "compress": old_ids,
        "strength": 1,
    }
    template[f"{trg}/indices_phase"] = {
        # only for Vitesh's example where it is assumed all belong to the same phase
        "compress": np.ones((n_cryst,), dtype=np.uint32),
        "strength": 1,
    }
    template[f"{trg}/area"] = {"compress": np.asarray(area, np.float32), "strength": 1}
    template[f"{trg}/area/@units"] = f"{ureg.micrometer**2}"

    # add a default cumsum plot for the area
    area_asc = np.sort(area, kind="stable")
    cumsum = np.asarray(
        np.linspace(1.0 / n_cryst, n_cryst / n_cryst, num=n_cryst, endpoint=True),
        np.float64,
    )
    abbrev = f"DATA[area_distribution]"
    template[f"{trg}/{abbrev}/@NX_class"] = "NXdata"
    # manual addition needed because currently not part of the NeXus schema
    template[f"{trg}/{abbrev}/@signal"] = "cumsum"
    template[f"{trg}/{abbrev}/@axes"] = ["axis_area"]
    template[f"{trg}/{abbrev}/@AXISNAME_indices[axis_area]"] = np.uint32(0)
    template[f"{trg}/{abbrev}/title"] = f"Feature area CDF"
    # only reporting those crystals for which we have values for all their descriptors!
    template[f"{trg}/{abbrev}/cumsum"] = {"compress": cumsum, "strength": 1}
    template[f"{trg}/{abbrev}/cumsum/@long_name"] = f"Cumulated (1)"
    template[f"{trg}/{abbrev}/axis_area"] = {"compress": area_asc, "strength": 1}
    template[f"{trg}/{abbrev}/axis_area/@long_name"] = (
        f"Feature area ({ureg.micrometer**2})"
    )

    return template
