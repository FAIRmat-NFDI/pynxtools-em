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
"""Parser mapping concepts and content from community *.dream3d files on NXem."""

from typing import Dict

import h5py
import numpy as np
from pynxtools_em.methods.ebsd import (
    SQUARE_TILING,
    EbsdPointCloud,
    has_hfive_magic_header,
)
from pynxtools_em.parsers.hfive_base import HdfFiveBaseParser
from pynxtools_em.utils.get_file_checksum import (
    DEFAULT_CHECKSUM_ALGORITHM,
    get_sha256_of_file_content,
)
from pynxtools_em.utils.hfive_utils import read_strings

# DREAM3D implements essentially a data analysis workflow with individual steps
# in the DREAM3D jargon each step is referred to as a filter, filters have well-defined
# name and version, each filter takes dependent on its version specific input and
# generates predictable output, this is a benefit and signature of the professional
# design and idea behind DREAM3D
# in effect, the combination of versioned filters used in combination with the DREAM3D
# software version and file version defines how results end up in a DREAM3D file

# TODO::to capture every possible output one would keep a record of the individual
# schemes for each filter and the differences in these between versions
# considering the fact that DREAM3D is still in a process of migrating from previous
# versions to a so-called DREAM3DNX (more professional) version we do not wish to explore
# for now how this filter-based schema version can be implemented
# instead we leave it with a few examples, here specifically how to extract if
# available inverse pole figure maps for the reconstructed discretized three-dimensional
# microstructure which is the key task that DREAM3D enables users to generate from a
# collection of EBSD mappings obtained via serial-sectioning

# idea behind this implementation:
# e.g. a materials scientists/engineer working in the field of e.g. ICME
# generating N microstructure reconstructions from M measurements
# in general N and M >= 1 and N can be N >> M i.e. one serial-section study with
# hundreds of different microstructures, typical case for exploring phase space
# of thermo-chemo-mechanical material response effect of structure on properties
# in this case each DREAM3D run should be supplemented with contextualizing metadata
# e.g. collected via an ELN e.g. user, material, measurement used, etc. i.e. all those
# pieces of information which are not documented by or not documentable currently by
# the DREAM3D software within its own realm
# in effect a research may have say N ~= 1000 uploads with one DREAM3D instance each
# benefits: i) for the researcher search across explore, ii) for many researchers explore
# and contextualize

# DREAM3D constants
# http://dream3d.bluequartz.net/Help/Filters/OrientationAnalysisFilters/CreateEnsembleInfo/
# picking the first in each category here https://en.wikipedia.org/wiki/List_of_space_groups

DREAM_SPACEGROUPS_TO_REPRESENTATIVE_SPACEGROUP = {
    0: 191,
    1: 221,
    2: 175,
    3: 200,
    4: 2,
    5: 10,
    6: 47,
    7: 83,
    8: 123,
    9: 147,
    10: 162,
}
# UnknownCrystalStructure, 999, Undefined Crystal Structure
from pynxtools_em.utils.pint_custom_unit_registry import ureg


