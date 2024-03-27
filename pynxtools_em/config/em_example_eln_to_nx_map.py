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


EM_EXAMPLE_OTHER_TO_NEXUS = []

# NeXus concept specific mapping tables which require special treatment as the current
# NOMAD Oasis custom schema implementation delivers them as a list of dictionaries instead
# of a directly flattenable list of key, value pairs

EM_EXAMPLE_USER_TO_NEXUS = [
    ("/ENTRY[entry*]/USER[user*]/name", "load_from", "name"),
    ("/ENTRY[entry*]/USER[user*]/affiliation", "load_from", "affiliation"),
    ("/ENTRY[entry*]/USER[user*]/address", "load_from", "address"),
    ("/ENTRY[entry*]/USER[user*]/email", "load_from", "email"),
    (
        "/ENTRY[entry*]/USER[user*]/IDENTIFIER[identifier]/identifier",
        "load_from",
        "orcid",
    ),
    ("/ENTRY[entry*]/USER[user*]/IDENTIFIER[identifier]/service", "orcid"),
    ("/ENTRY[entry*]/USER[user*]/IDENTIFIER[identifier]/is_persistent", False),
    ("/ENTRY[entry*]/USER[user*]/telephone_number", "load_from", "telephone_number"),
    ("/ENTRY[entry*]/USER[user*]/role", "load_from", "role"),
    ("/ENTRY[entry*]/USER[user*]/social_media_name", "load_from", "social_media_name"),
    (
        "/ENTRY[entry*]/USER[user*]/social_media_platform",
        "load_from",
        "social_media_platform",
    ),
]
