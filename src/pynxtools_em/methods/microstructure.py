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

from typing import Dict, Any, List
from ase.data import chemical_symbols
import numpy as np
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

    # consistency checks
    elements: set[int] = set()
    ids = set()
    for cryst in ms.crystal:
        if not hasattr(cryst, "id"):
            return template
        if cryst.id in ids:
            return template
        ids.add(cryst.id)
        if "area" not in cryst.props:
            return template
        continue
        if "composition" not in cryst.props:
            return template
        for key in cryst.props["composition"]:
            if key not in chemical_symbols[1:]:
                return template
            elements.add(key)

    n_cryst = len(ids)
    area = np.empty((n_cryst,), dtype=np.float32)
    for new_id, old_id in enumerate(sorted(ids)):
        print(old_id)
        found = False
        for cryst in ms.crystal:  # TODO::too high complexity, use LU
            if cryst.id != old_id:
                continue
            else:
                # Oxford Instruments starts counting at one! new_id for enumerate at 0
                area[new_id] = cryst.props["area"].magnitude
                found = True
                break

    trg = f"/MICROSTRUCTURE[microstructure1]/crystal"
    template[f"{trg}/number_of_crystals"] = np.uint32(n_cryst)
    template[f"{trg}/number_of_phases"] = np.uint32(1)
    # TODO::generally wrong, only for Vitesh's example!
    template[f"{trg}/crystal_identifier"] = {
        "compress": np.asarray(
            np.linspace(0, n_cryst - 1, num=n_cryst - 1, endpoint=True), dtype=np.uint32
        ),
        "strength": 1,
    }
    template[f"{trg}/phase_identifier"] = {
        "compress": np.ones((n_cryst,), dtype=np.uint32),
        "strength": 1,
    }
    template[f"{trg}/area"] = np.asarray(area, np.float32)
    template[f"{trg}/area/@units"] = f"{ureg.micrometer * ureg.micrometer}"
    del area

    """
    # cmp = []
    # cmp_sigma = []
    for key, val in area.items():  # composition["Fe"].items():
        idx.append(key)
    # print(np.mean(np.asarray(cmp)))
    """
    return template