class HdfFiveDreamThreedLegacyParser(HdfFiveBaseParser):
    """Read some information from (legacy) DREAM3D HDF5 files (Bluequartz's DREAM3D)"""

    def __init__(self, file_path: str = "", entry_id: int = 1, verbose: bool = False):
        if file_path:
            self.file_path = file_path
        self.id_mgn: Dict[str, int] = {
            "entry_id": entry_id if entry_id > 0 else 1,
            "roi_id": 1,
        }
        self.verbose = verbose
        self.prfx = ""  # template path handling
        # strictly speaking Bluequartz refers the above-mentioned here as File Version
        # but content is expected adaptive depends on filters used, their versions, and
        # the sequence in which the execution of these filters was instructed
        self.version: Dict = {  # Dict[str, Dict[str, List[str]]]
            "trg": {
                "tech_partner": ["Bluequartz"],
                "schema_name": ["DREAM3D"],
                "schema_version": ["6.0", "7.0"],
                "writer_name": ["DREAM3D"],
                "writer_version": [
                    "1.2.812.508bf5f37",
                    "2.0.170.4eecce207",
                    "1.0.107.2080f4e",
                    "2014.03.05",
                    "2014.03.13",
                    "2014.03.15",
                    "2014.03.16",
                    "4.3.6052.263064d",
                    "1.2.828.f45085c83",
                    "2.0.170.4eecce207",
                    "1.2.826.7c66a0e77",
                ],
            },
            "src": {},
        }
        self.path_registry: Dict = {}
        self.supported = False
        self.check_if_supported()
        if not self.supported:
            print(
                f"Parser {self.__class__.__name__} finds no content in {file_path} that it supports"
            )

    def check_if_supported(self):
        # check if instance to process matches any of these constraints
        self.supported = False
        if not has_hfive_magic_header(self.file_path):
            return

        with h5py.File(self.file_path, "r") as h5r:
            if len(h5r["/"].attrs) < 2:
                return

            for req_field in ["DREAM3D Version", "FileVersion"]:
                if f"{req_field}" not in h5r["/"].attrs:
                    return

            votes_for_support = 0
            dream_version = read_strings(h5r["/"].attrs["DREAM3D Version"])
            if dream_version in self.version["trg"]["writer_version"]:
                votes_for_support += 1
            file_version = read_strings(h5r["/"].attrs["FileVersion"])
            if file_version in self.version["trg"]["schema_version"]:
                votes_for_support += 1

            if votes_for_support == 2:
                self.supported = True
                # TODO::instantiate self.version["src"]

    def search_normalizable_ebsd_content(self):
        """Check if that highly customizable DREAM3D file has supported content or not."""
        super().open()
        super().get_content()
        # super().report_content()
        super().close()
        # DREAM3D allows flexible instance names in the HDF5 tree therefore
        # first identify the pathes of relevant groups, datasets for EBSD content
        self.path_registry = {
            "group_geometry": None,
            "group_data": None,
            "group_phases": None,
            "is_simulated": None,
            "roi_info": None,
        }
        # is_simulated is True when that DREAM3D pipeline generated just a synthetic structure
        # roi_info should be pair of absolute path to dataset (HDF5) and BC, CI or MAD
        # (like BC, CI, or MAD) to explain from which to render a greyscale image of the ROI
        # the logic to find if there is at all a 3D EBSD reconstruction in it
        # search for a node:
        group_geometry = []
        #    named _SIMPL_GEOMETRY
        candidate_paths = []
        for hdf_node_path in self.datasets.keys():
            idx = hdf_node_path.find("/_SIMPL_GEOMETRY")
            if idx > -1:
                candidate_paths.append((hdf_node_path, idx))
        #    which has childs "DIMENSIONS, ORIGIN, SPACING"
        for path_idx in candidate_paths:
            head = path_idx[0][0 : path_idx[1]]
            tail = path_idx[0][path_idx[1] :]
            found = 0
            for req_field in ["DIMENSIONS", "ORIGIN", "SPACING"]:
                if f"{head}/_SIMPL_GEOMETRY/{req_field}" in self.datasets:
                    found += 1
            if found == 3:
                group_geometry.append(head)
                break
        del candidate_paths
        # if only one such node found parse only if
        if len(group_geometry) != 1:
            return False
        else:
            group_geometry = group_geometry[0]
        #    that node has one sibling node called CellData
        found = 0
        i_j_k = (None, None, None)
        group_data = None
        for entry in self.datasets:
            if (
                entry.startswith(f"{group_geometry}") is True
                and entry.endswith(f"EulerAngles") is True
            ):
                group_data = entry[0:-12]  # removing the trailing fwslash
                #       which has a dset of named EulerAngles shape 4d, (i, j, k, 1) +
                shp = self.datasets[entry][2]
                if isinstance(shp, tuple) and len(shp) == 4:
                    if shp[3] == 3:
                        i_j_k = (shp[0], shp[1], shp[2])
                        found += 1
                        break
        if group_data is None:
            return False
        #       which has a dset named BC or CI or MAD shape 4d (i, j, k, 1) +
        group_roi = None
        roi_info = (None, None)
        one_key_required = {
            "BC": "bc",
            "Band Contrast": "bc",
            "BandContrast": "bc",
            "CI": "ci",
            "Confidence Index": "ci",
            "ConfidenceIndex": "ci",
            "MAD": "mad",
            "Mean Angular Deviation": "mad",
            "MeanAngularDeviation": "mad",
        }
        for key in one_key_required:
            if f"{group_data}/{key}" in self.datasets:
                shp = self.datasets[f"{group_data}/{key}"][2]
                if isinstance(shp, tuple) and len(shp) == 4:
                    if (shp[0], shp[1], shp[2]) == i_j_k:
                        roi_info = (f"{group_data}/{key}", one_key_required[key])
                        break
        #       which has a dset named Phases shape 4d (i, j, k, 1) +
        if f"{group_data}/Phases" in self.datasets:
            shp = self.datasets[f"{group_data}/Phases"][2]
            if isinstance(shp, tuple) and len(shp) == 4:
                if (shp[0], shp[1], shp[2]) == i_j_k:
                    found += 1
        #    that node has one sibling node called Phase Data
        if found != 2:
            return False
        #       which has a dset named CrystalStructures, LatticeConstants, MaterialName

        # at this point there are at least to scenarios where the data come from
        # a serial-sectioning experiment or a computer simulated
        # (RVE instantiation/microstructure synthesis) that generating an input for the
        # computer simulation without any real sample necessarily characterized
        # if we have that simulated scenario the location AND that is indicated
        # by the keyword "SyntheticVolumeDataContainer" we hunt elsewhere
        group_phases = None
        is_simulated = None
        if group_data.find("SyntheticVolumeDataContainer") > -1:
            is_simulated = True
            # hunt CrystalStructures
            for entry in self.datasets:
                if entry.find("CrystalStructures") > -1:
                    if group_phases is None:
                        group_phases = entry[0:-18]  # remove trailing fwslash
        else:
            is_simulated = False
            # these locations found in the examples but likely can be changed
            # depending on how the filters were configured ...
            for loc in ["Phase Data", "CellEnsembleData"]:
                if f"{group_geometry}/{loc}/CrystalStructures" in self.datasets:
                    group_phases = f"{group_geometry}/{loc}"
                    found = 0
                    for req_field in [
                        "CrystalStructures",
                        "LatticeConstants",
                        "MaterialName",
                    ]:
                        if f"{group_phases}/{req_field}" in self.datasets.keys():
                            found += 1
                    if found != 3:
                        return False
        if group_phases is None:
            return False

        self.path_registry["group_geometry"] = group_geometry
        self.path_registry["group_data"] = group_data
        self.path_registry["group_phases"] = group_phases
        self.path_registry["is_simulated"] = is_simulated
        self.path_registry["roi_info"] = roi_info
        print(f"Relevant 3D EBSD content found")
        for key, val in self.path_registry.items():
            print(f"{key}: {val}")

        # but see if that logic does not also check the shape and numerical content
        # there are still possibilities where this logic fails to detect a concept
        # reliably, this shows clearly that documenting and offering versioned description
        # of content is the key barrier to implement more sophisticated conceptual
        # normalization and assuring that content from other data providers (like DREAM3D)
        # is understood before being normalized so that results in the RDMS are really
        # useful and comparable
        # after this initial version of the parser was written DREAM3D became DREAM3NX

        # this is one approach how to find relevant groups
        # another would be to interpret really the filters applied and hunt
        # for the output within the parameters of a specific filter
        return True

    def parse(self, template: dict) -> dict:
        """Read and normalize away community-specific formatting with an equivalent in NXem."""
        if self.supported:
            with open(self.file_path, "rb", 0) as fp:
                self.file_path_sha256 = get_sha256_of_file_content(fp)
            print(
                f"Parsing {self.file_path} DREAM3D legacy with SHA256 {self.file_path_sha256} ..."
            )
            if self.search_normalizable_ebsd_content():
                with h5py.File(self.file_path, "r") as h5r:
                    self.ebsd = EbsdPointCloud()
                    self.parse_and_normalize_ebsd_header(h5r)
                    self.parse_and_normalize_ebsd_phases(h5r)
                    self.parse_and_normalize_ebsd_data(h5r)
                    # TODO::write back
                    self.id_mgn["roi_id"] += 1
                    self.ebsd = EbsdPointCloud()
            # TODO::more testing, more examples using DREAM3DNX
        return template

    def parse_and_normalize_ebsd_header(self, fp):
        smpl = "/_SIMPL_GEOMETRY/"
        grpnm = "group_geometry"
        dims = fp[f"{self.path_registry[{grpnm}]}{smpl}DIMENSIONS"][:].flatten()
        org = fp[f"{self.path_registry[{grpnm}]}{smpl}ORIGIN"][:].flatten()
        spc = fp[f"{self.path_registry[{grpnm}]}{smpl}SPACING"][:].flatten()

        # TODO::is it correct an assumption that DREAM3D regrids using square voxel
        self.ebsd.dimensionality = 3
        self.ebsd.grid_type = SQUARE_TILING
        # the next two lines encode the typical assumption that is not reported in tech partner file!
        for dim_idx, dim in enumerate(["x", "y", "z"]):
            self.ebsd.n[dim] = dims[dim_idx]
            self.ebsd.s[dim] = ureg.Quantity(spc[dim_idx], ureg.micrometer)
            self.ebsd.o[dim] = ureg.Quantity(org[dim_idx], ureg.micrometer)
        # TODO::where is the length scale documented? always micron?

    def parse_and_normalize_ebsd_phases(self, fp):
        self.ebsd.phase = []
        self.ebsd.space_group = []
        self.ebsd.phases = {}
        idx = np.asarray(
            fp[f"{self.path_registry['group_phases']}/CrystalStructures"][:].flatten(),
            np.uint32,
        )
        print(f"csys {np.shape(idx)}, {idx}")
        nms = None
        if f"{self.path_registry['group_phases']}/MaterialName" in fp:
            nms = read_strings(
                fp[f"{self.path_registry['group_phases']}/MaterialName"][:]
            )
            print(f"nms ---------> {nms}")
            if len(idx) != len(nms):
                print(
                    f"{__name__} MaterialName was recoverable but array has different length than for CrystalStructures!"
                )
                self.ebsd = EbsdPointCloud()
                return
        # alternatively
        if f"{self.path_registry['group_phases']}/PhaseName" in fp:
            nms = read_strings(fp[f"{self.path_registry['group_phases']}/PhaseName"][:])
            print(f"nms ---------> {nms}")
            if len(idx) != len(nms):
                print(
                    f"{__name__} PhaseName was recoverable but array has different length than for CrystalStructures!"
                )
                self.ebsd = EbsdPointCloud()
                return
        ijk = 0
        for entry in idx:
            if entry != 999:
                self.ebsd.phases[ijk] = {}
                self.ebsd.phases[ijk]["space_group"] = (
                    DREAM_SPACEGROUPS_TO_REPRESENTATIVE_SPACEGROUP[entry]
                )
                self.ebsd.phases[ijk]["phase_name"] = nms[ijk]
            ijk += 1
            # TODO::need to do a reindexing of the phase ids as they
            # might not be stored in asc. order!

            # LatticeAngles are implicitly defined for each space group
            # LatticeDimensions essentially provides scaling information
            # but indeed for simulating a crystal with a computer simulation
            # at a length scale larger than atoms (mesoscale and macroscale)
            # one can argue the exact spacing is not needed except when
            # one wishes to compute the diffraction pattern but as most results
            # from DREAM3D implicitly rely on information from a previous workflow
            # where these atomistic details have been abstracted away it is
            # factually true that there is not really a need for documenting
            # the lattice dimensions from a DREAM3D analysis.

    def parse_and_normalize_ebsd_data(self, fp):
        self.ebsd.euler = np.asarray(
            fp[f"{self.path_registry['group_data']}/EulerAngles"], np.float32
        )
        old_shp = np.shape(self.ebsd.euler)
        self.ebsd.euler = np.reshape(
            self.ebsd.euler,
            (int(np.prod(old_shp[0:3])), int(old_shp[3])),
            order="C",
        )
        self.ebsd.euler = ureg.Quantity(self.ebsd.euler, ureg.radian)
        # TODO::DREAM3D uses Rowenhorst et. al. conventions
        # so we are already in positive halfspace, and radiants

        self.ebsd.phase_id = np.asarray(
            fp[f"{self.path_registry['group_data']}/Phases"], np.int32
        )
        old_shp = np.shape(self.ebsd.phase_id)
        self.ebsd.phase_id = np.reshape(
            self.ebsd.phase_id, (int(np.prod(old_shp[0:3])),), order="C"
        )
        print(np.unique(self.ebsd.phase_id))
        # Phases here stores C-style index which Phase of the possible ones
        # we are facing, the marker 999 is equivalent to the null-model notIndexed
        # in all examples 999 was the first (0th) entry in the list of possible ones
        # in effect, the phase_id == 0 rightly so marks position indexed with the null-model

        # normalize pixel coordinates to physical positions even though the origin can still dangle somewhere
        if self.ebsd.grid_type != SQUARE_TILING:
            print(
                f"WARNING: Check carefully correct interpretation of scan_point coords!"
            )
        # TODO::all other hfive parsers normalize scan_point_{dim} arrays into
        # tiled and repeated coordinate tuples and not like below
        # only the dimension scale axes values!
        for dim in ["x", "y", "z"]:
            self.ebsd.pos[dim] = np.asarray(
                0.5 * self.ebsd.s[dim].magnitude
                + np.linspace(
                    0,
                    self.ebsd.n[dim] - 1,
                    num=self.ebsd.n[dim],
                    endpoint=True,
                )
                * self.ebsd.s[dim].magnitude,
                dtype=np.float32,
            )
        # TODO::ROI overview rendered from one of these possibilities bc, ci, or mad
