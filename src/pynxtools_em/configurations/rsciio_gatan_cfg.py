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

from typing import Any

from pynxtools_em.utils.pint_custom_unit_registry import ureg

# be careful compared to Nion and other tech partners data for may have reversed order!
# TODO:: confirming that this implementation is correct demands examples with dissimilar sized
# rectangular, cuboidal, and hypercuboidal stacks!
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


GATAN_STATIC_VARIOUS_NX: dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/instrument/fabrication",
    "prefix_src": "ImageList/TagGroup0/ImageTags/Microscope Info/",
    "map_to_str": [("model", "Name")],
}


GATAN_DYNAMIC_VARIOUS_NX: dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/eventID[event*]/instrument",
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
            "optics/probe_current",
            ureg.ampere,
            "Probe Current (nA)",
            ureg.nanoampere,
        ),
        (
            "optics/field_of_view",
            ureg.meter,
            "Field of View (µm)",
            ureg.micrometer,
        ),
        ("optics/magnification", ureg.nx_dimensionless, "Actual Magnification"),
        ("optics/magnification", ureg.nx_dimensionless, "Indicated Magnification"),
        # (
        #     "optics/camera_length",
        #     ureg.meter,
        #     "STEM Camera Length",
        #     ureg.meter,
        # ),  # meter?
        # Cs(mm), Magnification Interpolated, Formatted Actual Mag, Formatted Indicated Mag
    ],
    "map_to_str": [
        (
            "ebeam_column/operation_mode",
            [
                "Illumination Mode",
                "Illumination Sub-mode",
                "Imaging Mode",
                "Operation Mode Type",
            ],
        ),
    ],
}

GATAN_DYNAMIC_STAGE_NX: dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/eventID[event*]/instrument/stageID[stage]",
    "prefix_src": "ImageList/TagGroup0/ImageTags/Microscope Info/Stage Position/",
    "map_to_f8": [
        ("tilt1", ureg.radian, "Stage Alpha", ureg.radian),
        ("tilt2", ureg.radian, "Stage Beta", ureg.radian),
        (
            "position",
            ureg.meter,
            ["Stage X", "Stage Y", "Stage Z"],
            ureg.meter,  # really meter?
        ),
    ],
}
