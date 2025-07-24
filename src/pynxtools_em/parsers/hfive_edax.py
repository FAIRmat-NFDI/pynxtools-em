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
"""Parser mapping concepts and content from EDAX/AMETEK *.oh5/*.h5 (OIM Analysis) files on NXem."""

from typing import Dict

import h5py
import numpy as np
from diffpy.structure import Lattice, Structure

from pynxtools_em.examples.ebsd_database import ASSUME_PHASE_NAME_TO_SPACE_GROUP
from pynxtools_em.methods.ebsd import (
    HEXAGONAL_FLAT_TOP_TILING,
    SQUARE_TILING,
    EbsdPointCloud,
    ebsd_roi_overview,
    ebsd_roi_phase_ipf,
    has_hfive_magic_header,
)
from pynxtools_em.parsers.hfive_base import HdfFiveBaseParser
from pynxtools_em.utils.get_checksum import (
    DEFAULT_CHECKSUM_ALGORITHM,
    get_sha256_of_file_content,
)
from pynxtools_em.utils.hfive_utils import (
    EULER_SPACE_SYMMETRY,
    read_first_scalar,
    read_strings,
)
from pynxtools_em.utils.pint_custom_unit_registry import ureg


class HdfFiveEdaxOimAnalysisParser(HdfFiveBaseParser):
    """Read EDAX (O)H5"""

    def __init__(self, file_path: str = "", entry_id: int = 1, verbose: bool = True):
        if file_path:
            self.file_path = file_path
        self.id_mgn: Dict[str, int] = {
            "entry_id": entry_id if entry_id > 0 else 0,
            "roi_id": 1,
        }
        self.verbose = verbose
        self.prfx = ""  # template path handling
        self.version: Dict = {  # Dict[str, Dict[str, List[str]]
            "trg": {
                "tech_partner": ["EDAX"],
                "schema_name": ["H5"],
                "schema_version": [
                    "OIM Analysis 8.6.0050 x64 [18 Oct 2021]",
                    "OIM Analysis 8.5.1002 x64 [07-17-20]",
                ],
                "writer_name": ["OIM Analysis"],
                "writer_version": [
                    "OIM Analysis 8.6.0050 x64 [18 Oct 2021]",
                    "OIM Analysis 8.5.1002 x64 [07-17-20]",
                ],
            },
            "src": {},
        }
        self.supported = False
        self.check_if_supported()
        if not self.supported:
            print(
                f"Parser {self.__class__.__name__} finds no content in {file_path} that it supports"
            )

    def check_if_supported(self):
        """Check if instance matches all constraints to qualify as old EDAX"""
        self.supported = False
        if not has_hfive_magic_header(self.file_path):
            return

        with h5py.File(self.file_path, "r") as h5r:
            for req_field in ["Manufacturer", "Version"]:
                if f"/{req_field}" not in h5r:
                    return

            votes_for_support = 0
            partner = read_strings(h5r["/Manufacturer"][()])
            # for 8.6.0050 but for 8.5.1002 it is a matrix, this is because how strings end up in HDF5 allowed for so much flexibility!
            if partner in self.version["trg"]["tech_partner"]:
                self.version["src"]["tech_partner"] = partner
                votes_for_support += 1
            sversion = read_strings(h5r["/Version"][()])
            if sversion in self.version["trg"]["schema_version"]:
                self.version["src"]["schema_version"] = sversion
                votes_for_support += 1

            if votes_for_support == 2:
                for keyword in ["schema_name", "writer_name", "writer_version"]:
                    self.version["src"][keyword] = self.version["trg"][keyword]
                    self.supported = True

    def parse(self, template: dict) -> dict:
        """Read and normalize away EDAX-specific formatting with an equivalent in NXem."""
        if self.supported:
            with open(self.file_path, "rb", 0) as fp:
                self.file_path_sha256 = get_sha256_of_file_content(fp)
            print(
                f"Parsing {self.file_path} EDAX O(H5) with SHA256 {self.file_path_sha256} ..."
            )
            with h5py.File(f"{self.file_path}", "r") as h5r:
                grp_names = list(h5r["/"])
                for grp_name in grp_names:
                    if grp_name not in ["Version", "Manufacturer"]:
                        self.prfx = f"/{grp_name}"
                        self.ebsd = EbsdPointCloud()
                        self.parse_and_normalize_group_ebsd_header(h5r)
                        self.parse_and_normalize_group_ebsd_phases(h5r)
                        self.parse_and_normalize_group_ebsd_data(h5r)
                        ebsd_roi_overview(self.ebsd, self.id_mgn, template)
                        ebsd_roi_phase_ipf(self.ebsd, self.id_mgn, template)
                        self.id_mgn["roi_id"] += 1
                        self.ebsd = EbsdPointCloud()
                    # TODO::parsing of information from other imaging modalities
        return template

    def parse_and_normalize_group_ebsd_header(self, fp):
        grp_name = f"{self.prfx}/EBSD/Header"
        if f"{grp_name}" not in fp:
            print(f"Unable to parse {grp_name} !")
            self.ebsd = EbsdPointCloud()
            return

        n_pts = 0
        for req_field in ["Grid Type", "Step X", "Step Y", "nColumns", "nRows"]:
            if f"{grp_name}/{req_field}" not in fp:
                print(f"Unable to parse {grp_name}/{req_field} !")
                self.ebsd = EbsdPointCloud()
                return

        self.ebsd.dimensionality = 2
        grid_type = read_strings(fp[f"{grp_name}/Grid Type"][()])
        if grid_type == "HexGrid":
            self.ebsd.grid_type = HEXAGONAL_FLAT_TOP_TILING
        elif grid_type == "SqrGrid":
            self.ebsd.grid_type = SQUARE_TILING
        else:
            print(f"Unable to parse {grp_name}/Grid Type !")
            self.ebsd = EbsdPointCloud()
            return
        # the next two lines encode the typical assumption that is not reported in tech partner file!
        self.ebsd.s["x"] = ureg.Quantity(
            read_first_scalar(fp[f"{grp_name}/Step X"]), ureg.micrometer
        )
        self.ebsd.s["y"] = ureg.Quantity(
            read_first_scalar(fp[f"{grp_name}/Step Y"]), ureg.micrometer
        )
        # "um", "µm" TODO::always micron?
        self.ebsd.n["x"] = read_first_scalar(fp[f"{grp_name}/nColumns"])
        self.ebsd.n["y"] = read_first_scalar(fp[f"{grp_name}/nRows"])
        # TODO::different version store the same concept with the same path name with different shape
        # the read_first_scalar is not an optimal solution, in the future all reads from
        # HDF5 should check for the shape instead
        # TODO::check that all data are consistent

    def parse_and_normalize_group_ebsd_phases(self, fp):
        grp_name = f"{self.prfx}/EBSD/Header/Phase"
        # Phases, contains a subgroup for each phase where the name
        # of each subgroup is the index of the phase starting at 1.
        if f"{grp_name}" not in fp:
            print(f"Unable to parse {grp_name} !")
            self.ebsd = EbsdPointCloud()
            return

        phase_ids = sorted(list(fp[f"{grp_name}"]), key=int)
        self.ebsd.phase = []
        self.ebsd.space_group = []
        self.ebsd.phases = {}
        for phase_id in phase_ids:
            if phase_id.isdigit():
                phase_idx = int(phase_id)
                self.ebsd.phases[phase_idx] = {}
                sub_grp_name = f"{grp_name}/{phase_id}"
                # Name
                if f"{sub_grp_name}/MaterialName" in fp:
                    phase_name = read_strings(fp[f"{sub_grp_name}/MaterialName"][0])
                    self.ebsd.phases[phase_idx]["phase_name"] = phase_name
                else:
                    print(f"Unable to parse {sub_grp_name}/MaterialName !")
                    self.ebsd = EbsdPointCloud()
                    return

                # Reference not available only Info but this can be empty
                self.ebsd.phases[phase_idx]["reference"] = "n/a"

                for req_field in ["a", "b", "c", "alpha", "beta", "gamma"]:
                    if f"{sub_grp_name}/Lattice Constant {req_field}" not in fp:
                        print(f"Unable to parse ../Lattice Constant {req_field} !")
                        self.ebsd = EbsdPointCloud()
                        return
                abc = np.asarray(
                    (
                        fp[f"{sub_grp_name}/Lattice Constant a"][()],
                        fp[f"{sub_grp_name}/Lattice Constant b"][()],
                        fp[f"{sub_grp_name}/Lattice Constant c"][()],
                    ),
                    dtype=np.float32,
                ).flatten()
                angles = np.asarray(
                    (
                        fp[f"{sub_grp_name}/Lattice Constant alpha"][()],
                        fp[f"{sub_grp_name}/Lattice Constant beta"][()],
                        fp[f"{sub_grp_name}/Lattice Constant gamma"][()],
                    ),
                    dtype=np.float32,
                ).flatten()
                latt = Lattice(
                    abc[0],
                    abc[1],
                    abc[2],
                    angles[0],
                    angles[1],
                    angles[2],
                )
                # TODO::available examples support reporting in angstroem and degree
                self.ebsd.phases[phase_idx]["a_b_c"] = ureg.Quantity(abc, ureg.angstrom)
                self.ebsd.phases[phase_idx]["alpha_beta_gamma"] = ureg.Quantity(
                    angles, ureg.degree
                ).to(ureg.radian)

                # Space Group not stored, only laue group, point group and symmetry
                # https://doi.org/10.1107/S1600576718012724 is a relevant read here
                # problematic because mapping is not bijective!
                # if you know the space group we know laue and point group and symmetry
                # but the opposite direction leaves room for ambiguities
                spc_grp = None
                if phase_name in ASSUME_PHASE_NAME_TO_SPACE_GROUP:
                    spc_grp = ASSUME_PHASE_NAME_TO_SPACE_GROUP[phase_name]
                else:
                    print(f"Unknown space group for phase_name {phase_name}!")
                    self.ebsd = EbsdPointCloud()
                    return
                self.ebsd.phases[phase_idx]["space_group"] = spc_grp

                if len(self.ebsd.space_group) > 0:
                    self.ebsd.space_group.append(spc_grp)
                else:
                    self.ebsd.space_group = [spc_grp]

                strct = Structure(title=phase_name, atoms=None, lattice=latt)
                if len(self.ebsd.phase) > 0:
                    self.ebsd.phase.append(strct)
                else:
                    self.ebsd.phase = [strct]

    def parse_and_normalize_group_ebsd_data(self, fp):
        grp_name = f"{self.prfx}/EBSD/Data"
        if f"{grp_name}" not in fp:
            print(f"Unable to parse {grp_name} !")
            self.ebsd = EbsdPointCloud()

        for req_field in [
            "CI",
            "Phase",
            "Phi1",
            "Phi",
            "Phi2",
            "X Position",
            "Y Position",
        ]:
            if f"{grp_name}/{req_field}" not in fp:
                print(f"Unable to parse {grp_name}/{req_field} !")
                self.ebsd = EbsdPointCloud()
                return

        n_pts = self.ebsd.n["x"] * self.ebsd.n["y"]
        self.ebsd.euler = np.empty((n_pts, 3), np.float32)
        self.ebsd.euler.fill(np.nan)
        # TODO::available examples support that rumour that in EDAX file sometimes values
        # of Euler angle triplets are larger than mathematically possible
        # unfortunately there is no confirmation from EDAX what is the reported unit and
        # normalization for each software version, TODO::here rad is assumed but then values
        # as large as 12.... should not be possible
        # TODO::there has to be a mechanism which treats these dirty scan points!
        for idx, dim in enumerate(["Phi1", "Phi", "Phi2"]):
            self.ebsd.euler[:, idx] = np.asarray(fp[f"{grp_name}/{dim}"][:], np.float32)
            here = np.where(self.ebsd.euler[:, idx] < 0.0)
            self.ebsd.euler[here, idx] += EULER_SPACE_SYMMETRY[idx].magnitude
        self.ebsd.euler = ureg.Quantity(self.ebsd.euler, ureg.radian)
        # TODO::seems to be the situation in the example but there is no documentation

        # given no official EDAX OimAnalysis spec we cannot define for sure if
        # phase_id == 0 means just all was indexed with the first/zeroth phase or nothing
        # was indexed, here we assume it means all indexed with first phase
        # and we assume EDAX uses -1 for notIndexed, this assumption is also
        # substantiated by the situation in the hfive_apex parser
        if np.all(fp[f"{grp_name}/Phase"][:] == 0):
            self.ebsd.phase_id = np.zeros((n_pts,), np.int32) + 1
        else:
            self.ebsd.phase_id = np.asarray(fp[f"{grp_name}/Phase"][:], np.int32)
        # TODO::mark scan points as dirty
        # the line below shows an example how this could be achieved
        # is_dirty = np.zeros((n_pts,), bool)
        # for column_id in [0, 1, 2]:
        #    is_dirty = is_dirty & np.abs(self.ebsd.euler[:, column_id]) > EULER_SPACE_SYMMETRY
        # print(f"Found {np.sum(is_dirty)} scan points which are marked now as dirty!")
        # self.ebsd.phase_id[is_dirty] = 0

        # promoting int8 to int32 no problem
        self.ebsd.descr_type = "confidence_index"
        self.ebsd.descr_value = ureg.Quantity(
            np.asarray(fp[f"{grp_name}/CI"][:], np.float32)
        )
        # normalize pixel coordinates to physical positions even though the origin can still dangle somewhere
        # expected is order on x is first all possible x values while y == 0
        # followed by as many copies of this linear sequence for each y increment
        # tricky situation is that for one version pixel coordinates while in another case
        # calibrated e.g. micron coordinates are reported that is in the first case px needs
        # multiplication with step size in the other one must not multiple with step size
        # as the step size has already been accounted for by the tech partner when writing!
        if self.version["src"]["schema_version"] in [
            "OIM Analysis 8.5.1002 x64 [07-17-20]"
        ]:
            print(
                f"{self.version['src']['schema_version']}, tech partner accounted for calibration"
            )
            if self.ebsd.grid_type != SQUARE_TILING:
                print(
                    f"WARNING: Check carefully correct interpretation of scan_point coords!"
                )
            for dim in ["X", "Y"]:
                self.ebsd.pos[dim.lower()] = ureg.Quantity(
                    np.asarray(fp[f"{grp_name}/{dim} Position"][:], np.float32),
                    ureg.micrometer,
                )
        else:
            print(
                f"{self.version['src']['schema_version']}, parser has to do the calibration"
            )
            if self.ebsd.grid_type != SQUARE_TILING:
                print(
                    f"WARNING: Check carefully correct interpretation of scan_point coords!"
                )
            for dim in ["X", "Y"]:
                self.ebsd.pos[dim.lower()] = ureg.Quantity(
                    np.asarray(
                        fp[f"{grp_name}/{dim} Position"][:]
                        * self.ebsd.s[dim.lower()].magnitude,
                        dtype=np.float32,
                    ),
                    ureg.micrometer,
                )
        # despite differences in reported calibrations the scan_point_{dim} arrays are
        # already provided by the tech partner as tile and repeat coordinates
