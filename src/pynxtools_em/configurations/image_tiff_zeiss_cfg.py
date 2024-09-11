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
"""Configuration of the image_tiff_zeiss parser."""

from typing import Any, Dict

from pynxtools_em.utils.pint_custom_unit_registry import ureg

ZEISS_CONCEPT_PREFIXES = ("AP_", "DP_", "SV_")


ZEISS_DYNAMIC_VARIOUS_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/event_data_em_set/EVENT_DATA_EM[event_data_em*]",
    "prefix_src": "",
    "map_to_f8": [
        ("em_lab/OPTICAL_SYSTEM_EM[optical_system_em]/magnification", "AP_MAG"),
        (
            "em_lab/OPTICAL_SYSTEM_EM[optical_system_em]/working_distance",
            ureg.meter,
            "AP_WD",
        ),
        (
            "em_lab/EBEAM_COLUMN[ebeam_column]/electron_source/voltage",
            ureg.volt,
            "AP_MANUALKV",
        ),
    ],
}

ZEISS_DYNAMIC_STAGE_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/event_data_em_set/EVENT_DATA_EM[event_data_em*]/em_lab/STAGE_LAB[stage_lab]",
    "prefix_src": "",
    "map_to_f8": [
        ("rotation", ureg.radian, "AP_STAGE_AT_R"),
        ("tilt1", ureg.radian, "AP_STAGE_AT_T"),
        ("position", ureg.meter, ["AP_STAGE_AT_X", "AP_STAGE_AT_Y", "AP_STAGE_AT_Z"]),
    ],
}

ZEISS_STATIC_VARIOUS_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/em_lab",
    "prefix_src": "",
    "use": [("FABRICATION[fabrication]/vendor", "Zeiss")],
    "map": [
        ("FABRICATION[fabrication]/model", "DP_SEM"),
        ("FABRICATION[fabrication]/identifier", "SV_SERIAL_NUMBER"),
    ],
}
