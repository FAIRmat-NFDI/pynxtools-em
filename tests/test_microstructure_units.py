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
"""Units written by microstructure_to_template (Bug B32 in
https://github.com/FAIRmat-NFDI/pynxtools-plugin-audit/blob/main/pynxtools-unification/FINDINGS.md)."""

import numpy as np
from pynxtools.units import ureg

from pynxtools_em.methods.microstructure import (
    Crystal,
    Microstructure,
    microstructure_to_template,
)


def _one_crystal_microstructure():
    crystal = Crystal()
    crystal.id = np.uint32(7)
    crystal.props["area"] = 2.5 * ureg.micrometer**2
    crystal.props["composition"] = {"Fe": {"value": 70.0, "sigma": 0.5}}
    ms = Microstructure()
    ms.crystal = [crystal]
    return ms


def test_microstructure_units_are_valid():
    """Every @units written for a microstructure must be a unit pint can parse."""
    template = microstructure_to_template(
        _one_crystal_microstructure(), {"entry_id": 1, "roi_id": 1, "img_id": 1}, {}
    )
    units = {key: value for key, value in template.items() if key.endswith("@units")}
    assert units  # the composition and area units are written

    invalid = []
    for key, value in units.items():
        try:
            ureg(value)
        except Exception:
            invalid.append(f"{key}: {value!r}")
    assert invalid == []


def test_composition_is_in_percent():
    """The weight-percent composition is written as percent."""
    template = microstructure_to_template(
        _one_crystal_microstructure(), {"entry_id": 1, "roi_id": 1, "img_id": 1}, {}
    )
    composition = (
        "/ENTRY[entry1]/roiID[roi1]/img/imageID[image1]/microstructureID"
        "[microstructure1]/crystals/chemical_composition"
    )
    assert template[f"{composition}/ELEMENT[Fe]/value/@units"] == "percent"
    assert template[f"{composition}/ELEMENT[Fe]/sigma/@units"] == "percent"
    assert template[f"{composition}/normalization"] == "weight_percent"
