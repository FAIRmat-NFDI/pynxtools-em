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
#       "load_from": list of single value or pair (trg, src)
#           if single value this means that the endpoint of trg and src is the same
#           e.g. in the example below "name" means
#           ("/ENTRY[entry*]/USER[user*]/name, "load_from", "name")
#           if pair load the value pointed to by src and copy into trg

EM_EXAMPLE_ENTRY_TO_NEXUS = {
    "prefix": "/ENTRY[entry*]",
    "load_from": ["experiment_alias", "start_time"],
}


EM_EXAMPLE_SAMPLE_TO_NEXUS = {
    "prefix": "/ENTRY[entry*]",
    "load_from": ["method", "atom_types", "preparation_date"],
}


EM_EXAMPLE_USER_TO_NEXUS = {
    "prefix": "/ENTRY[entry*]/USER[user*]",
    "use": [
        ("IDENTIFIER[identifier]/identifier", "orcid"),
        ("IDENTIFIER[identifier]/service", "orcid"),
        ("IDENTIFIER[identifier]/is_persistent", False),
    ],
    "load_from": [
        "name",
        "affiliation",
        "address",
        "email",
        "telephone_number",
        "role",
    ],
}