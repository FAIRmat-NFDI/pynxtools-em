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
"""Parser mapping concepts and content from community *.h5/*.h5ebsd files on NXem."""

from typing import Dict

import h5py
import numpy as np
from diffpy.structure import Lattice, Structure
from pynxtools_em.examples.ebsd_database import ASSUME_PHASE_NAME_TO_SPACE_GROUP
from pynxtools_em.methods.ebsd import (
    EbsdPointCloud,
    ebsd_roi_overview,
    ebsd_roi_phase_ipf,
    has_hfive_magic_header,
)
from pynxtools_em.parsers.hfive_base import HdfFiveBaseParser
from pynxtools_em.utils.hfive_utils import (
    EBSD_MAP_SPACEGROUP,
    all_equal,
    apply_euler_space_symmetry,
    read_strings,
)
from pynxtools_em.utils.pint_custom_unit_registry import ureg


class HdfFiveEbsdCommunityParser(HdfFiveBaseParser):
    """Read modified H5EBSD (likely from Britton group)"""

    def __init__(self, file_path: str = "", entry_id: int = 1, verbose: bool = False):
        super().__init__(file_path)
        self.id_mgn: Dict[str, int] = {"entry_id": entry_id, "roi_id": 1}
        self.verbose = verbose
        self.prfx = ""  # template path handling
        self.version: Dict = {  # Dict[str, Dict[str, List[str]]]
            "trg": {
                "tech_partner": ["xcdskd"],
                "schema_name": ["H5EBSD"],
                "schema_version": ["0.1"],
                "writer_name": ["not standardized"],
                "writer_version": ["0.1"],
            },
            "src": {},
        }
        self.supported = False
        if self.is_hdf:
            self.check_if_supported()
        else:
            print(
                f"Parser {self.__class__.__name__} finds no content in {file_path} that it supports"
            )

    def check_if_supported(self):
        # check if instance to process matches any of these constraints
        self.supported = False
        if not has_hfive_magic_header(self.file_path):
            return

        with h5py.File(self.file_path, "r") as h5r:
            for req_field in ["Manufacturer", "Version"]:
                if f"/{req_field}" not in h5r:
                    return

            votes_for_support = 0
            partner = read_strings(h5r["/Manufacturer"][()])
            if partner in self.version["trg"]["tech_partner"]:
                self.version["src"]["tech_partner"] = partner
                votes_for_support += 1
            sversion = read_strings(h5r["/Version"][()])
            if sversion in self.version["trg"]["schema_version"]:
                self.version["src"]["schema_version"] = sversion
                votes_for_support += 1

            if self.supported == 2:
                for keyword in ["schema_name", "writer_name", "writer_version"]:
                    self.version["src"][keyword] = self.version["trg"][keyword]
                self.supported = True

    def parse(self, template: dict) -> dict:
        """Read and normalize away community-specific formatting with an equivalent in NXem."""
        if self.supported:
            print(f"Parsing via H5EBSD file format user community parser...")
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

        self.ebsd.dimensionality = 2
        # read_strings(fp[f"{grp_name}/Grid Type"][()]) == "isometric":
        for req_field in ["NCOLS", "NROWS", "XSTEP", "YSTEP"]:
            if f"{grp_name}/{req_field}" not in fp:
                print(f"Unable to parse {grp_name}/{req_field} !")
                self.ebsd = EbsdPointCloud()
                return

        self.ebsd.n["x"] = fp[f"{grp_name}/NCOLS"][()]
        self.ebsd.n["y"] = fp[f"{grp_name}/NROWS"][()]
        self.ebsd.s["x"] = ureg.Quantity(fp[f"{grp_name}/XSTEP"][()], ureg.micrometer)
        self.ebsd.s["y"] = ureg.Quantity(fp[f"{grp_name}/YSTEP"][()], ureg.micrometer)
        # "um"  # "µm"  TODO::always micron?
        # TODO::check that all data are consistent
        # TODO::what is y and x depends on coordinate system
        # TODO::why is SEPixelSize* half the value of *STEP for * X and Y respectively?

    def parse_and_normalize_group_ebsd_phases(self, fp):
        grp_name = f"{self.prfx}/EBSD/Header/Phases"
        if f"{grp_name}" not in fp:
            print(f"Unable parse {grp_name} !")
            self.ebsd = EbsdPointCloud()
            return

        # Phases, contains a subgroup for each phase where the name
        # of each subgroup is the index of the phase starting at 1.
        phase_ids = sorted(list(fp[f"{grp_name}"]), key=int)
        self.ebsd.phase = []
        self.ebsd.space_group = []
        self.ebsd.phases = {}
        for phase_id in phase_ids:
            if phase_id.isdigit():
                phase_idx = int(phase_id)
                self.ebsd.phases[phase_idx] = {}
                sub_grp_name = f"/{grp_name}/{phase_id}"
                for req_field in ["Name", "LatticeConstants", "SpaceGroup"]:
                    if f"{sub_grp_name}/{req_field}" not in fp:
                        print(f"Unable to parse {sub_grp_name}/{req_field} !")
                        self.ebsd = EbsdPointCloud()
                        return
                # Name
                phase_name = read_strings(fp[f"{sub_grp_name}/Name"][()])
                self.ebsd.phases[phase_idx]["phase_name"] = phase_name

                # Reference not available
                # self.ebsd.phases[phase_idx]["reference"] = "n/a"

                # LatticeConstants, a, b, c (angstrom) followed by alpha, beta and gamma angles in degree
                values = np.asarray(fp[f"{sub_grp_name}/LatticeConstants"][:].flatten())
                abc = values[0:3]
                angles = values[3:6]
                # TODO::available examples support that community H5EBSD reports lattice constants in angstroem
                self.ebsd.phases[phase_idx]["a_b_c"] = ureg.Quantity(abc, ureg.angstrom)
                self.ebsd.phases[phase_idx]["alpha_beta_gamma"] = ureg.Quantity(
                    angles, ureg.degree
                ).to(ureg.radian)
                latt = Lattice(
                    abc[0],
                    abc[1],
                    abc[2],
                    angles[0],
                    angles[1],
                    angles[2],
                )

                # Space Group, no, H5T_NATIVE_INT32, (1, 1), Space group index.
                # The attribute Symbol contains the string representation, for example P m -3 m.
                # formatting is a nightmare F m#ovl3m for F m 3bar m... but IT i.e.
                # international table of crystallography identifier
                spc_grp = read_strings(fp[f"{sub_grp_name}/SpaceGroup"][()])
                if spc_grp in EBSD_MAP_SPACEGROUP:
                    space_group = EBSD_MAP_SPACEGROUP[spc_grp]
                    self.ebsd.phases[phase_idx]["space_group"] = space_group
                elif phase_name in ASSUME_PHASE_NAME_TO_SPACE_GROUP:
                    space_group = ASSUME_PHASE_NAME_TO_SPACE_GROUP[phase_name]
                    self.ebsd.phases[phase_idx]["space_group"] = space_group
                else:
                    print(
                        f"Unable to decode improperly formatted space group {spc_grp} !"
                    )
                    self.ebsd = EbsdPointCloud()
                    return

                if len(self.ebsd.space_group) > 0:
                    self.ebsd.space_group.append(space_group)
                else:
                    self.ebsd.space_group = [space_group]

                strct = Structure(title=phase_name, atoms=None, lattice=latt)
                if len(self.ebsd.phase) > 0:
                    self.ebsd.phase.append(strct)
                else:
                    self.ebsd.phase = [strct]

    def parse_and_normalize_group_ebsd_data(self, fp):
        # no official documentation yet from Bruker but seems inspired by H5EBSD
        grp_name = f"{self.prfx}/EBSD/Data"
        if f"{grp_name}" not in fp:
            print(f"Unable to parse {grp_name} !")
            self.ebsd = EbsdPointCloud()
            return

        for req_field in [
            "phi1",
            "PHI",
            "phi2",
            "Phase",
            "X SAMPLE",
            "Y SAMPLE",
            "MAD",
        ]:
            if f"{grp_name}/{req_field}" not in fp:
                print(f"Unable to parse {grp_name}/{req_field} !")
                self.ebsd = EbsdPointCloud()
                return

        # Euler
        n_pts_probe = (
            np.shape(fp[f"{grp_name}/phi1"][:])[0],
            np.shape(fp[f"{grp_name}/PHI"][:])[0],
            np.shape(fp[f"{grp_name}/phi2"][:])[0],
        )
        if all_equal(n_pts_probe) and (
            n_pts_probe[0] == self.ebsd.n["x"] * self.ebsd.n["y"]
        ):
            self.ebsd.euler = np.zeros((n_pts_probe[0], 3), np.float32)
            # TODO::available examples support that community H5EBSD reports Euler triplets in degree
            for idx, angle in enumerate(["phi1", "PHI", "phi2"]):
                self.ebsd.euler[:, idx] = np.asarray(
                    fp[f"{grp_name}/{angle}"][:], np.float32
                )
            self.ebsd.euler = ureg.Quantity(self.ebsd.euler, ureg.degree).to(
                ureg.radian
            )
            self.ebsd.euler = apply_euler_space_symmetry(self.ebsd.euler)
            n_pts = n_pts_probe[0]

        # index of phase, 0 if not indexed
        # no normalization needed, also in NXem_ebsd the null model notIndexed is phase_identifier 0
        if np.shape(fp[f"{grp_name}/Phase"][:])[0] == n_pts:
            self.ebsd.phase_id = np.asarray(fp[f"{grp_name}/Phase"][:], np.int32)
        else:
            print(f"{grp_name}/Phase has unexpected shape !")
            self.ebsd = EbsdPointCloud()
            return

        # X and Y
        # there is X SAMPLE and Y SAMPLE but these are not defined somewhere instead
        # here adding x and y assuming that we scan first lines along positive x and then
        # moving downwards along +y
        # TODO::check validity for square and hexagon tiling
        self.ebsd.pos["x"] = ureg.Quantity(
            np.tile(
                np.asarray(
                    np.linspace(
                        0, self.ebsd.n["x"] - 1, num=self.ebsd.n["x"], endpoint=True
                    )
                    * self.ebsd.s["x"].magnitude,
                    dtype=np.float32,
                ),
                self.ebsd.n["y"],
            ),
            ureg.micrometer,
        )
        self.ebsd.pos["y"] = ureg.Quantity(
            np.repeat(
                np.asarray(
                    np.linspace(
                        0, self.ebsd.n["y"] - 1, num=self.ebsd.n["y"], endpoint=True
                    )
                    * self.ebsd.s["y"].magnitude,
                    dtype=np.float32,
                ),
                self.ebsd.n["x"],
            ),
            ureg.micrometer,
        )

        # Band Contrast is not stored in Bruker but Radon Quality or MAD
        # but this is s.th. different as it is the mean angular deviation between
        # indexed with simulated and measured pattern
        # TODO::MAD as degree?
        if np.shape(fp[f"{grp_name}/MAD"][:])[0] == n_pts:
            self.ebsd.descr_type = "mean_angular_deviation"
            self.ebsd.descr_value = ureg.Quantity(
                np.asarray(fp[f"{grp_name}/MAD"][:], np.float32), ureg.radian
            )
        else:
            print(f"{grp_name}/MAD has unexpected shape !")
            self.ebsd = EbsdPointCloud()
            return
