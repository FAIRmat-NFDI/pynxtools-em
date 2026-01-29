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
"""Parser for reading content from MRC via rosettasciio."""

from rsciio import mrc

from pynxtools_em.utils.custom_logging import logger
from pynxtools_em.utils.default_config import DEFAULT_VERBOSITY
from pynxtools_em.utils.get_checksum import get_sha256_of_file_content


class RsciioMrcParser:
    """Read MRC file format."""

    def __init__(
        self, file_path: str = "", entry_id: int = 1, verbose: bool = DEFAULT_VERBOSITY
    ):
        if file_path:
            self.file_path = file_path
            self.entry_id = entry_id if entry_id > 0 else 1
            self.verbose = verbose
            self.objs: list = []
            self.version: dict = {}
            self.supported = False
            self.check_if_supported()
            if not self.supported:
                logger.debug(
                    f"Parser {self.__class__.__name__} finds no content in {file_path} that it supports"
                )
        else:
            logger.warning(f"Parser {self.__class__.__name__} needs MRC file !")
            self.supported = False

    def check_if_supported(self):
        """Check if provided content matches MRC concepts."""
        self.supported = False
        try:
            self.objs = mrc.file_reader(self.file_path)
            # TODO::out-of-memory
            self.supported = True
        except (OSError, FileNotFoundError):
            logger.warning(f"{self.file_path} either FileNotFound or IOError !")
            return

    def parse(self, template: dict) -> dict:
        """Perform actual parsing."""
        if self.supported:
            with open(self.file_path, "rb", 0) as fp:
                self.file_path_sha256 = get_sha256_of_file_content(fp)
            logger.info(
                f"Parsing {self.file_path} MRC with SHA256 {self.file_path_sha256} ..."
            )
            self.parse_content(template)
        return template

    def parse_content(self, template: dict) -> dict:
        """Translate tech partner concepts to NeXus concepts."""
        return template
