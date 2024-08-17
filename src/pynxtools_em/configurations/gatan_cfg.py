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

# be careful compared to Nion and other tech partners data for may have reversed order!
# TODO:: confirming that this implementation is correct demands examples with dissimilar sized
# rectangular, cubodial, and hypercuboidal stacks!
GATAN_WHICH_SPECTRUM = {
    "eV": ("spectrum_0d", ["axis_energy"]),
    "eV_m": ("spectrum_1d", ["axis_energy", "axis_i"]),
    "eV_m_m": ("spectrum_2d", ["axis_energy", "axis_i", "axis_j"]),
}
GATAN_WHICH_IMAGE = {
    "m": ("image_1d", ["axis_i"]),
    "1/m": ("image_1d", ["axis_i"]),
    "m_m": ("image_2d", ["axis_i", "axis_j"]),
    "1/m_1/m": ("image_2d", ["axis_i", "axis_j"]),
}


GATAN_DYNAMIC_VARIOUS_TO_NX_EM: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/event_data_em_set/EVENT_DATA_EM[event_data_em*]/em_lab",
    "prefix_src": "ImageList/TagGroup0/ImageTags/Microscope Info/",
    "map_to_f8": [
        (
            "ebeam_column/electron_source/voltage",
            ureg.volt,
            "Voltage",
            ureg.volt,
        ),  # volt?
        (
            "ebeam_column/electron_source/emission_current",
            ureg.ampere,
            "Emission Current (µA)",
            ureg.microampere,
        ),
        # Formatted Voltage, HT Extrapolated
        (
            "ebeam_column/BEAM[beam]/diameter",
            ureg.meter,
            "Probe Size (nm)",
            ureg.nanometer,
        ),  # diameter? radius ?
        (
            "OPTICAL_SETUP_EM[optical_setup]/probe_current",
            ureg.ampere,
            "Probe Current (nA)",
            ureg.nanoampere,
        ),
        (
            "OPTICAL_SETUP_EM[optical_setup]/field_of_view",
            ureg.meter,
            "Field of View (µm)",
            ureg.micrometer,
        ),
        ("OPTICAL_SETUP_EM[optical_setup]/magnification", "Actual Magnification"),
        (
            "OPTICAL_SETUP_EM[optical_setup]/camera_length",
            ureg.meter,
            "STEM Camera Length",
            ureg.meter,
        ),
        # Cs(mm), Indicated Magnification, Magnification Interpolated, Formatted Actual Mag, Formatted Indicated Mag
    ],
    "map": [
        ("OPTICAL_SETUP_EM[optical_setup]/illumination_mode", "Illumination Mode"),
        (
            "OPTICAL_SETUP_EM[optical_setup]/illumination_submode",
            "Illumination Sub-mode",
        ),
        ("OPTICAL_SETUP_EM[optical_setup]/imaging_mode", "Imaging Mode"),
        ("OPTICAL_SETUP_EM[optical_setup]/name", "Name"),
        ("OPTICAL_SETUP_EM[optical_setup]/operation_mode", "Operation Mode"),
        ("OPTICAL_SETUP_EM[optical_setup]/operation_mode_type", "Operation Mode Type"),
    ],
}

GATAN_DYNAMIC_STAGE_TO_NX_EM: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/event_data_em_set/EVENT_DATA_EM[event_data_em*]/em_lab/STAGE_LAB[stage]",
    "prefix_src": "ImageList/TagGroup0/ImageTags/Microscope Info/Stage Position/",
    "map_to_f8": [
        ("tilt1", ureg.radian, "Stage Alpha", ureg.radian),
        ("tilt2", ureg.radian, "Stage Beta", ureg.radian),
        (
            "position",
            ureg.meter,
            ["Stage X", "Stage Y", "Stage Z"],
            ureg.meter,
        ),
    ],
}
