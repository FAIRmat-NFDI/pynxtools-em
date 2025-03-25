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

from typing import Any, Dict

from pynxtools_em.utils.pint_custom_unit_registry import ureg

HITACHI_DYNAMIC_VARIOUS_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/events/EVENT_DATA_EM[event_data_em*]",
    "prefix_src": "",
    "map_to_f8": [
        ("instrument/optics/magnification", "Magnification"),
        (
            "instrument/optics/working_distance",
            ureg.meter,
            "WorkingDistance",
        ),
        (
            "instrument/ebeam_column/electron_source/voltage",
            ureg.volt,
            "AcceleratingVoltage",
        ),
        (
            "instrument/ebeam_column/electron_source/filament_current",
            ureg.ampere,
            "FilamentCurrent",
        ),
        (
            "instrument/ebeam_column/electron_source/emission_current",
            ureg.ampere,
            "EmissionCurrent",
        ),
    ],
}


HITACHI_STATIC_VARIOUS_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/instrument/fabrication",
    "prefix_src": "",
    "use": [("vendor", "Hitachi")],
    "map_to_str": [
        ("model", "InstructName"),
        ("model", "Instrument name"),
        ("serial_number", "SerialNumber"),
    ],
}
