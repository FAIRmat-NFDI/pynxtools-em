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

# mapping instructions as a dictionary
#   prefix is the (variadic prefix to be add to every path on the target side)
#   different modifiers are used
#       "use": list of pair of trg, src endpoint, take the value in src copy into trg
#       "load": list of single value or pair (trg, src)
#           if single value this means that the endpoint of trg and src is the same
#           e.g. in the example below "name" means
#           ("/ENTRY[entry*]/USER[user*]/name, "load", "name")
#           if pair load the value pointed to by src and copy into trg
#       difference between load and map_to is that load assumes no e.g. string to real
#       conversion is required while map_does not assume this
#       and instead does the conversion also

EM_ENTRY_TO_NEXUS = {
    "prefix_trg": "/ENTRY[entry*]",
    "prefix_src": "entry/",
    "map_to_str": [
        "experiment_alias",
        "start_time",
        "end_time",
        "experiment_description",
    ],
}


EM_SAMPLE_TO_NEXUS = {
    "prefix_trg": "/ENTRY[entry*]/sample",
    "prefix_src": "sample/",
    "map_to_str": [("thickness/@units", "thickness/unit")],
    "map": [
        "method",
        "name",
        "atom_types",
        "preparation_date",
        ("thickness", "thickness/value"),
    ],
}


EM_USER_TO_NEXUS = {
    "prefix_trg": "/ENTRY[entry*]/USER[user*]",
    "map": [
        "name",
        "affiliation",
        "address",
        "email",
        "telephone_number",
        "role",
    ],
}


EM_USER_IDENTIFIER_TO_NEXUS = {
    "prefix_trg": "/ENTRY[entry*]/USER[user*]",
    "use": [
        ("IDENTIFIER[identifier]/identifier", "orcid"),
        ("IDENTIFIER[identifier]/service", "orcid"),
        ("IDENTIFIER[identifier]/is_persistent", True),
    ],
}
