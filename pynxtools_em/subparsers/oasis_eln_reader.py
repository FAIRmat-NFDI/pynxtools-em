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
"""Parser generic ELN content serialized as eln_data.yaml to NeXus NXem."""

import pathlib

import flatdict as fd
import yaml

from pynxtools_em.concepts.mapping_functors import add_specific_metadata
from pynxtools_em.config.eln_cfg import (
    EM_ENTRY_TO_NEXUS,
    EM_SAMPLE_TO_NEXUS,
    EM_USER_IDENTIFIER_TO_NEXUS,
    EM_USER_TO_NEXUS,
)


class NxEmNomadOasisElnSchemaParser:
    """Parse eln_data.yaml instance data from a NOMAD Oasis YAML.

    The implementation approach is not to copy over everything but only specific
    pieces of information relevant from the NeXus perspective
    """

    def __init__(self, file_path: str, entry_id: int, verbose: bool = False):
        print(f"Extracting data from ELN file {file_path} ...")
        if (
            pathlib.Path(file_path).name.endswith("eln_data.yaml")
            or pathlib.Path(file_path).name.endswith("eln_data.yml")
        ) and entry_id > 0:
            self.entry_id = entry_id
            self.file_path = file_path
            with open(self.file_path, "r", encoding="utf-8") as stream:
                self.yml = fd.FlatDict(yaml.safe_load(stream), delimiter="/")
                if verbose:
                    for key, val in self.yml.items():
                        print(f"key: {key}, value: {val}")
        else:
            self.entry_id = 1
            self.file_path = ""
            self.yml = {}

    def parse_entry(self, template: dict) -> dict:
        """Copy data from entry section into template."""
        identifier = [self.entry_id]
        add_specific_metadata(EM_ENTRY_TO_NEXUS, self.yml, identifier, template)
        return template

    def parse_sample(self, template: dict) -> dict:
        """Copy data from entry section into template."""
        identifier = [self.entry_id]
        add_specific_metadata(EM_SAMPLE_TO_NEXUS, self.yml, identifier, template)
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
                        add_specific_metadata(
                            EM_USER_TO_NEXUS,
                            fd.FlatDict(user_dict),
                            identifier,
                            template,
                        )
                        if "orcid" in user_dict:
                            add_specific_metadata(
                                EM_USER_IDENTIFIER_TO_NEXUS,
                                fd.FlatDict(user_dict),
                                identifier,
                                template,
                            )
                        user_id += 1
        return template

    def report(self, template: dict) -> dict:
        """Copy data from self into template the appdef instance."""
        self.parse_entry(template)
        self.parse_sample(template)
        self.parse_user(template)
        return template
