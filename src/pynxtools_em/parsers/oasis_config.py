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
"""Parser NOMAD-Oasis-specific configuration serialized as oasis.yaml to NeXus NXem."""

import pathlib

import flatdict as fd
import yaml
from pynxtools_em.concepts.mapping_functors_pint import add_specific_metadata_pint
from pynxtools_em.configurations.oasis_cfg import (
    OASISCFG_EM_CITATION_TO_NEXUS,
    OASISCFG_EM_CSYS_TO_NEXUS,
)
from pynxtools_em.utils.get_file_checksum import (
    DEFAULT_CHECKSUM_ALGORITHM,
    get_sha256_of_file_content,
)


class NxEmNomadOasisConfigParser:
    """Parse deployment specific configuration."""

    def __init__(self, file_path: str = "", entry_id: int = 1, verbose: bool = False):
        if pathlib.Path(file_path).name.endswith(
            ".oasis.specific.yaml"
        ) or pathlib.Path(file_path).name.endswith(".oasis.specific.yml"):
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
                self.flat_metadata = fd.FlatDict(yaml.safe_load(stream), "/")
                if self.verbose:
                    for key, val in self.flat_metadata.items():
                        print(f"key: {key}, val: {val}")
                self.supported = True
        except (FileNotFoundError, IOError):
            print(f"{self.file_path} either FileNotFound or IOError !")
            return

    def parse(self, template: dict) -> dict:
        """Copy data from configuration applying mapping functors."""
        if self.supported:
            with open(self.file_path, "rb", 0) as fp:
                self.file_path_sha256 = get_sha256_of_file_content(fp)
            print(
                f"Parsing {self.file_path} NOMAD Oasis/config with SHA256 {self.file_path_sha256} ..."
            )
            self.parse_reference_frames(template)
            self.parse_example(template)
        return template

    def parse_reference_frames(self, template: dict) -> dict:
        """Copy details about frames of reference into template."""
        src = "coordinate_system_set"
        if src in self.flat_metadata:
            if isinstance(self.flat_metadata[src], list):
                if all(isinstance(entry, dict) for entry in self.flat_metadata[src]):
                    csys_id = 1
                    # custom schema delivers a list of dictionaries...
                    for csys_dict in self.flat_metadata[src]:
                        if len(csys_dict) == 0:
                            continue
                        identifier = [self.entry_id, csys_id]
                        add_specific_metadata_pint(
                            OASISCFG_EM_CSYS_TO_NEXUS,
                            csys_dict,
                            identifier,
                            template,
                        )
                        csys_id += 1
        return template

    def parse_example(self, template: dict) -> dict:
        """Copy data from example-specific section into template."""
        src = "citation"
        if src in self.flat_metadata:
            if isinstance(self.flat_metadata[src], list):
                if (
                    all(isinstance(entry, dict) for entry in self.flat_metadata[src])
                    is True
                ):
                    cite_id = 1
                    # custom schema delivers a list of dictionaries...
                    for cite_dict in self.flat_metadata[src]:
                        if len(cite_dict) == 0:
                            continue
                        identifier = [self.entry_id, cite_id]
                        add_specific_metadata_pint(
                            OASISCFG_EM_CITATION_TO_NEXUS,
                            cite_dict,
                            identifier,
                            template,
                        )
                        cite_id += 1
        return template
