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
from pynxtools_em.concepts.mapping_functors_pint import add_specific_metadata_pint
from pynxtools_em.configurations.eln_cfg import (
    OASISELN_EM_ENTRY_TO_NEXUS,
    OASISELN_EM_SAMPLE_TO_NEXUS,
    OASISELN_EM_USER_IDENTIFIER_TO_NEXUS,
    OASISELN_EM_USER_TO_NEXUS,
)
from pynxtools_em.utils.get_file_checksum import (
    DEFAULT_CHECKSUM_ALGORITHM,
    get_sha256_of_file_content,
)


class NxEmNomadOasisElnSchemaParser:
    """Parse eln_data.yaml instance data from a NOMAD Oasis YAML.

    The implementation approach is not to copy over everything but only specific
    pieces of information relevant from the NeXus perspective
    """

    def __init__(self, file_path: str = "", entry_id: int = 1, verbose: bool = False):
        if pathlib.Path(file_path).name.endswith("eln_data.yaml") or pathlib.Path(
            file_path
        ).name.endswith("eln_data.yml"):
            self.file_path = file_path
        self.entry_id = entry_id if entry_id > 0 else 1
        self.verbose = verbose
        self.flat_metadata = fd.FlatDict({}, "/")
        self.supported = False
        self.check_if_supported()

    def check_if_supported(self):
        self.supported = False
        try:
            with open(self.file_path, "r", encoding="utf-8") as stream:
                self.flat_metadata = fd.FlatDict(yaml.safe_load(stream), delimiter="/")

                if self.verbose:
                    for key, val in self.flat_metadata.items():
                        print(f"key: {key}, value: {val}")
            self.supported = True
        except (FileNotFoundError, IOError):
            print(f"{self.file_path} either FileNotFound or IOError !")
            return

    def parse(self, template: dict) -> dict:
        """Copy data from self into template the appdef instance."""
        if self.supported:
            with open(self.file_path, "rb", 0) as fp:
                self.file_path_sha256 = get_sha256_of_file_content(fp)
            print(
                f"Parsing {self.file_path} NOMAD Oasis/ELN with SHA256 {self.file_path_sha256} ..."
            )
            self.parse_entry(template)
            self.parse_sample(template)
            self.parse_user(template)
        return template

    def parse_entry(self, template: dict) -> dict:
        """Copy data from entry section into template."""
        identifier = [self.entry_id]
        add_specific_metadata_pint(
            OASISELN_EM_ENTRY_TO_NEXUS, self.flat_metadata, identifier, template
        )
        return template

    def parse_sample(self, template: dict) -> dict:
        """Copy data from entry section into template."""
        identifier = [self.entry_id]
        add_specific_metadata_pint(
            OASISELN_EM_SAMPLE_TO_NEXUS, self.flat_metadata, identifier, template
        )
        return template

    def parse_user(self, template: dict) -> dict:
        """Copy data from user section into template."""
        src = "user"
        if src in self.flat_metadata:
            if isinstance(self.flat_metadata[src], list):
                if all(isinstance(entry, dict) for entry in self.flat_metadata[src]):
                    user_id = 1
                    # custom schema delivers a list of dictionaries...
                    for user_dict in self.flat_metadata[src]:
                        if len(user_dict) == 0:
                            continue
                        identifier = [self.entry_id, user_id]
                        add_specific_metadata_pint(
                            OASISELN_EM_USER_TO_NEXUS,
                            user_dict,
                            identifier,
                            template,
                        )
                        if "orcid" in user_dict:
                            add_specific_metadata_pint(
                                OASISELN_EM_USER_IDENTIFIER_TO_NEXUS,
                                user_dict,
                                identifier,
                                template,
                            )
                        user_id += 1
        return template
