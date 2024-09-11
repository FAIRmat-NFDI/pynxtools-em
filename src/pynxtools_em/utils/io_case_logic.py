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

VALID_FILE_NAME_SUFFIX_CONFIG = [".yaml", ".yml"]
VALID_FILE_NAME_SUFFIX_DATA = [
    ".emd",
    ".dm3",
    ".dm4",
    ".tiff",
    ".tif",
    ".zip",
    ".nsproj",
    ".edaxh5",
    ".h5",
    ".hdf5",
    ".h5oina",
    ".mtex.h5",
    ".dream3d",
    ".txt",
    ".hdr",
    ".oh5",
]


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
        self.cvn: List[str] = []
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
        for suffix, value in self.case.items():
            if suffix in VALID_FILE_NAME_SUFFIX_DATA:
                dat_input += len(value)
            elif suffix in VALID_FILE_NAME_SUFFIX_CONFIG:
                other_input += len(value)
            else:
                continue
        # print(f"{dat_input}, {other_input}")
        if 0 <= other_input <= 3:
            self.is_valid = True
            self.dat: List[str] = []
            for suffix in VALID_FILE_NAME_SUFFIX_DATA:
                self.dat += self.case[suffix]
            yml: List[str] = []
            for suffix in VALID_FILE_NAME_SUFFIX_CONFIG:
                yml += self.case[suffix]
            for entry in yml:
                if entry.endswith(".oasis.specific.yaml") or entry.endswith(
                    ".oasis.specific.yml"
                ):
                    self.cfg += [entry]
                elif entry.endswith("eln_data.yaml") or entry.endswith("eln_data.yml"):
                    self.eln += [entry]
                elif entry.endswith("conventions.yaml") or entry.endswith(
                    "conventions.yml"
                ):
                    self.cvn += [entry]
            print(
                f"Oasis local config: {self.cfg}\n"
                f"Oasis ELN: {self.eln}\n"
                f"Conventions ELN: {self.cvn}\n"
                f"Tech (meta)data: {self.dat}\n"
            )

    def report_workflow(self, template: dict, entry_id: int) -> dict:
        """Initialize the reporting of the workflow."""
        return template
