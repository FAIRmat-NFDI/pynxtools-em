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
"""Parser mapping concepts and content from Oxford Instruments *.h5oina files on NXem."""

import mmap
from typing import Dict

import h5py
import numpy as np
from diffpy.structure import Lattice, Structure
from pynxtools_em.examples.ebsd_database import (
    FLIGHT_PLAN,
    REGULAR_TILING,
    SQUARE_TILING,
)
from pynxtools_em.methods.ebsd import (
    ebsd_roi_overview,
    ebsd_roi_phase_ipf,
    has_hfive_magic_header,
)
from pynxtools_em.parsers.hfive_base import HdfFiveBaseParser
from pynxtools_em.utils.hfive_utils import apply_euler_space_symmetry, read_strings
from pynxtools_em.utils.pint_custom_unit_registry import ureg


class HdfFiveOxfordInstrumentsParser(HdfFiveBaseParser):
    """Overwrite constructor of hfive_base reader"""

    def __init__(self, file_path: str = "", entry_id: int = 1, verbose: bool = False):
        super().__init__(file_path)
        self.id_mgn: Dict[str, int] = {"entry_id": entry_id, "roi_id": 1}
        self.verbose = verbose
        self.prfx = None  # template path handling
        self.tmp = {}
        self.version: Dict = {  # Dict[str, Dict[str, List[str]]]
            "trg": {
                "tech_partner": ["Oxford Instruments"],
                "schema_name": ["H5OINA"],
                "schema_version": ["2.0", "3.0", "4.0", "5.0"],
                "writer_name": ["AZTec"],
                "writer_version": [
                    "4.4.7495.1",
                    "5.0.7643.1",
                    "5.1.7829.1",
                    "6.0.8014.1",
                    "6.0.8196.1",
                    "6.1.8451.1",
                ],
            },
            "src": {
                "tech_partner": None,
                "schema_name": None,
                "schema_version": None,
                "writer_name": None,
                "writer_version": None,
            },
        }
        self.supported = False
        if self.is_hdf:
            self.check_if_supported()
        if not self.supported:
            print(
                f"Parser {self.__class__.__name__} finds no content in {file_path} that it supports"
            )

    def check_if_supported(self):
        """Check if instance matches all constraints to qualify as supported H5OINA"""
        self.supported = False
        if not has_hfive_magic_header(self.file_path):
            return

        with h5py.File(self.file_path, "r") as h5r:
            req_fields = ["Manufacturer", "Software Version", "Format Version"]
            for req_field in req_fields:
                if f"/{req_field}" not in h5r:
                    return

            votes_for_support = 0
            partner = read_strings(h5r["/Manufacturer"][()])
            if partner in self.version["trg"]["tech_partner"]:
                self.version["src"]["tech_partner"] = partner
                votes_for_support += 1
            # only because we know (thanks to Philippe Pinard who wrote the H5OINA writer) that different
            # writer versions should implement the different HDF version correctly we can lift the
            # constraint on the writer_version for which we had examples available
            wversion = read_strings(h5r["/Software Version"][()])
            if wversion in self.version["trg"]["writer_version"]:
                self.version["src"]["writer_version"] = wversion
                votes_for_support += 1
            sversion = read_strings(h5r["/Format Version"][()])
            if sversion in self.version["trg"]["schema_version"]:
                self.version["src"]["schema_version"] = sversion
                votes_for_support += 1

            if votes_for_support == 3:
                self.version["src"]["schema_name"] = self.version["trg"]["schema_name"][
                    0
                ]
                self.version["src"]["writer_name"] = self.version["trg"]["writer_name"][
                    0
                ]
                self.supported = True

    def parse(self, template: dict) -> dict:
        """Read and normalize away Oxford-specific formatting with an equivalent in NXem."""
        if self.supported:
            print(f"Parsing via Oxford Instrument HDF5/H5OINA parser...")
            with h5py.File(f"{self.file_path}", "r") as h5r:
                cache_id = 1
                slice_ids = sorted(list(h5r["/"]))
                for slice_id in slice_ids:
                    if slice_id == "1" and f"/{slice_id}/EBSD" in h5r:
                        # non-negative int, parse for now only the first slice
                        self.prfx = f"/{slice_id}"
                        ckey = self.init_cache(f"ebsd{cache_id}")
                        self.parse_and_normalize_slice_ebsd_header(h5r, ckey)
                        self.parse_and_normalize_slice_ebsd_phases(h5r, ckey)
                        self.parse_and_normalize_slice_ebsd_data(h5r, ckey)
                        ebsd_roi_overview(self.tmp[ckey], self.id_mgn, template)
                        ebsd_roi_phase_ipf(self.tmp[ckey], self.id_mgn, template)
                        self.clear_cache(ckey)

                    # TODO:Vitesh example
        return template

    def parse_and_normalize_slice_ebsd_header(self, fp, ckey: str):
        grp_name = f"{self.prfx}/EBSD/Header"
        if f"{grp_name}" not in fp:
            print(f"Unable to parse {grp_name} !")
            self.tmp[ckey] = {}
            return

        # TODO::check if Oxford Instruments always uses SquareGrid like assumed here
        self.tmp[ckey]["dimensionality"] = 2
        self.tmp[ckey]["grid_type"] = SQUARE_TILING
        # the next two lines encode the typical assumption that is not reported in tech partner file!
        self.tmp[ckey]["tiling"] = REGULAR_TILING
        self.tmp[ckey]["flight_plan"] = FLIGHT_PLAN

        dims = ["X", "Y"]
        for dim in dims:
            for req_field in [f"{dim} Cells", f"{dim} Step"]:
                if f"{grp_name}/{req_field}" not in fp:
                    print(f"Unable to parse {grp_name}/{req_field} !")
                    self.tmp[ckey] = {}
                    return
        # X Cells, yes, H5T_NATIVE_INT32, (1, 1), Map: Width in pixels, Line scan: Length in pixels.
        # Y Cells, yes, H5T_NATIVE_INT32, (1, 1), Map: Height in pixels. Line scan: Always set to 1.
        # X Step, yes, H5T_NATIVE_FLOAT, (1, 1), Map: Step size along x-axis in micrometers.
        #   Line scan: step size along the line scan in micrometers.
        # Y Step, yes, H5T_NATIVE_FLOAT, (1, 1), Map: Step size along y-axis in micrometers.
        #   Line scan: Always set to 0.
        for dim in dims:
            self.tmp[ckey][f"n_{dim.lower()}"] = fp[f"{grp_name}/{dim} Cells"][0]
            if read_strings(fp[f"{grp_name}/{dim} Step"].attrs["Unit"]) == "um":
                self.tmp[ckey][f"s_{dim.lower()}"] = ureg.Quantity(
                    fp[f"{grp_name}/{dim} Step"][0], ureg.micrometer
                )
            else:
                print(f"Unexpected {dim} Step Unit attribute !")
                self.tmp[ckey] = {}
                return
        # TODO::check that all data in the self.oina are consistent

    def parse_and_normalize_slice_ebsd_phases(self, fp, ckey: str):
        """Parse EBSD header section for specific slice."""
        grp_name = f"{self.prfx}/EBSD/Header/Phases"
        if f"{grp_name}" not in fp:
            print(f"Unable to parse {grp_name} !")
            self.tmp[ckey] = {}
            return

        # Phases, yes, contains a subgroup for each phase where the name
        # of each subgroup is the index of the phase starting at 1.
        phase_ids = sorted(list(fp[f"{grp_name}"]), key=int)
        self.tmp[ckey]["phase"] = []
        self.tmp[ckey]["space_group"] = []
        self.tmp[ckey]["phases"] = {}
        for phase_id in phase_ids:
            if not phase_id.isdigit():
                continue
            self.tmp[ckey]["phases"][int(phase_id)] = {}
            sub_grp_name = f"/{grp_name}/{phase_id}"

            req_fields = [
                "Phase Name",
                "Reference",
                "Lattice Angles",
                "Lattice Dimensions",
                "Space Group",
            ]
            for req_field in req_fields:
                if f"{sub_grp_name}/{req_field}" not in fp:
                    print(f"Unable to parse {sub_grp_name}/{req_field} !")
                    self.tmp[ckey] = {}
                    return

            # Phase Name, yes, H5T_STRING, (1, 1)
            phase_name = read_strings(fp[f"{sub_grp_name}/Phase Name"][()])
            self.tmp[ckey]["phases"][int(phase_id)]["phase_name"] = phase_name

            # Reference, yes, H5T_STRING, (1, 1), Changed in version 2.0 to mandatory
            self.tmp[ckey]["phases"][int(phase_id)]["reference"] = read_strings(
                fp[f"{sub_grp_name}/Reference"][()]
            )

            # Lattice Angles, yes, H5T_NATIVE_FLOAT, (1, 3), Three columns for the alpha, beta and gamma angles in radians
            if (
                read_strings(fp[f"{sub_grp_name}/Lattice Angles"].attrs["Unit"])
                == "rad"
            ):
                alpha_beta_gamma = np.asarray(
                    fp[f"{sub_grp_name}/Lattice Angles"][:].flatten()
                )
                self.tmp[ckey]["phases"][int(phase_id)]["alpha_beta_gamma"] = (
                    ureg.Quantity(alpha_beta_gamma, ureg.radian)
                )
            else:
                print(f"Unexpected case that Lattice Angles are not reported in rad !")
                self.tmp[ckey] = {}
                return
            # Lattice Dimensions, yes, H5T_NATIVE_FLOAT, (1, 3), Three columns for a, b and c dimensions in Angstroms
            if (
                read_strings(fp[f"{sub_grp_name}/Lattice Dimensions"].attrs["Unit"])
                == "angstrom"
            ):
                a_b_c = np.asarray(
                    fp[f"{sub_grp_name}/Lattice Dimensions"][:].flatten()
                )
                self.tmp[ckey]["phases"][int(phase_id)]["a_b_c"] = ureg.Quantity(
                    a_b_c, ureg.angstrom
                )
            else:
                print(
                    f"Unexpected case that Lattice Dimensions are not reported in angstrom !"
                )
                self.tmp[ckey] = {}
                return

            # Space Group, no, H5T_NATIVE_INT32, (1, 1), Space group index.
            # The attribute Symbol contains the string representation, for example P m -3 m.
            space_group = int(fp[f"{sub_grp_name}/Space Group"][0])
            self.tmp[ckey]["phases"][int(phase_id)]["space_group"] = space_group
            if len(self.tmp[ckey]["space_group"]) > 0:
                self.tmp[ckey]["space_group"].append(space_group)
            else:
                self.tmp[ckey]["space_group"] = [space_group]

            if len(self.tmp[ckey]["phase"]) > 0:
                self.tmp[ckey]["phase"].append(
                    Structure(
                        title=phase_name,
                        atoms=None,
                        lattice=Lattice(
                            a_b_c[0],
                            a_b_c[1],
                            a_b_c[2],
                            alpha_beta_gamma[0],
                            alpha_beta_gamma[1],
                            alpha_beta_gamma[2],
                        ),
                    )
                )
            else:
                self.tmp[ckey]["phase"] = [
                    Structure(
                        title=phase_name,
                        atoms=None,
                        lattice=Lattice(
                            a_b_c[0],
                            a_b_c[1],
                            a_b_c[2],
                            alpha_beta_gamma[0],
                            alpha_beta_gamma[1],
                            alpha_beta_gamma[2],
                        ),
                    )
                ]

    def parse_and_normalize_slice_ebsd_data(self, fp, ckey: str):
        # https://github.com/oinanoanalysis/h5oina/blob/master/H5OINAFile.md
        grp_name = f"{self.prfx}/EBSD/Data"
        if f"{grp_name}" not in fp:
            raise ValueError(f"Unable to parse {grp_name} !")

        req_fields = ["Euler", "Phase", "X", "Y", "Band Contrast"]
        for req_field in req_fields:
            if f"{grp_name}/{req_field}" not in fp:
                print(f"Unable to parse {grp_name}/{req_field} !")
                self.tmp[ckey] = {}
                return

        # Euler, yes, H5T_NATIVE_FLOAT, (size, 3), Orientation of Crystal (CS2) to Sample-Surface (CS1).
        if read_strings(fp[f"{grp_name}/Euler"].attrs["Unit"]) == "rad":
            self.tmp[ckey]["euler"] = ureg.Quantity(
                np.asarray(fp[f"{grp_name}/Euler"]), ureg.radian
            )
        else:
            print(f"Unexpected case that Euler angle are not reported in rad !")
            self.tmp[ckey] = {}
            return

        self.tmp[ckey]["euler"] = apply_euler_space_symmetry(self.tmp[ckey]["euler"])

        # no normalization needed, also in NXem the null model notIndexed is phase_identifier 0
        self.tmp[ckey]["phase_id"] = np.asarray(fp[f"{grp_name}/Phase"], np.int32)

        # normalize pixel coordinates to physical positions even though the origin can still dangle somewhere
        # expected is order on x is first all possible x values while y == 0
        # followed by as many copies of this linear sequence for each y increment
        # no action needed Oxford reports already the pixel coordinate multiplied by step
        if self.tmp[ckey]["grid_type"] != SQUARE_TILING:
            print(
                f"WARNING: Check carefully correct interpretation of scan_point coords!"
            )
        # Phase, yes, H5T_NATIVE_INT32, (size, 1), Index of phase, 0 if not indexed
        # X, no, H5T_NATIVE_FLOAT, (size, 1), X position of each pixel in micrometers (origin: top left corner)
        # Y, no, H5T_NATIVE_FLOAT, (size, 1), Y position of each pixel in micrometers (origin: top left corner)
        # Band Contrast, no, H5T_NATIVE_INT32, (size, 1)
        # for Oxford instrument this is already the required tile and repeated array of shape (size, 1)
        # inconsistency f32 in file although specification states float
        dims = ["X", "Y"]
        for dim in dims:
            self.tmp[ckey][f"scan_point_{dim.lower()}"] = np.asarray(
                fp[f"{grp_name}/{dim}"]
            )

        self.tmp[ckey]["bc"] = np.asarray(fp[f"{grp_name}/Band Contrast"], np.int32)
        # inconsistency uint8 in file although specification states should be int32
        # promoting uint8 to int32 no problem
