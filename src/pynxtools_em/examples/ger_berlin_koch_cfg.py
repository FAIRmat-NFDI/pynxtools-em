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
"""Dict mapping values for a specifically configured NOMAD Oasis."""

from typing import Any, Dict

from pynxtools_em.utils.pint_custom_unit_registry import ureg

GER_BERLIN_KOCH_GROUP_INSTRUMENT_TO_NEXUS: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/instrument",
    "prefix_src": "instrument/",
    "map_to_str": [
        "location",
        "name",
        "capabilities",
        ("fabrication/vendor", "vendor"),
        ("fabrication/model", "model"),
        ("fabrication/serial_number", "serial_number"),
    ],
}

GER_BERLIN_KOCH_GROUP_ECOLUMN_TO_NEXUS: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/instrument/ebeam_column",
    "prefix_src": "ebeam_column/",
    "map_to_str": [
        ("fabrication/vendor", "vendor"),
        ("fabrication/model", "model"),
        ("fabrication/serial_number", "serial_number"),
    ],
}

GER_BERLIN_KOCH_GROUP_ESOURCE_TO_NEXUS: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/instrument/ebeam_column/electron_source",
    "prefix_src": "electron_source/",
    "map_to_str": [
        "name",
        "emitter_type",
    ],
    "map_to_f8": [
        ("voltage", ureg.volt, "voltage/value", "voltage/unit"),
    ],
}
