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
"""Parser mapping concepts and content from Marc deGraeff's EMsoft *.h5 files on NXem."""

from typing import Dict

import h5py

from pynxtools_em.methods.ebsd import has_hfive_magic_header
from pynxtools_em.parsers.hfive_base import HdfFiveBaseParser
from pynxtools_em.utils.custom_logging import logger


class HdfFiveEmSoftParser(HdfFiveBaseParser):
    """Read EMsoft H5 (Marc deGraeff Carnegie Mellon)"""

    def __init__(self, file_path: str = "", entry_id: int = 1, verbose: bool = True):
        if file_path:
            self.file_path = file_path
            self.id_mgn: Dict[str, int] = {
                "entry_id": entry_id if entry_id > 0 else 1,
                "roi_id": 1,
            }
            self.verbose = verbose
            self.prfx = ""  # template path handling
            self.version: Dict = {
                "trg": {
                    "tech_partner": ["EMsoft"],
                    "schema_name": ["EMsoft"],
                    "schema_version": ["EMsoft"],
                    "writer_name": ["EMsoft"],
                    "writer_version": ["EMsoft"],
                },
                "src": {},
            }
            self.supported = False
            self.check_if_supported()
            if not self.supported:
                logger.debug(
                    f"Parser {self.__class__.__name__} finds no content in {file_path} that it supports"
                )
        else:
            logger.warning(f"Parser {self.__class__.__name__} needs EMsoft HDF5 file !")
            self.supported = False

    def check_if_supported(self):
        """Check if instance matches all constraints to EMsoft"""
        self.supported = False
        if not has_hfive_magic_header(self.file_path):
            return

        with h5py.File(self.file_path, "r") as h5r:
            for req_group in [
                "CrystalData",
                "EMData",
                "EMheader",
                "NMLfiles",
                "NMLparameters",
            ]:
                if f"/{req_group}" not in h5r:
                    return
            self.supported = True
            for keyword in [
                "tech_partner",
                "schema_name",
                "schema_version",
                "writer_name",
                "writer_version",
            ]:
                self.version["src"][keyword] = self.version["trg"][keyword]

    def parse(self, template: dict) -> dict:
        if self.supported:
            logger.info(f"Parsing via Carnegie/Mellon EMsoft parser...")
            logger.critical("TODO::add functionality")
        return template
