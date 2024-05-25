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
"""(Sub-)parser mapping concepts and content from *.nxs.mtex files on NXem."""

# *.nxs.mtex is a specific semantic file formatting for storing processing results obtained
# with the MTex texture toolbox for Matlab into an HDF5 file. The format uses NeXus
# base classes such as NXem_ebsd, NXms_ipf, for details see
# https://fairmat-nfdi.github.io/nexus_definitions/classes/contributed_definitions/em-structure.html#em-structure

import re
import h5py
import mmap
from ase.data import chemical_symbols
from pynxtools_em.examples.ebsd_database import (
    PHASE_NAME_TO_CONCEPT,
    CONCEPT_TO_ATOM_TYPES,
)


class NxEmNxsMTexSubParser:
    """Map content from *.nxs.mtex files on an instance of NXem."""

    def __init__(self, entry_id: int = 1, file_path: str = "", verbose: bool = False):
        if entry_id > 0:
            self.entry_id = entry_id
        else:
            self.entry_id = 1
        self.file_path = file_path
        self.supported = False
        self.verbose = verbose

    def check_if_mtex_nxs(self):
        """Check if content matches expected content."""
        if self.file_path is None or not self.file_path.endswith(".mtex.nxs"):
            return
        with open(self.file_path, "rb", 0) as file:
            s = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)
            magic = s.read(4)
            if magic != b"\x89HDF":
                return
        # TODO add code which checks for available content
        # the file written out by MTex/Matlab this file is already preformatted for NeXus
        # #######
        self.supported = True

    def parse(self, template: dict) -> dict:
        """Pass because for *.nxs.mtex all data are already in the copy of the output."""
        if not self.supported:
            return template
        self.parse_roi(template)
        self.parse_ipf(template)
        self.parse_atom_types(template)
        self.parse_conventions(template)
        return template

    def parse_roi(self, template: dict) -> dict:
        """Copy ROI-related content."""
        return template

    def parse_ipf(self, template: dict) -> dict:
        """Copy IPF-related content."""
        return template

    def parse_atom_types(self, template: dict) -> dict:
        """Add phase name surplus other data to the copy of the *.nxs.mtex instance."""
        atom_types = set()
        with h5py.File(self.file_path, "r") as h5r:
            trg = f"/entry{self.entry_id}/roi1/ebsd/indexing"
            if trg in h5r:
                for node_name in h5r[trg]:
                    if re.match("phase[0-9]+", node_name) is None:
                        continue
                    if f"{trg}/{node_name}/phase_name" in h5r:
                        free_text = (
                            h5r[f"{trg}/{node_name}/phase_name"][()]
                            .decode("utf-8")
                            .rstrip(" ")
                            .lstrip(" ")
                        )
                        if free_text in PHASE_NAME_TO_CONCEPT:
                            concept = PHASE_NAME_TO_CONCEPT[free_text]
                            if concept in CONCEPT_TO_ATOM_TYPES:
                                symbols = CONCEPT_TO_ATOM_TYPES[concept].split(";")
                                for symbol in symbols:
                                    if symbol in chemical_symbols[1::]:
                                        atom_types.add(symbol)
        if len(atom_types) > 0:
            template[f"/ENTRY[entry{self.entry_id}]/sample/atom_types"] = ", ".join(
                list(atom_types)
            )
        else:
            template[f"/ENTRY[entry{self.entry_id}]/sample/atom_types"] = ""
        return template

    def parse_conventions(self, template: dict) -> dict:
        """Add conventions made for EBSD setup and geometry."""
        # TODO::parse these from the project table
        return template
