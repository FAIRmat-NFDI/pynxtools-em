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
"""Utility class to analyze which vendor/community files are passed to apm reader."""

from typing import Dict, List, Tuple

import flatdict as fd
import yaml

VALID_FILE_NAME_SUFFIX_CONFIG = [".yaml", ".yml"]
VALID_FILE_NAME_SUFFIX_DATA = [
    ".emd",
    ".dm3",
    ".dm4",
    ".dm5",
    ".tiff",
    ".tif",
    ".zip",
    ".nsproj",
    ".edaxh5",
    ".h5oina",
    ".oh5",
    ".dream3d",
    ".mtex.h5",
    ".h5",
    ".hdf5",
    ".txt",
    ".hdr",
]
# the order of this list is significant to assure that whatever is found first and
# valid will trigger acceptance but avoiding to load one dataset twice e.g.
# if .h5 would be tested before .mtex.h5 the .mtex.h5 qualifies two times if we
# do not break, however, if we do break and test .mtex.h5 first it will be found only
# one time


class EmUseCaseSelector:
    """Decision maker about what needs to be parsed given arbitrary input.

    Users might invoke this dataconverter with arbitrary input, no input, or
    too much input. The UseCaseSelector decide what to do in each case.
    """

    def __init__(self, file_paths: Tuple[str] = None):
        """Initialize the class."""
        self.case: Dict[str, list] = {}
        self.cfg: List[str] = []
        self.eln: List[str] = []
        self.cst: List[Dict[str, str]] = []
        self.dat: List[str] = []
        self.is_valid = False
        self.supported_file_name_suffixes = (
            VALID_FILE_NAME_SUFFIX_CONFIG + VALID_FILE_NAME_SUFFIX_DATA
        )
        print(f"Supported file format suffixes: {self.supported_file_name_suffixes}")
        self.sort_files_by_file_name_suffix(file_paths)
        self.check_validity_of_file_combinations()

    def sort_files_by_file_name_suffix(self, file_paths: Tuple[str] = None):
        """Sort all input-files based on their name suffix to prepare validity check.

        Individual readers have more sophisticated internal check if specific
        format instances are parseable or not and will do their own version checks.
        """
        for suffix in self.supported_file_name_suffixes:
            self.case[suffix] = []
        for fpath in file_paths:
            for suffix in self.supported_file_name_suffixes:
                if (fpath.lower().endswith(suffix)) and (
                    fpath not in self.case[suffix]
                ):
                    self.case[suffix].append(fpath)

    def check_validity_of_file_combinations(self):
        """Check if this combination of types of files is supported."""
        dat_input = 0  # tech-partner relevant (meta)file e.g. HDF5, EMD, ...
        other_input = 0  # generic ELN or Oasis-specific configurations
        for suffix in VALID_FILE_NAME_SUFFIX_DATA:
            if len(self.case[suffix]) > 0:
                dat_input += len(self.case[suffix])
                break
        for suffix in VALID_FILE_NAME_SUFFIX_CONFIG:
            if len(self.case[suffix]) > 0:
                other_input += len(self.case[suffix])

        if 0 <= dat_input <= 2 and 0 <= other_input <= 3:
            self.is_valid = True
            self.dat: List[str] = []
            for suffix in VALID_FILE_NAME_SUFFIX_DATA:
                if len(self.case[suffix]) > 0:
                    self.dat += self.case[suffix]
                    break
            yml: List[str] = []
            for suffix in VALID_FILE_NAME_SUFFIX_CONFIG:
                if len(self.case[suffix]) > 0:
                    yml += self.case[suffix]
            for entry in yml:
                if entry.endswith((".oasis.specific.yaml", ".oasis.specific.yml")):
                    self.cfg += [entry]
                elif entry.endswith(("nxs_eln_data.yaml", "nxs_eln_data.yml")):
                    self.eln += [entry]
                elif entry.endswith(("custom_eln_data.yaml", "custom_eln_data.yml")):
                    with open(entry, "r", encoding="utf-8") as stream:
                        flat_metadata = fd.FlatDict(yaml.safe_load(stream), "/")
                        if "parser" in flat_metadata:
                            self.cst += [
                                {"parser": flat_metadata["parser"], "file": entry}
                            ]
            print(
                f"Oasis local config: {self.cfg}\n"
                f"Oasis ELN: {self.eln}\n"
                f"Custom ELN: {self.cst}\n"
                f"Tech (meta)data: {self.dat}\n"
            )

    def report_workflow(self, template: dict, entry_id: int) -> dict:
        """Initialize the reporting of the workflow."""
        return template
