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
"""Parser for reading content from Bruker *.BCF files via rosettasciio."""

from typing import Dict, List

from pynxtools_em.parsers.rsciio_base import RsciioBaseParser
from rsciio import bruker


class RsciioBrukerParser(RsciioBaseParser):
    """Read Bruker BCF File Format bcf."""

    def __init__(self, file_path: str = ""):
        super().__init__(file_path)
        self.tmp: Dict = {}
        self.objs: List = []
        self.version: Dict = {}
        self.supported = False
        self.check_if_supported()

    def check_if_supported(self):
        """Check if provided content matches Bruker concepts."""
        try:
            self.objs = bruker.file_reader(self.file_path)
            # TODO::what to do if the content of the file is larger than the available
            # main memory, one approach to handle this is to have the file_reader parsing
            # only the collection of the concepts without the actual instance data
            # based on this one could then plan how much memory has to be reserved
            # in the template and stream out accordingly
            self.supported = True
        except IOError:
            print(f"Loading {self.file_path} using Bruker is not supported !")

    def parse_and_normalize(self, template: dict) -> dict:
        """Perform actual parsing filling cache."""
        if self.supported:
            print(f"Parsing via Bruker...")
            self.normalize_eds_content(template)
            self.normalize_eels_content(template)
        else:
            print(
                f"{self.file_path} is not a Bruker-specific "
                f"BCF file that this parser can process !"
            )
        return template

    def normalize_eds_content(self, template: dict) -> dict:
        """TODO implementation."""
        return template

    def normalize_eels_content(self, template: dict) -> dict:
        """TODO implementation."""
        return template

    def process_into_template(self, template: dict) -> dict:
        """TODO implementation."""
        if self.supported:
            self.process_event_data_em_metadata(template)
            self.process_event_data_em_data(template)
        return template

    def process_event_data_em_metadata(self, template: dict) -> dict:
        """TODO implementation."""
        return template

    def process_event_data_em_data(self, template: dict) -> dict:
        """TODO implementation."""
        return template
