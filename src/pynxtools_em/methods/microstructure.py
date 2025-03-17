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

    # ms.crystal is a contigous array of crystal class instances
    is_consistent = np.zeros((len(ms.crystal),), bool)
    # falsify the assumption that a crystal has not all required values for each crystal
    # not each crystal/feature has the results for always the same elements
    # e.g. becau
    for idx, cryst in enumerate(ms.crystal):
        if "area" in cryst.props and "composition" in cryst.props:
            is_consistent[idx] = True
    print(f"{len(ms.crystal)}, {np.sum(is_consistent)}")

    # reindex
    n_cryst = np.sum(is_consistent)
    area = np.empty((n_cryst,), dtype=np.float32)
    ctable = {}
    for symbol in elements:
        ctable[symbol] = {
            "value": np.zeros((n_cryst,), dtype=np.float32),
            "sigma": np.zeros((n_cryst,), dtype=np.float32),
        }
        for qnt in ["value", "sigma"]:
            ctable[symbol][qnt][:] = np.nan
    old_ids = np.empty((n_cryst,), dtype=np.uint32)
    new_idx = 0
    for idx, state in enumerate(is_consistent):
        if state:
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

    trg = f"/ENTRY[entry{id_mgn['entry_id']}]/ROI[roi{id_mgn['roi_id']}]/imaging"
    template[f"{trg}/imaging_mode"] = f"secondary_electron"
    trg = f"/ENTRY[entry{id_mgn['entry_id']}]/ROI[roi{id_mgn['roi_id']}]/imaging/IMAGE[image{id_mgn['img_id']}]/MICROSTRUCTURE[microstructure1]/crystal"
    template[f"{trg}/number_of_crystals"] = np.uint32(n_cryst)
    template[f"{trg}/number_of_phases"] = np.uint32(1)
    # TODO::generally wrong, only for Vitesh's example!
    template[f"{trg}/crystal_identifier"] = {
        "compress": np.asarray(
            np.linspace(0, n_cryst - 1, num=n_cryst, endpoint=True), dtype=np.uint32
        ),
        "strength": 1,
    }
    template[f"{trg}/h5oina_feature_identifier"] = {
        "compress": old_ids,
        "strength": 1,
    }
    template[f"{trg}/phase_identifier"] = {
        "compress": np.ones((n_cryst,), dtype=np.uint32),
        "strength": 1,
    }
    template[f"{trg}/area"] = {"compress": np.asarray(area, np.float32), "strength": 1}
    template[f"{trg}/area/@units"] = f"{ureg.micrometer * ureg.micrometer}"

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
    template[f"{trg}/{abbrev}/cumsum"] = {"compress": cumsum, "strength": 1}
    template[f"{trg}/{abbrev}/cumsum/@long_name"] = f"Cumulated (1)"
    template[f"{trg}/{abbrev}/axis_area"] = {"compress": area_asc, "strength": 1}
    template[f"{trg}/{abbrev}/axis_area/@long_name"] = (
        f"Feature area ({ureg.micrometer * ureg.micrometer})"
    )

    # add custom, i.e. currently not NeXus-standardized composition tables
    abbrev = "CHEMICAL_COMPOSITION[chemical_composition]"
    template[f"{trg}/{abbrev}/@NX_class"] = "NXchemical_composition"
    for symbol in ctable:
        template[f"{trg}/{abbrev}/OBJECT[{symbol}]/@NX_class"] = "NXobject"
        for qnt in ["value", "sigma"]:
            template[f"{trg}/{abbrev}/OBJECT[{symbol}]/{qnt}"] = {
                "compress": ctable[symbol][qnt],
                "strength": 1,
            }
            template[f"{trg}/{abbrev}/OBJECT[{symbol}]/{qnt}/@units"] = "wt%"
    return template
