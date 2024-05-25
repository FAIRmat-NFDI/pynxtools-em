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
        self.parse_mtex_config(template)
        self.parse_various(template)
        self.parse_roi_default_plot(template)
        self.parse_phases(template)
        self.parse_conventions(template)
        return template

    def parse_mtex_config(self, template: dict) -> dict:
        """Parse MTex content."""
        print("Parse MTex content...")
        # with h5py.File(self.file_name, "r") as h5r:
        #     src = "/entry1/roi1/ebsd/indexing1/mtex"
        #     trg = f"/ENTRY[entry{self.entry_id}]/ebsd/indexing/roi1/mtex"
        # machine off a dictionary
        return template

    def parse_various(self, template: dict) -> dict:
        """Parse various quantities."""
        print("Parse various...")
        with h5py.File(self.file_path, "r") as h5r:
            src = "/entry1/roi1/ebsd/indexing1"
            trg = f"/ENTRY[entry{self.entry_id}]/ROI[roi1]/ebsd/indexing"
            if f"{src}" not in h5r:
                return template
            grp = h5r[f"{src}"]
            if "NX_class" in grp.attrs:
                template[f"{trg}/@NX_class"] = grp.attrs["NX_class"]
            for dst_name in ["indexing_rate", "number_of_scan_points"]:
                if f"{src}/{dst_name}" in h5r:
                    dst = h5r[f"{src}/{dst_name}"]
                    template[f"{trg}/{dst_name}"] = dst
                    if "units" in dst.attrs:
                        template[f"{trg}/{dst_name}/@units"] = dst.attrs["units"]
        return template

    def parse_roi_default_plot(self, template: dict) -> dict:
        """Parse data for the region-of-interest default plot."""
        print("Parse ROI default plot...")
        with h5py.File(self.file_path, "r") as h5r:
            # by construction from MTex entry always named entry1
            # MTex HDF5 file uses formatting from matching that of NXem_ebsd
            # ideally self.hfive_deep_copy(h5r, src, trg, template) at some point
            # but template uses NeXus template path names
            # and HDF5 src has HDF5 instance names
            src = "/entry1/roi1/ebsd/indexing1/roi"
            trg = f"/ENTRY[entry{self.entry_id}]/ROI[roi1]/ebsd/indexing"
            if f"{src}" not in h5r:
                return template
            grp = h5r[f"{src}"]
            attrs = ["NX_class", "axes", "axis_x_indices", "axis_y_indices", "signal"]
            for attr_name in attrs:
                if attr_name in grp.attrs:
                    template[f"{trg}/@{attr_name}"] = grp.attrs[attr_name]
            for dst_name in ["axis_x", "axis_y", "data"]:
                if f"{src}/{dst_name}" in h5r:
                    dst = h5r[f"{src}/{dst_name}"]
                    template[f"{trg}/{dst_name}"] = dst
                    attrs = [
                        "CLASS",
                        "IMAGE_VERSION",
                        "SUBCLASS_VERSION",
                        "long_name",
                        "units",
                    ]
                    for attr_name in attrs:
                        if attr_name in dst.attrs:
                            template[f"{trg}/{dst_name}/@{attr_name}"] = dst.attrs[
                                attr_name
                            ]
            for dst_name in ["description", "title"]:
                if f"{src}/{dst_name}" in h5r:
                    template[f"{trg}/{dst_name}"] = h5r[f"{src}/{dst_name}"]
        return template

    def parse_phases(self, template: dict) -> dict:
        """Parse data for the region-of-interest default plot."""
        print("Parse phases...")
        with h5py.File(self.file_path, "r") as h5r:
            src = "/entry1/roi1/ebsd/indexing1"
            trg = f"/ENTRY[entry{self.entry_id}]/ROI[roi1]/ebsd/indexing/phaseID"
            if f"{src}" not in h5r:
                return template
            for grp_name in h5r[f"{src}"]:
                if re.match("phase[0-9]+", grp_name) is None:
                    continue
                grp = h5r[f"{src}/{grp_name}"]
                if "NX_class" in grp.attrs:
                    template[f"{trg}[{grp_name}]/@NX_class"] = grp.attrs["NX_class"]

                for dst_name in [
                    "number_of_scan_points",
                    "phase_identifier",
                    "unit_cell_abc",
                    "unit_cell_alphabetagamma",
                ]:
                    if f"{src}/{grp_name}/{dst_name}" in h5r:
                        dst = h5r[f"{src}/{grp_name}/{dst_name}"]
                        template[f"{trg}[{grp_name}]/{dst_name}"] = dst
                        if "units" in dst.attrs:
                            template[f"{trg}[{grp_name}]/{dst_name}/@units"] = (
                                dst.attrs["units"]
                            )

                for dst_name in ["phase_name", "point_group"]:
                    if f"{src}/{grp_name}/{dst_name}" in h5r:
                        template[f"{trg}[{grp_name}]/{dst_name}"] = h5r[
                            f"{src}/{grp_name}/{dst_name}"
                        ]

                self.parse_phase_ipf(h5r, grp_name, template)
        return template

    def parse_phase_ipf(self, h5r, phase: str, template: dict) -> dict:
        for ipfid in [1, 2, 3]:  # by default MTex reports three IPFs
            src = f"/entry1/roi1/ebsd/indexing1/{phase}"
            trg = f"/ENTRY[entry{self.entry_id}]/ROI[roi1]/ebsd/indexing/phaseID[{phase}]/ipfID[ipf{ipfid}]"
            if f"{src}/projection_direction" in h5r:
                template[f"{trg}/projection_direction"] = h5r[
                    f"{src}/projection_direction"
                ]
            for nxdata in ["legend", "map"]:
                if f"{src}/{nxdata}" in h5r:
                    grp = h5r[f"{src}/{nxdata}"]
                    attrs = [
                        "NX_class",
                        "axes",
                        "axis_x_indices",
                        "axis_y_indices",
                        "signal",
                    ]
                    for attr_name in attrs:
                        if attr_name in grp.attrs:
                            template[f"{trg}/@{attr_name}"] = grp.attrs[attr_name]
                    for dst_name in ["axis_x", "axis_y", "data"]:
                        if f"{src}/{nxdata}/{dst_name}" in h5r:
                            dst = h5r[f"{src}/{nxdata}/{dst_name}"]
                            template[f"{trg}/{nxdata}/{dst_name}"] = dst
                            attrs = [
                                "CLASS",
                                "IMAGE_VERSION",
                                "SUBCLASS_VERSION",
                                "long_name",
                                "units",
                            ]
                            for attr_name in attrs:
                                if attr_name in dst.attrs:
                                    template[
                                        f"{trg}/{nxdata}/{dst_name}/@{attr_name}"
                                    ] = dst.attrs[attr_name]
                    if f"{src}/{nxdata}/title" in h5r:
                        template[f"{trg}/{nxdata}/title"] = h5r[f"{src}/{nxdata}/title"]
        return template

    def parse_conventions(self, template: dict) -> dict:
        """Add conventions made for EBSD setup and geometry."""
        # TODO::parse these from the project table
        return template
