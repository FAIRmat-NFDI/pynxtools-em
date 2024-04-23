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

import flatdict as fd
import yaml


from pynxtools_em.config.eln_cfg import (
    EM_EXAMPLE_ENTRY_TO_NEXUS,
    EM_EXAMPLE_SAMPLE_TO_NEXUS,
    EM_EXAMPLE_USER_TO_NEXUS,
)
from pynxtools_em.concepts.concept_mapper import variadic_path_to_specific_path


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

    def parse_entry(self, template: dict) -> dict:
        """Copy data from entry section into template."""
        src = "entry"
        identifier = [self.entry_id]
        if src in self.yml:
            if isinstance(self.yml[src], fd.FlatDict):
                for key in self.yml[src]:
                    variadic_prefix = EM_EXAMPLE_ENTRY_TO_NEXUS["prefix"]
                    for entry in EM_EXAMPLE_ENTRY_TO_NEXUS["load"]:
                        if isinstance(entry, str) and key == entry:
                            trg = variadic_path_to_specific_path(
                                f"{variadic_prefix}/{entry}", identifier
                            )
                            template[trg] = self.yml[src][entry]
                            break
                        elif isinstance(entry, tuple) and len(entry) == 2:
                            if key == entry[1]:
                                trg = variadic_path_to_specific_path(
                                    f"{variadic_prefix}/{entry[0]}", identifier
                                )
                                template[trg] = self.yml[src][entry[1]]
                                break
                    for entry in EM_EXAMPLE_ENTRY_TO_NEXUS["iso8601"]:
                        if isinstance(entry, str) and key == entry:
                            trg = variadic_path_to_specific_path(
                                f"{variadic_prefix}/{entry}", identifier
                            )
                            template[trg] = self.yml[src][entry].isoformat()
        return template

    def parse_sample(self, template: dict) -> dict:
        """Copy data from entry section into template."""
        src = "sample"
        identifier = [self.entry_id]
        if src in self.yml:
            if isinstance(self.yml[src], fd.FlatDict):
                for key in self.yml[src]:
                    variadic_prefix = EM_EXAMPLE_SAMPLE_TO_NEXUS["prefix"]
                    for entry in EM_EXAMPLE_SAMPLE_TO_NEXUS["load"]:
                        if isinstance(entry, str) and key == entry:
                            trg = variadic_path_to_specific_path(
                                f"{variadic_prefix}/{entry}", identifier
                            )
                            template[trg] = self.yml[src][entry]
                            break
                        elif isinstance(entry, tuple) and len(entry) == 2:
                            if key == entry[1]:
                                trg = variadic_path_to_specific_path(
                                    f"{variadic_prefix}/{entry[0]}", identifier
                                )
                                template[trg] = self.yml[src][entry[1]]
                                break
                    for entry in EM_EXAMPLE_SAMPLE_TO_NEXUS["iso8601"]:
                        if isinstance(entry, str) and key == entry:
                            trg = variadic_path_to_specific_path(
                                f"{variadic_prefix}/{entry}", identifier
                            )
                            template[trg] = self.yml[src][entry].isoformat()
                            break
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
                            if key != "orcid":
                                for entry in EM_EXAMPLE_USER_TO_NEXUS["load"]:
                                    if isinstance(entry, str) and key == entry:
                                        trg = variadic_path_to_specific_path(
                                            f"{variadic_prefix}/{entry}", identifier
                                        )
                                        template[trg] = user_dict[entry]
                                        break
                                    elif isinstance(entry, tuple) and len(entry) == 2:
                                        if key == entry[1]:
                                            trg = variadic_path_to_specific_path(
                                                f"{variadic_prefix}/{entry[0]}",
                                                identifier,
                                            )
                                            template[trg] = user_dict[entry[1]]
                                            break
                            else:
                                trg = variadic_path_to_specific_path(
                                    f"{variadic_prefix}", identifier
                                )
                                template[f"{trg}/IDENTIFIER[identifier]/identifier"] = (
                                    user_dict["orcid"]
                                )
                                template[f"{trg}/IDENTIFIER[identifier]/service"] = (
                                    "orcid"
                                )
                                template[
                                    f"{trg}/IDENTIFIER[identifier]/is_persistent"
                                ] = False
                        user_id += 1
        return template

    def report(self, template: dict) -> dict:
        """Copy data from self into template the appdef instance."""
        self.parse_entry(template)
        self.parse_sample(template)
        self.parse_user(template)
        return template
