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

# import datetime as dt
# f"{dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00', 'Z')}",

OASISCFG_EM_CSYS_TO_NEXUS: dict[str, str | list[str | tuple[str, str]]] = {
    "prefix_trg": "/ENTRY[entry*]/NAMED_reference_frameID[custom_reference_frame]",
    "prefix_src": "",
    "map_to_str": [
        "alias",
        "type",
        "handedness",
        "origin",
        ("x_direction", "xaxis_direction"),
        ("x_alias", "xaxis_alias"),
        ("y_direction", "yaxis_direction"),
        ("y_alias", "yaxis_alias"),
        ("z_direction", "zaxis_direction"),
        ("z_alias", "zaxis_alias"),
    ],
}


OASISCFG_EM_CITATION_TO_NEXUS: dict[str, str | list[str]] = {
    "prefix_trg": "/ENTRY[entry*]/citeID[cite*]",
    "prefix_src": "",
    "map_to_str": ["author", "doi", "description", "url"],
}


OASISCFG_EM_NOTE_TO_NEXUS: dict[str, str | list[str]] = {
    "prefix_trg": "/ENTRY[entry*]/noteID[note*]",
    "prefix_src": "",
    "map_to_str": ["file_name"],
}


OASISCFG_EM_SAMPLE_TO_NEXUS: dict[str, str | list[str]] = {
    "prefix_trg": "/ENTRY[entry*]/sampleID[sample]",
    "prefix_src": "sample/",
    "map_to_bool": ["is_simulation"],
    "map_to_str": ["atom_types"],
}


OASISCFG_EM_PROJECT_TO_NEXUS: dict[str, str | list[str]] = {
    "prefix_trg": "/ENTRY[entry*]/project",
    "prefix_src": "project/",
    "map_to_str": ["name"],
}

OASISCFG_EM_INSTRUMENT_TO_NEXUS: dict[str, str | list[str]] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/instrument",
    "prefix_src": "measurement/instrument/",
    "map_to_str": ["fabrication/vendor", "fabrication/model"],
}


OASISCFG_EM_USER_TO_NEXUS: dict[str, str | list[str | tuple[str, str]]] = {
    "prefix_trg": "/ENTRY[entry*]/userID[user*]",
    "prefix_src": "",
    "map_to_str": [
        "name",
        ("ORCID", "orcid"),
        "affiliation",
        "address",
        "email",
        "telephone_number",
        "role",
    ],
}
