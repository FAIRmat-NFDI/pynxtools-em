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
"""Configuration of the image_tiff_fei parser."""

from typing import Any, Dict

from pynxtools_em.utils.pint_custom_unit_registry import ureg

# Tecnai TEM-specific metadata based on prototype example
# currently not mapped:
# Intensity____31.429 dimensionless
# Objective lens____92.941 dimensionless
# Diffraction lens____36.754 dimensionless
# TODO::changeme need to go elsewhere after the Autumn NIAC meeting NXem


FEI_TECNAI_STATIC_VARIOUS_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/em_lab",
    "prefix_src": "",
    "use": [("fabrication/vendor", "FEI")],
    "map": [
        ("fabrication/model", "Microscope"),
        ("ebeam_column/electron_source/emitter_type", "Gun type"),
    ],
}


FEI_TECNAI_DYNAMIC_OPTICS_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/event_data_em_set/EVENT_DATA_EM[event_data_em*]/em_lab/OPTICAL_SYSTEM_EM[optical_system_em]",
    "prefix_src": "",
    "map": [("filtermode_tmp", "Filter mode")],
    "map_to_u4": [("gunlens_tmp", "Gun lens"), ("spotsize_tmp", "Spot size")],
    "map_to_f8": [
        ("magnification", "Magnification"),
        ("camera_length", ureg.meter, "Camera length", ureg.meter),
        ("defocus", ureg.meter, "Defocus", ureg.micrometer),
        ("stemrotation_tmp", ureg.radian, "Stem rotation", ureg.degree),
        ("stemrotation_tmp", ureg.radian, "Stem rotation correction", ureg.degree),
    ],
}


FEI_TECNAI_DYNAMIC_STAGE_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/event_data_em_set/EVENT_DATA_EM[event_data_em*]/em_lab/STAGE_LAB[stage_lab]",
    "prefix_src": "",
    "map_to_f8": [
        ("tilt1", ureg.radian, "Stage A", ureg.degree),
        ("tilt2", ureg.radian, "Stage B", ureg.degree),
        (
            "position",
            ureg.meter,
            ["Stage X", "Stage Y", "Stage Z"],
            # ureg.micrometer,
        ),
    ],
}
# TODO:: L68 should be commented in again related to TODO in case_five_list


FEI_TECNAI_DYNAMIC_VARIOUS_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/event_data_em_set/EVENT_DATA_EM[event_data_em*]",
    "prefix_src": "",
    "map": [("em_lab/ebeam_column/operation_mode", "Mode")],
    "map_to_f8": [
        (
            "em_lab/ebeam_column/electron_source/voltage",
            ureg.volt,
            "High tension",
            ureg.kilovolt,
        ),
        (
            "em_lab/ebeam_column/electron_source/extraction_voltage",
            ureg.volt,
            "Extraction voltage",
            ureg.kilovolt,
        ),
        (
            "em_lab/ebeam_column/electron_source/emission_current",
            ureg.ampere,
            "Emission",
            ureg.microampere,
        ),
    ],
}
