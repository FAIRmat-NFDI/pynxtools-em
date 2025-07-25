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
"""Parse ELN metadata for C. Koch's NOMAD OASIS at HU Berlin, CSMB."""

import pathlib

import flatdict as fd
import yaml

from pynxtools_em.concepts.mapping_functors_pint import add_specific_metadata_pint
from pynxtools_em.examples.ger_berlin_koch_cfg import (
    GER_BERLIN_KOCH_GROUP_ECOLUMN_TO_NEXUS,
    GER_BERLIN_KOCH_GROUP_ESOURCE_TO_NEXUS,
    GER_BERLIN_KOCH_GROUP_INSTRUMENT_TO_NEXUS,
)
from pynxtools_em.utils.get_checksum import get_sha256_of_file_content


class NxEmCustomElnGerBerlinKoch:
    """Parse deployment specific configuration."""

    def __init__(self, file_path: str = "", entry_id: int = 1, verbose: bool = True):
        if pathlib.Path(file_path).name.endswith(
            ("custom_eln_data.yaml", "custom_eln_data.yml")
        ):
            self.file_path = file_path
            self.entry_id = entry_id if entry_id > 0 else 1
            self.verbose = verbose
            self.flat_metadata = fd.FlatDict({}, "/")
            self.supported = False
            self.check_if_supported()
            if not self.supported:
                print(
                    f"Parser {self.__class__.__name__} finds no content in {file_path} that it supports"
                )
        else:
            print(f"Parser {self.__class__.__name__} needs custom_eln_data.yaml file !")
            self.supported = False

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
            self.parse_static_metadata_nion_microscope(template)
        return template

    def parse_static_metadata_nion_microscope(self, template: dict) -> dict:
        """Copy data from example-specific section into template."""
        # print(f"Mapping some of the Zeiss metadata on respective NeXus concepts...")
        identifier = [self.entry_id]
        for cfg in [
            GER_BERLIN_KOCH_GROUP_INSTRUMENT_TO_NEXUS,
            GER_BERLIN_KOCH_GROUP_ESOURCE_TO_NEXUS,
            GER_BERLIN_KOCH_GROUP_ECOLUMN_TO_NEXUS,
        ]:
            add_specific_metadata_pint(
                cfg,
                self.flat_metadata,
                identifier,
                template,
            )
        return template
