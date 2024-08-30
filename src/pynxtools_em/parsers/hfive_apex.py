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
"""Parser mapping concepts and content from EDAX/AMETEK *.edaxh5 (APEX) files on NXem."""

from typing import Any, Dict, List

import h5py
import numpy as np
from diffpy.structure import Lattice, Structure
from orix.quaternion import Orientation
from pynxtools_em.concepts.nxs_em_eds_indexing import NxEmEdsIndexing
from pynxtools_em.concepts.nxs_image_set import NxImageRealSpaceSet
from pynxtools_em.concepts.nxs_object import NxObject
from pynxtools_em.concepts.nxs_spectrum_set import NxSpectrumSet
from pynxtools_em.examples.ebsd_database import ASSUME_PHASE_NAME_TO_SPACE_GROUP
from pynxtools_em.methods.ebsd import (
    EbsdPointCloud,
    ebsd_roi_overview,
    ebsd_roi_phase_ipf,
)
from pynxtools_em.parsers.hfive_base import HdfFiveBaseParser
from pynxtools_em.utils.get_xrayline_iupac_names import get_xrayline_candidates
from pynxtools_em.utils.hfive_utils import read_strings
from pynxtools_em.utils.pint_custom_unit_registry import ureg


class HdfFiveEdaxApexParser(HdfFiveBaseParser):
    """Read APEX edaxh5"""

    def __init__(self, file_path: str = "", entry_id: int = 1, verbose: bool = False):
        super().__init__(file_path)
        self.id_mgn: Dict[str, int] = {"entry_id": entry_id, "roi_id": 1}
        self.prfx: str = ""
        self.tmp = {}
        self.ebsd: EbsdPointCloud = EbsdPointCloud()
        self.cache_id: int = 1  # deprecate soon!
        self.version: Dict = {
            "trg": {  # supported ones
                "tech_partner": ["EDAX, LLC"],
                "schema_name": ["EDAXH5"],
                "schema_version": ["2.1.0009.0001", "2.2.0001.0001", "2.5.1001.0001"],
            },
            "src": {  # actual one for instance resolved by file path
                "tech_partner": None,
                "schema_name": None,
                "schema_version": None,
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
        votes_for_support = 0
        with h5py.File(self.file_path, "r") as h5r:
            # parse Company and PRODUCT_VERSION attribute values from the first group below
            # but these are not scalar but single value lists
            # so much about interoperability
            # but hehe for the APEX example from Sebastian and Sabine
            # there is again no Company but PRODUCT_VERSION, 2 files, 2 "formats"
            grp_names = list(h5r["/"])
            if len(grp_names) == 1:
                if "Company" in h5r[grp_names[0]].attrs:
                    partner = read_strings(h5r[grp_names[0]].attrs["Company"][0])
                    if partner in self.version["trg"]["tech_partner"]:
                        self.version["src"]["tech_partner"] = partner
                        votes_for_support += 1
                if "PRODUCT_VERSION" in h5r[grp_names[0]].attrs:
                    version = read_strings(
                        h5r[grp_names[0]].attrs["PRODUCT_VERSION"][0]
                    )
                    if version in self.version["trg"]["schema_version"]:
                        self.version["src"]["schema_version"] = version
                        votes_for_support += 1
            if votes_for_support >= 1:
                # this is not as strict because IKZ example does not contain Company EDAX, LLC
                # but what if there are HDF5 files whose PRODUCT_VERSION is one of Apex but the file
                # is not an APEX file, in this case be behavior is undefined, therefore strict
                # would be cleaner
                self.supported = True

    def parse(self, template: dict) -> dict:
        """Read and normalize away EDAX/APEX-specific formatting with an equivalent in NXem."""
        if not self.supported:
            return template
        with h5py.File(f"{self.file_path}", "r") as h5r:
            self.cache_id = 1
            grp_nms = list(h5r["/"])
            # TODO::make this nesting access code better readable although its benefit
            # is that we do not need to visit first all nodes and do e.g. rfind operations
            # full_hdf_path = "/a/b/c/d/Area" triggering action could also just be catched
            # if full_hdf_path[full_hdf_path.rfind("/") + 1:].startswith("Area")
            # but then one would need to get all full_hdf_paths first for which one would
            # have to visit all nodes recursively (which the HdfFiveBaseParser) can do
            # though
            for grp_nm in grp_nms:
                sub_grp_nms = list(h5r[grp_nm])
                for sub_grp_nm in sub_grp_nms:
                    sub_sub_grp_nms = list(h5r[f"/{grp_nm}/{sub_grp_nm}"])
                    for sub_sub_grp_nm in sub_sub_grp_nms:
                        if sub_sub_grp_nm.startswith("Area"):
                            # get field-of-view (fov in edax jargon, i.e. roi)
                            self.prfx = f"/{grp_nm}/{sub_grp_nm}/{sub_sub_grp_nm}"
                            self.parse_and_normalize_eds_fov(h5r)

                            # get oim_maps, live_maps, or full area if available
                            area_grp_nms = list(
                                h5r[f"/{grp_nm}/{sub_grp_nm}/{sub_sub_grp_nm}"]
                            )
                            for area_grp_nm in area_grp_nms:
                                if area_grp_nm.startswith("OIM Map"):
                                    self.prfx = f"/{grp_nm}/{sub_grp_nm}/{sub_sub_grp_nm}/{area_grp_nm}"
                                    print(f"Parsing {self.prfx}")
                                    self.ebsd = EbsdPointCloud()
                                    self.parse_and_normalize_group_ebsd_header(h5r)
                                    self.parse_and_normalize_group_ebsd_phases(h5r)
                                    self.parse_and_normalize_group_ebsd_data(h5r)
                                    ebsd_roi_overview(self.ebsd, self.id_mgn, template)
                                    ebsd_roi_phase_ipf(self.ebsd, self.id_mgn, template)
                                    self.id_mgn["roi_id"] += 1
                                    self.ebsd = EbsdPointCloud()

                                # EDAX, APEX distinguishes different concept/groups:
                                # FOV*, full area rectangular region plus siblings
                                # Live Map *, rectangular region plus childs
                                # Free Draw *, polygonal region via GUI interaction
                                # OIM Map *, EBSD, orientation data + metadata childs
                                # with (sum) spectrum SPC, spectrum stack (SPD)
                                # with eventually different number of energy bins and
                                # Live Map */ROIs for the individual elements/ EDS maps
                                # TODO means here not planned for immediate implementation
                                # TODO: LIVENETMAPS groups are not parsed cuz not requested
                                # TODO: EBSD+EDS groups are not parsed cuz internal structure
                                # TODO: ZAF WtLineScan 2 and other custom concepts like e.g.
                                # /GeSn/GeSn_404b/Added Spectra/GeSn | GeSn_404b |
                                # Area 1 | ZAF AtLineScan 1 | 2023-01-16-15-37-41
                                # but mirror concept tree similar to those of the here
                                # implemented OIM Map and Live Map concept trees
                                if area_grp_nm.startswith(
                                    "Full Area"
                                ) or area_grp_nm.startswith("Selected Area"):
                                    # TODO: Selected Area groups have a REGION and I assume that this
                                    # is the use case when one filters from the FOV a sub-set but
                                    # not a free-form but a rectangular sub-FOV this is also substantiated
                                    # by the metadata stored in region (x,y) pair (likely upperleft edge)
                                    # and relative width/height of the sub-FOV
                                    # also supported in that Full Area has a region with (x,y) 0,0
                                    # and relative width/height 1./1.
                                    self.prfx = f"/{grp_nm}/{sub_grp_nm}/{sub_sub_grp_nm}/{area_grp_nm}"
                                    self.parse_and_normalize_eds_spc(h5r)

                                # there is a oned equivalent of the twod Free Draw called EDS Spot
                                if area_grp_nm.startswith("EDS Spot"):
                                    # TODO: parse ../REGION x,y coordinate pair (relative coordinate)
                                    # with respect to parent FOV, SPC
                                    self.prfx = f"/{grp_nm}/{sub_grp_nm}/{sub_sub_grp_nm}/{area_grp_nm}"
                                    self.parse_and_normalize_eds_spc(h5r)

                                if area_grp_nm.startswith("Free Draw"):
                                    # TODO: parse ../REGION x,y table (relative coordinate)
                                    # with respect to parent FOV, SPC
                                    self.prfx = f"/{grp_nm}/{sub_grp_nm}/{sub_sub_grp_nm}/{area_grp_nm}"
                                    self.parse_and_normalize_eds_spc(h5r)

                                if area_grp_nm.startswith("Live Map"):
                                    self.prfx = f"/{grp_nm}/{sub_grp_nm}/{sub_sub_grp_nm}/{area_grp_nm}"
                                    self.parse_and_normalize_eds_spc(h5r)
                                    self.parse_and_normalize_eds_spd(h5r)
                                    # element-specific ROI (aka element map)
                                    self.parse_and_normalize_eds_area_rois(h5r)

                                if area_grp_nm.startswith(
                                    "LineScan"
                                ) or area_grp_nm.startswith("ROILineScan"):
                                    # "free form? or (which I assume) orthogonal line grid inside the FOV
                                    # TODO::currently I assume that the internal organization of LineScan and ROILineScan
                                    # groups is the same TODO but maybe the physical ROI which they reference
                                    # respective differs !?
                                    # (TODO:: LineScan refers to the FOV that is
                                    # in the parent of the LineScan group)
                                    self.prfx = f"/{grp_nm}/{sub_grp_nm}/{sub_sub_grp_nm}/{area_grp_nm}"
                                    self.parse_and_normalize_eds_line_lsd(h5r)
                                    self.parse_and_normalize_eds_line_rois(h5r)

    def parse_and_normalize_group_ebsd_header(self, fp):
        # no official documentation yet from EDAX/APEX, deeply nested, chunking, virtual ds
        if f"{self.prfx}/EBSD/ANG/DATA/DATA" not in fp:
            self.ebsd = EbsdPointCloud()
            return
        for req_field in [
            "Grid Type",
            "Step X",
            "Step Y",
            "Number Of Rows",
            "Number Of Columns",
        ]:
            if f"{self.prfx}/Sample/{req_field}" not in fp:
                print(f"Unable to parse {self.prfx}/Sample/{req_field} !")
                self.ebsd = EbsdPointCloud()
                return

        self.ebsd.dimensionality = 2
        self.ebsd.grid_type = read_strings(fp[f"{self.prfx}/Sample/Grid Type"][()])
        # the next two lines encode the typical assumption that is not reported in tech partner file!
        self.ebsd.s["x"] = ureg.Quantity(
            fp[f"{self.prfx}/Sample/Step X"][0], ureg.micrometer
        )  # TODO::always micron?
        self.ebsd.n["x"] = fp[f"{self.prfx}/Sample/Number Of Columns"][0]
        self.ebsd.s["y"] = ureg.Quantity(
            fp[f"{self.prfx}/Sample/Step Y"][0], ureg.micrometer
        )
        self.ebsd.n["y"] = fp[f"{self.prfx}/Sample/Number Of Rows"][0]
        # TODO::check that all data are consistent

    def parse_and_normalize_group_ebsd_phases(self, fp):
        grp_name = f"{self.prfx}/EBSD/ANG/HEADER/Phase"
        if f"{grp_name}" not in fp:
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
                sub_grp_name = f"{grp_name}/{phase_id}"
                # Name
                if f"{sub_grp_name}/Material Name" in fp:
                    phase_name = read_strings(fp[f"{sub_grp_name}/Material Name"][0])
                    self.ebsd.phases[phase_idx]["phase_name"] = phase_name
                else:
                    print(f"Unable to parse {sub_grp_name}/Material Name !")
                    self.ebsd = EbsdPointCloud()
                    return

                # Reference not available only Info but this can be empty
                self.ebsd.phases[phase_idx]["reference"] = "n/a"

                req_fields = ["A", "B", "C", "Alpha", "Beta", "Gamma"]
                for req_field in req_fields:
                    if f"{sub_grp_name}/Lattice Constant {req_field}" not in fp:
                        print(f"Unable to parse ../Lattice Constant {req_field} !")
                        self.ebsd = EbsdPointCloud()
                        return
                abc = [
                    ureg.Quantity(
                        fp[f"{sub_grp_name}/Lattice Constant A"][0], ureg.angstrom
                    ),
                    ureg.Quantity(
                        fp[f"{sub_grp_name}/Lattice Constant B"][0], ureg.angstrom
                    ),
                    ureg.Quantity(
                        fp[f"{sub_grp_name}/Lattice Constant C"][0], ureg.angstrom
                    ),
                ]
                angles = [
                    ureg.Quantity(
                        fp[f"{sub_grp_name}/Lattice Constant Alpha"][0], ureg.degree
                    ).to(ureg.radian),
                    ureg.Quantity(
                        fp[f"{sub_grp_name}/Lattice Constant Beta"][0], ureg.degree
                    ).to(ureg.radian),
                    ureg.Quantity(
                        fp[f"{sub_grp_name}/Lattice Constant Gamma"][0], ureg.degree
                    ).to(ureg.radian),
                ]
                # TODO::available examples support reporting in angstroem and degree
                self.ebsd.phases[phase_idx]["a_b_c"] = abc
                self.ebsd.phases[phase_idx]["alpha_beta_gamma"] = angles
                latt = Lattice(
                    abc[0].magnitude,
                    abc[1].magnitude,
                    abc[2].magnitude,
                    angles[0].magnitude,
                    angles[1].magnitude,
                    angles[2].magnitude,
                )

                # Space Group not stored, only laue group, point group and symmetry
                # problematic because mapping is not bijective!
                # if you know the space group we know laue and point group and symmetry
                # but the opposite direction leaves room for ambiguities
                space_group = None
                if phase_name in ASSUME_PHASE_NAME_TO_SPACE_GROUP:
                    space_group = ASSUME_PHASE_NAME_TO_SPACE_GROUP[phase_name]
                else:
                    print(f"{phase_name} is not in ASSUME_PHASE_NAME_TO_SPACE_GROUP !")
                    self.ebsd = EbsdPointCloud()
                    return
                self.ebsd.phases[phase_idx]["space_group"] = space_group

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
        grp_name = f"{self.prfx}/EBSD/ANG/DATA/DATA"
        if f"{grp_name}" not in fp:
            self.ebsd = EbsdPointCloud()
            return

        n_pts = 1
        dims = ["x", "y"]
        for dim in dims:
            n_pts *= self.ebsd.n[dim]
        if (
            np.shape(fp[f"{grp_name}"]) != (n_pts,)
            or n_pts == 1
            or n_pts >= np.iinfo(np.uint32).max
        ):
            print(
                f"Unexpected shape, spot measurement, or unsupported large map {grp_name} !"
            )
            self.ebsd = EbsdPointCloud()
            return

        dat = fp[f"{grp_name}"]
        self.ebsd.euler = np.zeros((n_pts, 3), np.float32)
        self.ebsd.descr_type = "confidence_index"
        self.ebsd.descr_value = np.zeros((n_pts,), np.float32)
        self.ebsd.phase_id = np.zeros((n_pts,), np.int32)
        for i in np.arange(0, n_pts):
            # check shape of internal virtual chunked number array
            # TODO::Bunge-Euler angle ZXZ ?
            oris = Orientation.from_matrix([np.reshape(dat[i][0], (3, 3))])
            self.ebsd.euler[i, :] = oris.to_euler(degrees=False)
            self.ebsd.descr_value[i] = dat[i][2]
            self.ebsd.phase_id[i] = dat[i][3] + 1  # adding +1 because
            # EDAX/APEX seems to define notIndexed as -1 and the first valid phase_id is then 0
            # for NXem however we assume that notIndexed is 0 and the first valid_phase_id is 1
        if np.isnan(self.ebsd.euler).any():
            print(f"Conversion of om2eu unexpectedly resulted in NaN !")
            self.ebsd = EbsdPointCloud()
            return
        else:
            self.ebsd.euler = ureg.Quantity(self.ebsd.euler, ureg.radian)
        # TODO::convert orientation matrix to Euler angles via om_eu but what are conventions !
        # orix based transformation ends up in positive half space and with degrees=False
        # as radiants but the from_matrix command above might miss one rotation

        # TODO::the case of EDAX APEX shows the key problem with implicit assumptions
        # edaxh5 file not necessarily store the scan_point_{dim} positions
        # assume how tech partners write out scan_point positions implicitly
        # no absolute coordinates on the specimen surface, only coordinates w/o offset
        # TODO::square grid, with self.ebsd.s and self.ebsd.n
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

    def parse_and_normalize_eds_fov(self, fp):
        """Normalize and scale APEX-specific FOV/ROI image to NeXus."""
        src = self.prfx
        print(f"Parsing {src} ...")
        for req in ["FOVIMAGE", "FOVIMAGECOLLECTIONPARAMS", "FOVIPR"]:
            if f"{src}/{req}" not in fp:
                return
        for req in ["PixelHeight", "PixelWidth"]:
            if req not in fp[f"{src}/FOVIMAGE"].attrs:  # also check for shape
                raise ValueError(
                    f"Required attribute named {req} not found in {src}/FOVIMAGE !"
                )
        for req in ["MicronsPerPixelX", "MicronsPerPixelY"]:
            if req not in fp[f"{src}/FOVIPR"].dtype.names:
                raise ValueError(
                    f"Required attribute named {req} not found in {src}/FOVIPR !"
                )

        ckey = self.init_cache(f"eds_roi{self.cache_id}")
        self.tmp[ckey] = NxImageRealSpaceSet()
        self.tmp[ckey].tmp["source"] = f"{src}/FOVIMAGE"
        nyx = {
            "j": fp[f"{src}/FOVIMAGE"].attrs["PixelHeight"][0],
            "i": fp[f"{src}/FOVIMAGE"].attrs["PixelWidth"][0],
        }
        syx = {
            "j": fp[f"{src}/FOVIPR"]["MicronsPerPixelY"][0],
            "i": fp[f"{src}/FOVIPR"]["MicronsPerPixelX"][0],
        }
        scan_unit = {"i": "µm", "j": "µm"}
        # is micron because MicronsPerPixel{dim} used by EDAX
        self.tmp[ckey].tmp["image_2d/real"].value = np.reshape(
            np.asarray(fp[f"{src}/FOVIMAGE"]), (nyx["j"], nyx["i"])
        )
        dims = ["j", "i"]
        for dim in dims:
            self.tmp[ckey].tmp[f"image_2d/axis_{dim}"].value = np.asarray(
                np.linspace(0, nyx[dim] - 1, num=nyx[dim], endpoint=True) * syx[dim],
                dtype=syx[dim].dtype,
            )
            self.tmp[ckey].tmp[
                f"image_2d/axis_{dim}@long_name"
            ].value = f"Position along {dim} ({scan_unit[dim]})"
        self.cache_id += 1

        for key, obj in self.tmp[ckey].tmp.items():
            if isinstance(obj, NxObject):
                if obj.value is not None:
                    print(f"ckey: {ckey}, key: {key}, obj: {obj}")
            else:
                print(f"ckey: {ckey}, key: {key}, obj: {obj}")

    def parse_and_normalize_eds_spc(self, fp):
        """Normalize and scale APEX-specific SPC (sum) spectrum to NeXus."""
        # https://hyperspy.org/rosettasciio/_downloads/
        # 9e2f0ccf5287bb2d17f1b7550e1d626f/SPECTRUM-V70.pdf
        src = self.prfx
        print(f"Parsing {src} ...")
        if f"{src}/SPC" not in fp:
            return
        if "NumberOfLines" in fp[f"{src}/SPC"].attrs:
            return
        for req in ["eVOffset", "evPch", "NumberOfPoints", "SpectrumCounts"]:
            if req not in fp[f"{src}/SPC"].dtype.names:  # also check for shape
                raise ValueError(
                    f"Required attribute named {req} not found in {src}/SPC !"
                )

        ckey = self.init_cache(f"eds_spc{self.cache_id}")
        self.tmp[ckey] = NxSpectrumSet()
        self.tmp[ckey].tmp["source"] = f"{src}/SPC"
        e_zero = fp[f"{src}/SPC"]["eVOffset"][0]
        e_delta = fp[f"{src}/SPC"]["evPch"][0]
        e_n = fp[f"{src}/SPC"]["NumberOfPoints"][0]
        self.tmp[ckey].tmp["spectrum_0d/axis_energy"].value = np.asarray(
            (
                e_zero
                + np.linspace(0, int(e_n) - 1, num=int(e_n), endpoint=True) * e_delta
            )
            / 1000.0,
            dtype=e_zero.dtype,
        )  # keV
        self.tmp[ckey].tmp["spectrum_0d/axis_energy@long_name"].value = "Energy (keV)"
        self.tmp[ckey].tmp["spectrum_0d/real"].value = np.asarray(
            fp[f"{src}/SPC"]["SpectrumCounts"][0], np.int32
        )
        self.tmp[ckey].tmp["spectrum_0d/real@long_name"].value = f"Count (1)"
        self.cache_id += 1

        for key, obj in self.tmp[ckey].tmp.items():
            if isinstance(obj, NxObject):
                if obj.value is not None:
                    print(f"ckey: {ckey}, key: {key}, obj: {obj}")
            else:
                print(f"ckey: {ckey}, key: {key}, obj: {obj}")

    def parse_and_normalize_eds_spd(self, fp):
        """Normalize and scale APEX-specific spectrum cuboid to NeXus."""
        # https://hyperspy.org/rosettasciio/_downloads/
        # c2e8b23d511a3c44fc30c69114e2873e/SpcMap-spd.file.format.pdf
        src = self.prfx
        print(f"Parsing {src} ...")
        if f"{src}/SPD" not in fp:
            return
        for req in [
            "MicronPerPixelX",
            "MicronPerPixelY",
            "NumberOfLines",
            "NumberOfPoints",
            "NumberofChannels",
        ]:  # TODO: mind the typo here, can break parsing easily!
            if req not in fp[f"{src}/SPD"].attrs:  # also check for shape
                raise ValueError(
                    f"Required attribute named {req} not found in {src}/SPD !"
                )

        ckey = self.init_cache(f"eds_spd{self.cache_id}")
        self.tmp[ckey] = NxSpectrumSet()
        self.tmp[ckey].tmp["source"] = f"{src}/SPD"
        nyxe = {
            "y": fp[f"{src}/SPD"].attrs["NumberOfLines"][0],
            "x": fp[f"{src}/SPD"].attrs["NumberOfPoints"][0],
            "e": fp[f"{src}/SPD"].attrs["NumberofChannels"][0],
        }
        print(f"lines: {nyxe['y']}, points: {nyxe['x']}, channels: {nyxe['e']}")
        # the native APEX SPD concept instance is a two-dimensional array of arrays of length e (n_energy_bins)
        # likely EDAX has in their C(++) code a vector of vector or something equivalent either way we faced
        # nested C arrays of the base data type in an IKZ example <i2, even worse stored chunked in HDF5 !
        # while storage efficient and likely with small effort to add HDF5 storage from the EDAX code
        # thereby these EDAX energy count arrays are just some payload inside a set of compressed chunks
        # without some extra logic to resolve the third (energy) dimension reading them can be super inefficient
        # so let's read chunk-by-chunk to reuse chunk cache, hopefully...
        chk_bnds: Dict = {"x": [], "y": []}
        chk_info = {
            "ny": nyxe["y"],
            "cy": fp[f"{src}/SPD"].chunks[0],
            "nx": nyxe["x"],
            "cx": fp[f"{src}/SPD"].chunks[1],
        }
        for dim in ["y", "x"]:
            idx = 0
            while idx < chk_info[f"n{dim}"]:
                if idx + chk_info[f"c{dim}"] < chk_info[f"n{dim}"]:
                    chk_bnds[f"{dim}"].append((idx, idx + chk_info[f"c{dim}"]))
                else:
                    chk_bnds[f"{dim}"].append((idx, chk_info[f"n{dim}"]))
                idx += chk_info[f"c{dim}"]
        for key, val in chk_bnds.items():
            print(f"{key}, {val}")
        spd_chk = np.zeros(
            (nyxe["y"], nyxe["x"], nyxe["e"]), fp[f"{src}/SPD"][0, 0][0].dtype
        )
        print(f"edax: {np.shape(spd_chk)}, {type(spd_chk)}, {spd_chk.dtype}")
        print(
            "WARNING::Currently the parsing of the SPD is switched off for debugging but works!"
        )
        self.cache_id += 1
        return
        for chk_bnd_y in chk_bnds["y"]:
            for chk_bnd_x in chk_bnds["x"]:
                spd_chk[chk_bnd_y[0] : chk_bnd_y[1], chk_bnd_x[0] : chk_bnd_x[1], :] = (
                    fp[
                        f"{src}/SPD"
                    ][chk_bnd_y[0] : chk_bnd_y[1], chk_bnd_x[0] : chk_bnd_x[1]]
                )
        for key, obj in self.tmp[ckey].tmp.items():
            if isinstance(obj, NxObject):
                if obj.value is not None:
                    print(f"ckey: {ckey}, key: {key}, obj: {obj}")
            else:
                print(f"ckey: {ckey}, key: {key}, obj: {obj}")
        # compared to naive reading, thereby we read the chunks as they are arranged in memory
        # and thus do not discard unnecessarily data cached in the hfive chunk cache
        # by contrast, if we were to read naively for each pixel the energy array most of the
        # content in the chunk cache is discarded plus we may end up reading a substantially
        # more times from the file, tested this on a Samsung 990 2TB pro-SSD for a tiny 400 x 512 SPD:
        # above strategy 2s, versus hours! required to read and reshape the spectrum via naive I/O
        # TODO:: e.g the IKZ example VInP_108_L2 has a Area 10/Live Map 1/SPD but it has
        # no calibration data of the spectrum stack, which is significant as Live Map 1
        # has a child SPC but here the number of channels is 4096 while for SPD the
        # number of channels is 1000
        # one could inspect the location of identified peaks from an SPC instance and
        # thus infer (assuming linearly spaced energy channels) the range but as this is
        # pure speculation and because of the fact that not even the SPD file format
        # specification details the metadata, i.e. energy per channel, start and end
        # we do not use the SPD instance right now

    def parse_and_normalize_eds_area_rois(self, fp):
        """Normalize and scale APEX-specific EDS element emission line maps to NeXus."""
        src = self.prfx
        print(f"Parsing {src} ...")
        for req in ["ELEMENTOVRLAYIMGCOLLECTIONPARAMS", "PHASES", "ROIs", "SPC"]:
            if f"{src}/{req}" not in fp:
                return
        for req in ["eVOffset", "evPch", "NumberOfPoints", "SpectrumCounts"]:
            if req not in fp[f"{src}/SPC"].dtype.names:  # also check for shape
                raise ValueError(
                    f"Required attribute named {req} not found in {src}/SPC !"
                )
        for req in ["ResolutionX", "ResolutionY", "mmFieldWidth", "mmFieldHeight"]:
            if req not in fp[f"{src}/ELEMENTOVRLAYIMGCOLLECTIONPARAMS"].dtype.names:
                # also check for shape
                raise ValueError(
                    f"Required attribute named {req} not found in "
                    f"{src}/ELEMENTOVRLAYIMGCOLLECTIONPARAMS !"
                )
        # find relevant EDS maps (pairs of <symbol>.dat, <symbol>.ipr) groups
        uniq = set()
        for group_name in fp[f"{src}/ROIs"]:
            token = group_name.split(".")
            if (len(token) == 2) and (token[1] in ("dat", "ipr")):
                uniq.add(token[0])
        for entry in uniq:
            if (f"{src}/ROIs/{entry}.dat" not in fp[f"{src}/ROIs"]) or (
                f"{src}/ROIs/{entry}.ipr" not in fp[f"{src}/ROIs"]
            ):
                uniq.remove(entry)
                continue
            if ("RoiStartChan" not in fp[f"{src}/ROIs/{entry}.dat"].attrs) or (
                "RoiEndChan" not in fp[f"{src}/ROIs/{entry}.dat"].attrs
            ):
                uniq.remove(entry)

        ckey = self.init_cache(f"eds_map{self.cache_id}")
        self.tmp[ckey] = NxEmEdsIndexing()
        self.tmp[ckey].tmp["source"] = f"{src}/ROIs"
        self.tmp[ckey].tmp["IMAGE_SET"] = []

        e_zero = fp[f"{src}/SPC"]["eVOffset"][0]
        e_delta = fp[f"{src}/SPC"]["evPch"][0]
        e_n = fp[f"{src}/SPC"]["NumberOfPoints"][0]
        e_channels = np.asarray(
            e_zero + np.linspace(0, e_n - 1, num=int(e_n), endpoint=True) * e_delta,
            dtype=e_zero.dtype,
        )  # eV, as xraydb demands
        nxy = {
            "i": fp[f"{src}/ELEMENTOVRLAYIMGCOLLECTIONPARAMS"][0]["ResolutionX"],
            "j": fp[f"{src}/ELEMENTOVRLAYIMGCOLLECTIONPARAMS"][0]["ResolutionY"],
            "li": fp[f"{src}/ELEMENTOVRLAYIMGCOLLECTIONPARAMS"][0]["mmFieldWidth"],
            "lj": fp[f"{src}/ELEMENTOVRLAYIMGCOLLECTIONPARAMS"][0]["mmFieldHeight"],
        }
        sxy = {"i": nxy["li"] / nxy["i"], "j": nxy["lj"] / nxy["j"]}
        scan_unit = {"i": "µm", "j": "µm"}
        for entry in uniq:
            eds_map = NxImageRealSpaceSet()
            eds_map.tmp["source"] = f"{src}/ROIs/{entry}"
            eds_map.tmp["description"] = f"{entry}"
            # this can be a custom name e.g. InL or In L but it is not necessarily
            # a clean description of an element plus a IUPAC line, hence get all
            # theoretical candidates within integrated energy region [e_roi_s, e_roi_e]
            e_roi_s = fp[f"{src}/ROIs/{entry}.dat"].attrs["RoiStartChan"][0]
            e_roi_e = fp[f"{src}/ROIs/{entry}.dat"].attrs["RoiEndChan"][0]
            eds_map.tmp["energy_range"] = NxObject(
                unit="eV",
                value=np.asarray([e_channels[e_roi_s], e_channels[e_roi_e + 1]]),
            )
            eds_map.tmp["iupac_line_candidates"] = ", ".join(
                get_xrayline_candidates(e_channels[e_roi_s], e_channels[e_roi_e + 1])
            )
            for dim in ["i", "j"]:
                eds_map.tmp[f"image_2d/axis_{dim}"].value = np.asarray(
                    0.0
                    + np.linspace(0, nxy[dim] - 1, num=int(nxy[dim]), endpoint=True)
                    * sxy[dim],
                    dtype=np.float32,
                )
                eds_map.tmp[
                    f"image_2d/axis_{dim}@long_name"
                ].value = f"{dim}-axis pixel coordinate ({scan_unit[dim]})"
                eds_map.tmp["image_2d/real"].value = np.asarray(
                    fp[f"{src}/ROIs/{entry}.dat"]
                )
            self.tmp[ckey].tmp["IMAGE_SET"].append(eds_map)  # copy
        self.cache_id += 1

        for key, val in self.tmp[ckey].tmp.items():
            if key.startswith("IMAGE_SET"):
                for img in val:
                    for kkey, vval in img.tmp.items():
                        print(f"\t\timg, key: {kkey}, val: {vval}")
            else:
                print(f"ckey: {ckey}, eds_map, key: {key}, val: {val}")

    def parse_and_normalize_eds_line_lsd(self, fp):
        """Normalize and scale APEX-specific line scan with one spectrum each to NeXus."""
        # https://hyperspy.org/rosettasciio/_downloads/
        # c2e8b23d511a3c44fc30c69114e2873e/SpcMap-spd.file.format.pdf
        # ../Region/Step = ..Region(deltaXY) * ../IPR/mmField(Width/Height) !
        # ../Region attributes detail the calibrated position of the line in the image
        # we need to collect pieces of information from various places to contextualize
        # the absolute location of the line grid in the image of this LineScan group
        # and to get the spectra right
        # TODO: this can be an arbitrary free form line, right?
        src = self.prfx
        print(f"Parsing {src} ...")
        for req in ["LSD", "SPC", "REGION", "LINEIMAGECOLLECTIONPARAMS"]:
            if f"{src}/{req}" not in fp:
                return
        # TODO: mind the typo here, can break parsing easily!
        for req in ["NumberOfSpectra", "NumberofChannels"]:
            # also check all following four for shape
            if req not in fp[f"{src}/LSD"].attrs:
                raise ValueError(
                    f"Required attribute named {req} not found in {src}/LSD !"
                )
        for req in ["evPCh"]:
            if req not in fp[f"{src}/SPC"].attrs:
                raise ValueError(
                    f"Required attribute named {req} not found in {src}/SPC !"
                )
        for req in ["Step", "X1", "X2", "Y1", "Y2"]:
            if req not in fp[f"{src}/REGION"].attrs:
                raise ValueError(
                    f"Required attribute named {req} not found in {src}/REGION !"
                )
        # mm as the name implies
        for req in ["mmFieldWidth", "mmFieldHeight"]:
            if req not in fp[f"{src}/LINEMAPIMAGECOLLECTIONPARAMS"].attrs:
                raise ValueError(
                    f"Required attribute named {req} not found "
                    f"in {src}/LINEMAPIMAGECOLLECTIONPARAMS !"
                )

        ckey = self.init_cache(f"eds_lsd{self.cache_id}")
        self.tmp[ckey] = NxSpectrumSet()
        self.tmp[ckey].tmp["source"] = f"{src}/LSD"
        e_zero = 0.0  # strong assumption based on VInP_108_L2 example from IKZ
        e_delta = fp[f"{src}/SPC"].attrs["eVPCh"][0]
        e_n = fp[f"{src}/LSD"].attrs["NumberofChannels"][0]
        self.tmp[ckey].tmp["spectrum_1d/axis_energy"].value = np.asarray(
            e_zero
            + np.linspace(0, int(e_n) - 1, num=int(e_n), endpoint=True) * e_delta,
            dtype=e_zero.dtype,
        )
        self.tmp[ckey].tmp["spectrum_1d/axis_energy@long_name"].value = "Energy (eV)"

        # vector representation of the line's physical length from mm to µm
        line = np.asarray(
            [
                (
                    fp[f"{src}/REGION"].attrs["X2"][0]
                    - fp[f"{src}/REGION"].attrs["X1"][0]
                )
                * fp[f"{src}/LINEMAPIMAGECOLLECTIONPARAMS"].attrs["mmFieldWidth"]
                * 1000.0,
                (
                    fp[f"{src}/REGION"].attrs["Y2"][0]
                    - fp[f"{src}/REGION"].attrs["Y1"][0]
                )
                * fp[f"{src}/LINEMAPIMAGECOLLECTIONPARAMS"].attrs["mmFieldHeight"]
                * 1000.0,
            ]
        )
        i_n = fp[f"{src}/LSD"].attrs["NumberOfSpectra"][0]
        line_length = np.sqrt(line[0] ** 2 + line[1] ** 2)
        line_incr = line_length / i_n
        self.tmp[ckey].tmp["spectrum_1d/axis_i"].value = np.asarray(
            np.linspace(0.5 * line_incr, line_length, num=i_n, endpoint=True),
            dtype=fp[f"{src}/REGION"].attrs["X2"][0].dtype,
        )
        self.tmp[ckey].tmp["spectrum_1d/axis_i@long_name"] = (
            "Coordinate along x-axis (µm)"
        )
        self.tmp[ckey].tmp["spectrum_1d/real"].value = np.asarray(
            fp[f"{src}/LSD"][0], np.int32
        )
        self.tmp[ckey].tmp["spectrum_1d/real@long_name"].value = f"Count (1)"
        self.cache_id += 1

        for key, val in self.tmp[ckey].tmp.items():
            print(f"ckey: {ckey}, spectrum_1d, key: {key}, val: {val}")

    def parse_and_normalize_eds_line_rois(self, fp):
        """Normalize and scale APEX-specific EDS element emission line maps to NeXus."""
        # source of the information
        src = self.prfx
        print(f"Parsing {src} ...")
        # ckey = self.init_named_cache(f"eds_map{self.cache_id}")
        # self.cache_id += 1
        pass
