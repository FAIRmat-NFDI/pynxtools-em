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
"""Dict mapping Gatan DigitalMicrograph custom schema instances on concepts in NXem."""

from typing import Any, Dict

from pynxtools_em.utils.pint_custom_unit_registry import ureg

GATAN_WHICH_SPECTRUM = {
    "eV": ("spectrum_0d", ["axis_energy"]),
    "eV_m": ("spectrum_1d", ["axis_i", "axis_energy"]),
    "eV_m_m": ("spectrum_2d", ["axis_j", "axis_i", "axis_energy"]),
}
GATAN_WHICH_IMAGE = {
    "m": ("image_1d", ["axis_i"]),
    "1/m": ("image_1d", ["axis_i"]),
    "m_m": ("image_2d", ["axis_j", "axis_i"]),
    "1/m_1/m": ("image_2d", ["axis_j", "axis_i"]),
}
