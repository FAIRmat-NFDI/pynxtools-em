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
"""Parse ELN metadata for the EM database use case."""

import pathlib

import flatdict as fd
import yaml

from pynxtools_em.concepts.mapping_functors_pint import add_specific_metadata_pint
from pynxtools_em.examples.ebsd_database_eln_cfg import (
    EBSD_DATABASE_CITATION_TO_NEXUS,
    EBSD_DATABASE_SPECIMEN_TO_NEXUS,
)
from pynxtools_em.utils.custom_logging import logger
from pynxtools_em.utils.get_checksum import get_sha256_of_file_content


class NxEmCustomElnEbsdDatabase:
    """Parse example-specific metadata like coming from an external src e.g. ELN."""

    def __init__(
        self, file_path: str = "", entry_id: int = 1, verbose: bool = DEFAULT_VERBOSITY
    ):
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
                logger.debug(
                    f"Parser {self.__class__.__name__} finds no content in {file_path} that it supports"
                )
        else:
            logger.warning(
                f"Parser {self.__class__.__name__} needs custom_eln_data.yaml file !"
            )
            self.supported = False

    def check_if_supported(self):
        self.supported = False
        try:
            with open(self.file_path, "r", encoding="utf-8") as stream:
                self.flat_metadata = fd.FlatDict(yaml.safe_load(stream), "/")
                if self.verbose:
                    for key, val in self.flat_metadata.items():
                        logger.info(f"key: {key}, val: {val}")
                self.supported = True
        except (FileNotFoundError, IOError):
            logger.warning(f"{self.file_path} either FileNotFound or IOError !")
            return

    def parse(self, template: dict) -> dict:
        """Copy data from configuration applying mapping functors."""
        if self.supported:
            with open(self.file_path, "rb", 0) as fp:
                self.file_path_sha256 = get_sha256_of_file_content(fp)
            logger.info(
                f"Parsing {self.file_path} NOMAD Oasis/config with SHA256 {self.file_path_sha256} ..."
            )
            self.parse_metadata(template)
        return template

    def parse_metadata(self, template: dict) -> dict:
        """Copy data from example-specific section into template."""
        identifier = [self.entry_id]
        add_specific_metadata_pint(
            EBSD_DATABASE_SPECIMEN_TO_NEXUS,
            self.flat_metadata,
            identifier,
            template,
        )

        src = "citation"
        if src in self.flat_metadata:
            if isinstance(self.flat_metadata[src], list):
                if all(isinstance(entry, dict) for entry in self.flat_metadata[src]):
                    cite_id = 1
                    # custom schema delivers a list of dictionaries...
                    for cite_dict in self.flat_metadata[src]:
                        if len(cite_dict) > 0:
                            identifier = [self.entry_id, cite_id]
                            add_specific_metadata_pint(
                                EBSD_DATABASE_CITATION_TO_NEXUS,
                                cite_dict,
                                identifier,
                                template,
                            )
                            cite_id += 1
        return template
