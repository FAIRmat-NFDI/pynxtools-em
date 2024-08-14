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
"""(Sub-)parser for reading content from Gatan Digital Micrograph *.dm3 and *.dm4 (HDF5) via rosettasciio."""

from datetime import datetime
from typing import Dict, List

import flatdict as fd
import numpy as np
import pytz
from ase.data import chemical_symbols
from pynxtools_em.concepts.mapping_functors_pint import add_specific_metadata_pint

# from pynxtools_em.configurations.rsciio_gatan_cfg import
from pynxtools_em.parsers.rsciio_base import RsciioBaseParser
from pynxtools_em.utils.get_file_checksum import (
    DEFAULT_CHECKSUM_ALGORITHM,
    get_sha256_of_file_content,
)
from pynxtools_em.utils.numerics import COMPLEX_SPACE, REAL_SPACE
from pynxtools_em.utils.rsciio_hspy_utils import (
    all_req_keywords_in_dict,
    get_axes_dims,
    get_axes_units,
    get_named_axis,
)
from pynxtools_em.utils.string_conversions import string_to_number
from rsciio import digitalmicrograph as gatan


class RsciioGatanParser(RsciioBaseParser):
    """Read Gatan Digital Micrograph dm3/dm4 formats."""

    def __init__(self, entry_id: int = 1, file_path: str = "", verbose: bool = False):
        super().__init__(file_path)
        if entry_id > 0:
            self.entry_id = entry_id
        else:
            self.entry_id = 1
        self.event_id = 1
        self.file_path_sha256 = ""
        self.supported_version: Dict = {}
        self.version: Dict = {}
        self.supported = False
        self.verbose = verbose
        self.check_if_supported()

    def check_if_supported(self):
        self.supported = False
        try:
            self.objs = gatan.file_reader(
                self.file_path, lazy=False, order="C", optimize=True
            )
            # TODO::what to do if the content of the file is larger than the available
            # main memory, make use of lazy loading

            reqs = ["data", "axes", "metadata", "original_metadata", "mapping"]
            obj_idx_supported = List[int] = []
            for idx, obj in enumerate(self.objs):
                if not isinstance(obj, dict):
                    continue
                if not all_req_keywords_in_dict(obj, reqs):
                    continue
                # flat_metadata = fd.FlatDict(obj["original_metadata"], "/")
                # TODO::add version distinction logic from rsciio_velox
                obj_idx_supported.append(idx)
                if self.verbose:
                    print(f"{idx}-th obj is supported")
            if len(obj_idx_supported) > 0:  # at least some supported content
                self.supported = True
            else:
                print(
                    f"Parser {self.__class__.__name__} finds no content in {self.file_path} that it supports"
                )
        except IOError:
            return

    def parse(self, template: dict) -> dict:
        """Perform actual parsing filling cache self.tmp."""
        if self.supported:
            with open(self.file_path, "rb", 0) as fp:
                self.file_path_sha256 = get_sha256_of_file_content(fp)
            print(
                f"Parsing {self.file_path} Gatan with SHA256 {self.file_path_sha256} ..."
            )
            self.parse_content(template)
        return template

    def parse_content(self, template: dict) -> dict:
        """Translate tech partner concepts to NeXus concepts."""
        reqs = ["data", "axes", "metadata", "original_metadata", "mapping"]
        for idx, obj in enumerate(self.objs):
            if not isinstance(obj, dict):
                continue
            if not all_req_keywords_in_dict(obj, reqs):
                continue
            self.process_event_data_em_metadata(obj, template)
            self.process_event_data_em_data(obj, template)
            self.event_id += 1
            if self.verbose:
                print(f"obj{idx}, dims {obj['axes']}")
        return template

    def process_event_data_em_metadata(self, obj: dict, template: dict) -> dict:
        """Map Gatan Digital Micrograph-specific concept representations on NeXus concepts."""
        # use an own function for each instead of a loop of a template function call
        # as for each section there are typically always some extra formatting
        # steps required
        flat_metadata = fd.FlatDict(obj["original_metadata"], "/")
        identifier = [self.entry_id, self.event_id, 1]
        # for cfg in []:  # TODO::add configurations
        #    add_specific_metadata_pint(cfg, flat_metadata, identifier, template)

        return template

    def process_event_data_em_data(self, obj: dict, template: dict) -> dict:
        """Generic mapping of image data on NeXus template."""
        # assume rosettasciio-specific formatting of the obj informationemd parser
        # i.e. a dictionary with the following keys:
        # "data", "axes", "metadata", "original_metadata", "mapping"
        flat_hspy_meta = fd.FlatDict(obj["metadata"], "/")
        flat_orig_meta = fd.FlatDict(obj["original_metadata"], "/")
        # dims = get_axes_dims(obj["axes"])
        # units = get_axes_units(obj["axes"])
        if "General/title" not in flat_hspy_meta:
            return template
        # TODO::use implementation from Velox logic
        return template

    # template[f"{trg}/PROCESS[process]/source/type"] = "file"
    # template[f"{trg}/PROCESS[process]/source/path"] = self.file_path
    # template[f"{trg}/PROCESS[process]/source/checksum"] = self.file_path_sha256
    # template[f"{trg}/PROCESS[process]/source/algorithm"] = DEFAULT_CHECKSUM_ALGORITHM
