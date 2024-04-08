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
"""Wrapping multiple parsers for vendor files with NOMAD Oasis/ELN/YAML metadata."""

import flatdict as fd
import yaml


from pynxtools_em.config.em_example_eln_to_nx_map import (
    EM_EXAMPLE_OTHER_TO_NEXUS,
    EM_EXAMPLE_CSYS_TO_NEXUS,
    EM_EXAMPLE_USER_TO_NEXUS,
)
from pynxtools_em.shared.shared_utils import (
    rchop, get_sha256_of_file_content
)
from pynxtools_em.shared.mapping_functors import (
    variadic_path_to_specific_path
)


class NxEmNomadOasisElnSchemaParser:
    """Parse eln_data.yaml instance data from a NOMAD Oasis YAML.

    The implementation approach is not to copy over everything but only specific
    pieces of information relevant from the NeXus perspective
    """

    def __init__(self, file_path: str, entry_id: int, verbose: bool = False):
        print(f"Extracting data from ELN file: {file_path}")
        if (
            file_path.rsplit("/", 1)[-1].startswith("eln_data")
            or file_path.startswith("eln_data")
        ) and entry_id > 0:
            self.entry_id = entry_id
            self.file_path = file_path
            with open(self.file_path, "r", encoding="utf-8") as stream:
                self.yml = fd.FlatDict(yaml.safe_load(stream), delimiter="/")
                if verbose is True:
                    for key, val in self.yml.items():
                        print(f"key: {key}, value: {val}")
        else:
            self.entry_id = 1
            self.file_path = ""
            self.yml = {}

    def parse_reference_frames(self, template: dict) -> dict:
        """Copy details about frames of reference into template."""
        src = "coordinate_system"
        if src in self.yml:
            if isinstance(self.yml[src], list):
                if all(isinstance(entry, dict) for entry in self.yml[src]):
                    csys_id = 1
                    # custom schema delivers a list of dictionaries...
                    for csys_dict in self.yml[src]:
                        if csys_dict == {}:
                            continue
                        identifier = [self.entry_id, csys_id]
                        variadic_prefix = EM_EXAMPLE_CSYS_TO_NEXUS["prefix"]
                        for key in csys_dict:
                            # EM_EXAMPLE_CSYS_TO_NEXUS["use"] is None
                            for entry in EM_EXAMPLE_CSYS_TO_NEXUS["load_from"]:
                                if isinstance(entry, str) and key == entry:
                                    trg = variadic_path_to_specific_path(
                                        f"{variadic_prefix}/{entry}", identifier
                                    )
                                    template[trg] = csys_dict[entry]
                                if isinstance(entry, tuple) and len(entry) == 2:
                                    if key == entry[1]:
                                       trg = variadic_path_to_specific_path(
                                           f"{variadic_prefix}/{entry[0]}", identifier
                                       )
                                       template[trg] = csys_dict[entry[1]]
                        csys_id += 1
        return template

    def parse_user(self, template: dict) -> dict:
        """Copy data from user section into template."""
        src = "user"
        if src in self.yml:
            if isinstance(self.yml[src], list):
                if all(isinstance(entry, dict) for entry in self.yml[src]):
                    user_id = 1
                    # custom schema delivers a list of dictionaries...
                    for user_dict in self.yml[src]:
                        if user_dict == {}:
                            continue
                        identifier = [self.entry_id, user_id]
                        variadic_prefix = EM_EXAMPLE_USER_TO_NEXUS["prefix"]
                        for key in user_dict:
                            for tpl in EM_EXAMPLE_USER_TO_NEXUS["member"]:
                                if isinstance(tpl, tuple) and (len(tpl) == 3):
                                    if (tpl[1] == "load_from") and (key == tpl[2]):
                                        trg = variadic_path_to_specific_path(
                                            f"{variadic_prefix}/{tpl[0]}", identifier
                                        )
                                        # res = apply_modifier(modifier, user_dict)
                                        template[trg] = user_dict[tpl[2]]
                        user_id += 1
        return template

    def report(self, template: dict) -> dict:
        """Copy data from self into template the appdef instance."""
        self.parse_reference_frames(template)
        # self.parse_user(template)
        return template
