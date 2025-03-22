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
"""Dict mapping custom schema instances from eln_data.yaml file on concepts in NXem."""

from typing import Any, Dict

from pynxtools_em.utils.pint_custom_unit_registry import ureg

OASISELN_EM_ENTRY_TO_NEXUS: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]",
    "prefix_src": "entry/",
    "map_to_str": [
        "experiment_alias",
        "start_time",
        "end_time",
        "experiment_description",
    ],
}


OASISELN_EM_SAMPLE_TO_NEXUS: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/SAMPLE[sample]",
    "prefix_src": "sample/",
    "map_to_str": [
        "name",
        "atom_types",
        "preparation_date",
        ("type", "method"),
    ],
    "map_to_bool": ["is_simulation"],
    "map_to_f8": [("thickness", ureg.meter, "thickness/value", "thickness/unit")],
}


OASISELN_EM_USER_TO_NEXUS: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/USER[user*]",
    "prefix_src": "",
    "map_to_str": [
        "name",
        "affiliation",
        "address",
        "email",
        "telephone_number",
        "role",
    ],
}
