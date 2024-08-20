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
"""Configuration of the image_tiff_hitachi parser."""

from pynxtools_em.utils.pint_custom_unit_registry import ureg

HITACHI_DYNAMIC_VARIOUS_TO_NX_EM = {
    "prefix_trg": "/ENTRY[entry*]/measurement/event_data_em_set/EVENT_DATA_EM[event_data_em*]",
    "prefix_src": "",
    "map_to_f8": [
        ("em_lab/OPTICAL_SYSTEM_EM[optical_system_em]/magnification", "Magnification"),
        (
            "em_lab/OPTICAL_SYSTEM_EM[optical_system_em]/working_distance",
            ureg.meter,
            "WorkingDistance",
        ),
        (
            "em_lab/EBEAM_COLUMN[ebeam_column]/electron_source/voltage",
            ureg.volt,
            "AcceleratingVoltage",
        ),
        (
            "em_lab/EBEAM_COLUMN[ebeam_column]/electron_source/filament_current",
            ureg.ampere,
            "FilamentCurrent",
        ),
        (
            "em_lab/EBEAM_COLUMN[ebeam_column]/electron_source/emission_current",
            ureg.ampere,
            "EmissionCurrent",
        ),
    ],
}


HITACHI_STATIC_VARIOUS_TO_NX_EM = {
    "prefix_trg": "/ENTRY[entry*]/measurement/em_lab",
    "prefix_src": "",
    "use": [("FABRICATION[fabrication]/vendor", "Hitachi")],
    "map": [
        ("FABRICATION[fabrication]/model", "InstructName"),
        ("FABRICATION[fabrication]/model", "Instrument name"),
        ("FABRICATION[fabrication]/identifier", "SerialNumber"),
    ],
}
