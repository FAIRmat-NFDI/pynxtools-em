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
"""Standardized functionalities and visualization used within the EBSD community using normalized OIM data."""

import mmap
import os

import matplotlib.pyplot as plt  # in the hope that this closes figures with orix plot
import numpy as np
from orix import plot
from orix.quaternion import Rotation
from orix.quaternion.symmetry import get_point_group
from orix.vector import Vector3d
from PIL import Image as pil
from pynxtools_em.concepts.nxs_image_set import NxImageRealSpaceSet
from pynxtools_em.utils.get_scan_points import hexagonal_grid, square_grid, threed
from pynxtools_em.utils.get_sqr_grid import (
    regrid_onto_equisized_scan_points,
)
from pynxtools_em.utils.hfive_web_constants import (
    HFIVE_WEB_MAXIMUM_RGB,
    HFIVE_WEB_MAXIMUM_ROI,
)
from pynxtools_em.utils.hfive_web_utils import hfive_web_decorate_nxdata
from pynxtools_em.utils.image_processing import thumbnail

PROJECTION_VECTORS = [Vector3d.xvector(), Vector3d.yvector(), Vector3d.zvector()]
PROJECTION_DIRECTIONS = [
    ("X", Vector3d.xvector().data.flatten()),
    ("Y", Vector3d.yvector().data.flatten()),
    ("Z", Vector3d.zvector().data.flatten()),
]


def get_ipfdir_legend(ipf_key):
    """Generate IPF color map key for a specific ipf_key."""
    img = None
    fig = ipf_key.plot(return_figure=True)
    fig.savefig(
        "temporary.png",
        dpi=300,
        facecolor="w",
        edgecolor="w",
        orientation="landscape",
        format="png",
        transparent=False,
        bbox_inches="tight",
        pad_inches=0.1,
        metadata=None,
    )
    plt.close("all")
    img = np.asarray(
        thumbnail(pil.open("temporary.png", "r", ["png"]), size=HFIVE_WEB_MAXIMUM_RGB),
        np.uint8,
    )  # no flipping
    img = img[:, :, 0:3]  # discard alpha channel
    if os.path.exists("temporary.png"):
        os.remove("temporary.png")
    return img


def has_hfive_magic_header(file_path: str) -> bool:
    """Check if file_path has magic header matching HDF5."""
    with open(file_path, "rb", 0) as file:
        s = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)
        magic = s.read(4)
        if magic == b"\x89HDF":
            return True
    return False


def get_named_axis(inp: dict, dim: str) -> np.ndarray:
    """Return scaled but not offset-calibrated scan point coordinates along dim."""
    # TODO::deprecate at some point
    if square_grid(inp) or hexagonal_grid(inp):
        # TODO::this code does not work for scaled and origin-offset scan point positions!
        # TODO::below formula is only the same for sqr and hex grid if
        # s_{dim_name} already accounts for the fact that typically s_y = sqrt(3)/2 s_x !
        return np.asarray(
            np.linspace(0, inp[f"n_{dim}"] - 1, num=inp[f"n_{dim}"], endpoint=True)
            * inp[f"s_{dim}"],
            np.float32,
        )
    return None


def ebsd_roi_overview(inp: dict, id_mgn: dict, template: dict) -> dict:
    """Create an H5Web-capable ENTRY[entry]/ROI[roi*]/ebsd/indexing/roi."""
    # EBSD maps are collected using different scan strategies but RDMs may not be
    # able to show all of them at the provided size and grid type
    # here a default plot is generated taking the OIM data per scan point
    # and regridding on a square_grid with the maximum resolution supported by H5Web
    # this is never an upsampled but may represent a downsampled representation of the
    # actual ROI using some regridding scheme
    trg_grid = regrid_onto_equisized_scan_points(inp, HFIVE_WEB_MAXIMUM_ROI)

    contrast_modes = [
        (None, "n/a"),
        ("bc", "normalized_band_contrast"),
        ("ci", "normalized_confidence_index"),
        ("mad", "normalized_mean_angular_deviation"),
    ]
    contrast_mode = None
    for mode in contrast_modes:
        if mode[0] in trg_grid and contrast_mode is None:
            contrast_mode = mode
            break
    if contrast_mode is None:
        print(f"ebsd_roi_overview unable to generate plot for roi{roi_id} !")
        return template

    trg = f"/ENTRY[entry{id_mgn['entry_id']}]/ROI[roi{id_mgn['roi_id']}]/ebsd/indexing/roi"
    template[f"{trg}/title"] = f"Region-of-interest overview image"
    template[f"{trg}/@signal"] = "data"
    dims = ["x", "y"]
    if trg_grid["dimensionality"] == 3:
        dims.append("z")
    idx = 0
    for dim in dims:
        template[f"{trg}/@AXISNAME_indices[axis_{dim}_indices]"] = np.uint32(idx)
        idx += 1
    template[f"{trg}/@axes"] = []
    for dim in dims[::-1]:
        template[f"{trg}/@axes"].append(f"axis_{dim}")

    if trg_grid["dimensionality"] == 3:
        template[f"{trg}/data"] = {
            "compress": np.squeeze(
                np.asarray(
                    np.asarray(
                        (
                            trg_grid[contrast_mode[0]]
                            / np.max(trg_grid[contrast_mode[0]], axis=None)
                            * 255.0
                        ),
                        np.uint32,
                    ),
                    np.uint8,
                ),
                axis=3,
            ),
            "strength": 1,
        }
    else:
        template[f"{trg}/data"] = {
            "compress": np.reshape(
                np.asarray(
                    np.asarray(
                        (
                            trg_grid[contrast_mode[0]]
                            / np.max(trg_grid[contrast_mode[0]])
                            * 255.0
                        ),
                        np.uint32,
                    ),
                    np.uint8,
                ),
                (trg_grid["n_y"], trg_grid["n_x"]),
                order="C",
            ),
            "strength": 1,
        }
    template[f"{trg}/descriptor"] = contrast_mode[1]

    # 0 is y while 1 is x for 2d, 0 is z, 1 is y, while 2 is x for 3d
    template[f"{trg}/data/@long_name"] = f"Signal"
    hfive_web_decorate_nxdata(f"{trg}/data", template)

    scan_unit = trg_grid["s_unit"]
    if scan_unit == "um":
        scan_unit = "µm"
    for dim in dims:
        template[f"{trg}/AXISNAME[axis_{dim}]"] = {
            "compress": self.get_named_axis(trg_grid, dim),
            "strength": 1,
        }
        template[f"{trg}/AXISNAME[axis_{dim}]/@long_name"] = (
            f"Coordinate along {dim}-axis ({scan_unit})"
        )
        template[f"{trg}/AXISNAME[axis_{dim}]/@units"] = f"{scan_unit}"
    return template

    def process_roi_overview_eds_based(self, inp, template: dict) -> dict:
        trg = (
            f"/ENTRY[entry{self.entry_id}]/measurement/event_data_em_set/"
            f"EVENT_DATA_EM[event_data_em{self.id_mgn['event']}]/"
            f"IMAGE_SET[image_set{self.id_mgn['event_img']}]/image_2d"
        )
        template[f"{trg}/description"] = inp.tmp["source"]
        template[f"{trg}/title"] = f"Region-of-interest overview image"
        template[f"{trg}/@signal"] = "real"
        dims = [("i", 0), ("j", 1)]
        template[f"{trg}/@axes"] = []
        for dim in dims[::-1]:
            template[f"{trg}/@axes"].append(f"axis_{dim[0]}")
        template[f"{trg}/real"] = {
            "compress": inp.tmp["image_2d/real"].value,
            "strength": 1,
        }
        template[f"{trg}/real/@long_name"] = f"Signal"
        for dim in dims:
            template[f"{trg}/@AXISNAME_indices[axis_{dim[0]}_indices]"] = np.uint32(
                dim[1]
            )
            template[f"{trg}/AXISNAME[axis_{dim[0]}]"] = {
                "compress": inp.tmp[f"image_2d/axis_{dim[0]}"].value,
                "strength": 1,
            }
            template[f"{trg}/AXISNAME[axis_{dim[0]}]/@long_name"] = inp.tmp[
                f"image_2d/axis_{dim[0]}@long_name"
            ].value
        self.id_mgn["event_img"] += 1
        self.id_mgn["event"] += 1
        return template

    def process_roi_ebsd_maps(self, inp: dict, template: dict) -> dict:
        for ckey in inp.keys():
            if ckey.startswith("ebsd") and inp[ckey] != {}:
                if ckey.replace("ebsd", "").isdigit():
                    roi_id = int(ckey.replace("ebsd", ""))
                    if threed(inp[ckey]) is False:
                        self.onthefly_process_roi_ipfs_phases_twod(
                            inp[ckey], roi_id, template
                        )
                    else:
                        self.onthefly_process_roi_ipfs_phases_threed(
                            inp[ckey], roi_id, template
                        )
        return template

    def onthefly_process_roi_ipfs_phases_twod(
        self, inp: dict, roi_id: int, template: dict
    ) -> dict:
        dimensionality = inp["dimensionality"]
        print(f"Parse crystal_structure_models aka phases {dimensionality}D version...")
        nxem_phase_id = 0
        prfx = f"/ENTRY[entry{self.entry_id}]/ROI[roi{roi_id}]/ebsd/indexing"
        # bookkeeping is always reported for the original grid
        # because the eventual discretization for h5web is solely
        # for the purpose of showing users a readily consumable default plot
        # to judge for each possible dataset in the same way if the
        # dataset is worthwhile and potentially valuable for ones on research
        n_pts = inp["n_x"] * inp["n_y"]
        n_pts_indexed = np.sum(inp["phase_id"] != 0)
        print(f"n_pts {n_pts}, n_pts_indexed {n_pts_indexed}")
        template[f"{prfx}/number_of_scan_points"] = np.uint32(n_pts)
        template[f"{prfx}/indexing_rate"] = np.float64(n_pts_indexed / n_pts)
        grp_name = f"{prfx}/phaseID[phase{nxem_phase_id}]"
        template[f"{grp_name}/number_of_scan_points"] = np.uint32(
            np.sum(inp["phase_id"] == 0)
        )
        template[f"{grp_name}/phase_identifier"] = np.uint32(nxem_phase_id)
        template[f"{grp_name}/phase_name"] = f"notIndexed"

        print(f"----unique inp phase_id--->{np.unique(inp['phase_id'])}")
        for nxem_phase_id in np.arange(1, np.max(np.unique(inp["phase_id"])) + 1):
            # starting here at ID 1 because the subpasrsers have already normalized the
            # tech partner specific phase_id convention to follow NXem NeXus convention
            print(f"inp[phases].keys(): {inp['phases'].keys()}")
            if nxem_phase_id not in inp["phases"].keys():
                raise ValueError(f"{nxem_phase_id} is not a key in inp['phases'] !")
            trg = f"{prfx}/phaseID[phase{nxem_phase_id}]"
            template[f"{trg}/number_of_scan_points"] = np.uint32(
                np.sum(inp["phase_id"] == nxem_phase_id)
            )
            template[f"{trg}/phase_identifier"] = np.uint32(nxem_phase_id)
            template[f"{trg}/phase_name"] = (
                f"{inp['phases'][nxem_phase_id]['phase_name']}"
            )
            # internally the following function may discretize a coarser IPF
            # if the input grid inp is too large for h5web to display
            # this remove fine details in the EBSD maps but keep in mind
            # that the purpose of the default plot is to guide the user
            # of the potential usefulness of the dataset when searching in
            # a RDMS like NOMAD OASIS, the purpose is NOT to take the coarse-grained
            # discretization and use this for scientific data analysis!
            self.process_roi_phase_ipfs_twod(
                inp,
                roi_id,
                nxem_phase_id,
                inp["phases"][nxem_phase_id]["phase_name"],
                inp["phases"][nxem_phase_id]["space_group"],
                template,
            )
        return template

    def process_roi_phase_ipfs_twod(
        self,
        inp: dict,
        roi_id: int,
        nxem_phase_id: int,
        phase_name: str,
        space_group: int,
        template: dict,
    ) -> dict:
        print(f"Generate 2D IPF maps for {nxem_phase_id}, {phase_name}...")
        trg_grid = regrid_onto_equisized_scan_points(inp, HFIVE_WEB_MAXIMUM_RGB)

        rotations = Rotation.from_euler(
            euler=trg_grid["euler"][trg_grid["phase_id"] == nxem_phase_id],
            direction="lab2crystal",
            degrees=False,
        )
        print(f"shape rotations -----> {np.shape(rotations)}")

        for idx in np.arange(0, len(PROJECTION_VECTORS)):
            point_group = get_point_group(space_group, proper=False)
            ipf_key = plot.IPFColorKeyTSL(
                point_group.laue, direction=PROJECTION_VECTORS[idx]
            )
            img = get_ipfdir_legend(ipf_key)

            rgb_px_with_phase_id = np.asarray(
                np.asarray(ipf_key.orientation2color(rotations) * 255.0, np.uint32),
                np.uint8,
            )
            print(f"shape rgb_px_with_phase_id -----> {np.shape(rgb_px_with_phase_id)}")

            ipf_rgb_map = np.asarray(
                np.asarray(
                    np.zeros((trg_grid["n_y"] * trg_grid["n_x"], 3)) * 255.0, np.uint32
                ),
                np.uint8,
            )
            # background is black instead of white (which would be more pleasing)
            # but IPF color maps have a whitepoint which encodes in fact an orientation
            # and because of that we may have a map from a single crystal characterization
            # whose orientation could be close to the whitepoint which becomes a fully white
            # seemingly "empty" image, therefore we use black as empty, i.e. white reports an
            # orientation
            ipf_rgb_map[trg_grid["phase_id"] == nxem_phase_id, :] = rgb_px_with_phase_id
            ipf_rgb_map = np.reshape(
                ipf_rgb_map, (trg_grid["n_y"], trg_grid["n_x"], 3), order="C"
            )
            # 0 is y, 1 is x, only valid for REGULAR_TILING and FLIGHT_PLAN !

            trg = (
                f"/ENTRY[entry{self.entry_id}]/ROI[roi{roi_id}]/ebsd/indexing"
                f"/phaseID[phase{nxem_phase_id}]/ipfID[ipf{idx + 1}]"
            )
            template[f"{trg}/projection_direction"] = np.asarray(
                PROJECTION_VECTORS[idx].data.flatten(), np.float32
            )

            # add the IPF color map
            mpp = f"{trg}/map"
            template[f"{mpp}/title"] = (
                f"Inverse pole figure {PROJECTION_DIRECTIONS[idx][0]} {phase_name}"
            )
            template[f"{mpp}/@signal"] = "data"
            dims = ["x", "y"]
            template[f"{mpp}/@axes"] = []
            for dim in dims[::-1]:
                template[f"{mpp}/@axes"].append(f"axis_{dim}")
            enum = 0
            for dim in dims:
                template[f"{mpp}/@AXISNAME_indices[axis_{dim}_indices]"] = np.uint32(
                    enum
                )
                enum += 1
            template[f"{mpp}/DATA[data]"] = {"compress": ipf_rgb_map, "strength": 1}
            hfive_web_decorate_nxdata(f"{mpp}/DATA[data]", template)

            scan_unit = trg_grid["s_unit"]  # TODO::this is not necessarily correct
            # could be a scale-invariant synthetic microstructure whose simulation
            # would work on multiple length-scales as atoms are not resolved directly!
            if scan_unit == "um":
                scan_unit = "µm"
            for dim in dims:
                template[f"{mpp}/AXISNAME[axis_{dim}]"] = {
                    "compress": self.get_named_axis(trg_grid, f"{dim}"),
                    "strength": 1,
                }
                template[f"{mpp}/AXISNAME[axis_{dim}]/@long_name"] = (
                    f"Coordinate along {dim}-axis ({scan_unit})"
                )
                template[f"{mpp}/AXISNAME[axis_{dim}]/@units"] = f"{scan_unit}"

            # add the IPF color map legend/key
            lgd = f"{trg}/legend"
            template[f"{lgd}/title"] = (
                f"Inverse pole figure {PROJECTION_DIRECTIONS[idx][0]} {phase_name}"
            )
            # template[f"{trg}/title"] = f"Inverse pole figure color key with SST"
            template[f"{lgd}/@signal"] = "data"
            template[f"{lgd}/@axes"] = []
            dims = ["x", "y"]
            for dim in dims[::-1]:
                template[f"{lgd}/@axes"].append(f"axis_{dim}")
            enum = 0
            for dim in dims:
                template[f"{lgd}/@AXISNAME_indices[axis_{dim}_indices]"] = np.uint32(
                    enum
                )
                enum += 1
            template[f"{lgd}/data"] = {"compress": img, "strength": 1}
            hfive_web_decorate_nxdata(f"{lgd}/data", template)

            dims_idxs = {"x": 1, "y": 0}
            for dim, idx in dims_idxs.items():
                template[f"{lgd}/AXISNAME[axis_{dim}]"] = {
                    "compress": np.asarray(
                        np.linspace(
                            0,
                            np.shape(img)[idx] - 1,
                            num=np.shape(img)[idx],
                            endpoint=True,
                        ),
                        np.uint32,
                    ),
                    "strength": 1,
                }
                template[f"{lgd}/AXISNAME[axis_{dim}]/@long_name"] = (
                    f"Pixel coordinate along {dim[0]}-axis"
                )
        return template

    def onthefly_process_roi_ipfs_phases_threed(
        self, inp: dict, roi_id: int, template: dict
    ) -> dict:
        # this function is almost the same as its twod version we keep it for
        # now an own function until the rediscretization also works for the 3D grid
        dimensionality = inp["dimensionality"]
        print(f"Parse crystal_structure_models aka phases {dimensionality}D version...")
        # see comments in twod version of this function
        nxem_phase_id = 0
        prfx = f"/ENTRY[entry{self.entry_id}]/ROI[roi{roi_id}]/ebsd/indexing"
        n_pts = inp["n_x"] * inp["n_y"] * inp["n_z"]
        n_pts_indexed = np.sum(inp["phase_id"] != 0)
        print(f"n_pts {n_pts}, n_pts_indexed {n_pts_indexed}")
        template[f"{prfx}/number_of_scan_points"] = np.uint32(n_pts)
        template[f"{prfx}/indexing_rate"] = np.float64(n_pts_indexed / n_pts)
        grp_name = f"{prfx}/phaseID[phase{nxem_phase_id}]"
        template[f"{grp_name}/number_of_scan_points"] = np.uint32(
            np.sum(inp["phase_id"] == 0)
        )
        template[f"{grp_name}/phase_identifier"] = np.uint32(nxem_phase_id)
        template[f"{grp_name}/phase_name"] = f"notIndexed"

        print(f"----unique inp phase_id--->{np.unique(inp['phase_id'])}")
        for nxem_phase_id in np.arange(1, np.max(np.unique(inp["phase_id"])) + 1):
            print(f"inp[phases].keys(): {inp['phases'].keys()}")
            if nxem_phase_id not in inp["phases"].keys():
                raise ValueError(f"{nxem_phase_id} is not a key in inp['phases'] !")
            trg = f"{prfx}/phaseID[phase{nxem_phase_id}]"
            template[f"{trg}/number_of_scan_points"] = np.uint32(
                np.sum(inp["phase_id"] == nxem_phase_id)
            )
            template[f"{trg}/phase_identifier"] = np.uint32(nxem_phase_id)
            template[f"{trg}/phase_name"] = (
                f"{inp['phases'][nxem_phase_id]['phase_name']}"
            )

            self.process_roi_phase_ipfs_threed(
                inp,
                roi_id,
                nxem_phase_id,
                inp["phases"][nxem_phase_id]["phase_name"],
                inp["phases"][nxem_phase_id]["space_group"],
                template,
            )
        return template

    def process_roi_phase_ipfs_threed(
        self,
        inp: dict,
        roi_id: int,
        nxem_phase_id: int,
        phase_name: str,
        space_group: int,
        template: dict,
    ) -> dict:
        """Generate inverse pole figures (IPF) for 3D mappings for specific phase."""
        # equivalent to the case in twod, one needs at if required regridding/downsampling
        # code here when any of the ROI's number of pixels along an edge > HFIVE_WEB_MAXIMUM_RGB
        # TODO: I have not seen any dataset yet where is limit is exhausted, the largest
        # dataset is a 3D SEM/FIB study from a UK project this is likely because to
        # get an EBSD map as large one already scans quite long for one section as making
        # a compromise is required and thus such hypothetical large serial-sectioning
        # studies would block the microscope for a very long time
        # however I have seen examples from Hadi Pirgazi with L. Kestens from Leuven
        # where indeed large but thin 3d slabs were characterized
        print(f"Generate 3D IPF map for {nxem_phase_id}, {phase_name}...")
        rotations = Rotation.from_euler(
            euler=inp["euler"][inp["phase_id"] == nxem_phase_id],
            direction="lab2crystal",
            degrees=False,
        )
        print(f"shape rotations -----> {np.shape(rotations)}")

        for idx in np.arange(0, len(PROJECTION_VECTORS)):
            point_group = get_point_group(space_group, proper=False)
            ipf_key = plot.IPFColorKeyTSL(
                point_group.laue, direction=PROJECTION_VECTORS[idx]
            )
            img = get_ipfdir_legend(ipf_key)

            rgb_px_with_phase_id = np.asarray(
                np.asarray(ipf_key.orientation2color(rotations) * 255.0, np.uint32),
                np.uint8,
            )
            print(f"shape rgb_px_with_phase_id -----> {np.shape(rgb_px_with_phase_id)}")

            ipf_rgb_map = np.asarray(
                np.asarray(
                    np.zeros((inp["n_z"] * inp["n_y"] * inp["n_x"], 3)) * 255.0,
                    np.uint32,
                ),
                np.uint8,
            )
            # background is black instead of white (which would be more pleasing)
            # but IPF color maps have a whitepoint which encodes in fact an orientation
            # and because of that we may have a single crystal with an orientation
            # close to the whitepoint which become a fully white seemingly "empty" image
            ipf_rgb_map[inp["phase_id"] == nxem_phase_id, :] = rgb_px_with_phase_id
            ipf_rgb_map = np.reshape(
                ipf_rgb_map, (inp["n_z"], inp["n_y"], inp["n_x"], 3), order="C"
            )
            # 0 is z, 1 is y, while 2 is x !

            trg = (
                f"/ENTRY[entry{self.entry_id}]/ROI[roi{roi_id}]/ebsd/indexing"
                f"/phaseID[phase{nxem_phase_id}]/ipfID[ipf{idx + 1}]"
            )
            template[f"{trg}/projection_direction"] = np.asarray(
                PROJECTION_VECTORS[idx].data.flatten(), np.float32
            )

            # add the IPF color map
            mpp = f"{trg}/map"
            template[f"{mpp}/title"] = (
                f"Inverse pole figure {PROJECTION_DIRECTIONS[idx][0]} {phase_name}"
            )
            template[f"{mpp}/@signal"] = "data"
            dims = ["x", "y", "z"]
            template[f"{mpp}/@axes"] = []
            for dim in dims[::-1]:
                template[f"{mpp}/@axes"].append(f"axis_{dim}")
            enum = 0
            for dim in dims:
                template[f"{mpp}/@AXISNAME_indices[axis_{dim}_indices]"] = np.uint32(
                    enum
                )
                enum += 1
            template[f"{mpp}/DATA[data]"] = {"compress": ipf_rgb_map, "strength": 1}
            hfive_web_decorate_nxdata(f"{mpp}/DATA[data]", template)

            scan_unit = inp["s_unit"]  # TODO::this is not necessarily correct
            # could be a scale-invariant synthetic microstructure whose simulation
            # would work on multiple length-scales as atoms are not resolved directly!
            if scan_unit == "um":
                scan_unit = "µm"
            for dim in dims:
                template[f"{mpp}/AXISNAME[axis_{dim}]"] = {
                    "compress": self.get_named_axis(inp, f"{dim}"),
                    "strength": 1,
                }
                template[f"{mpp}/AXISNAME[axis_{dim}]/@long_name"] = (
                    f"Coordinate along {dim}-axis ({scan_unit})"
                )
                template[f"{mpp}/AXISNAME[axis_{dim}]/@units"] = f"{scan_unit}"

            # add the IPF color map legend/key
            lgd = f"{trg}/legend"
            template[f"{lgd}/title"] = (
                f"Inverse pole figure {PROJECTION_DIRECTIONS[idx][0]} {phase_name}"
            )
            # template[f"{trg}/title"] = f"Inverse pole figure color key with SST"
            template[f"{lgd}/@signal"] = "data"
            template[f"{lgd}/@axes"] = []
            dims = ["x", "y"]
            for dim in dims[::-1]:
                template[f"{lgd}/@axes"].append(f"axis_{dim}")
            enum = 0
            for dim in dims:
                template[f"{lgd}/@AXISNAME_indices[axis_{dim}_indices]"] = np.uint32(
                    enum
                )
                enum += 1
            template[f"{lgd}/data"] = {"compress": img, "strength": 1}
            hfive_web_decorate_nxdata(f"{lgd}/data", template)

            dims_idxs = {"x": 1, "y": 0}
            for dim, idx in dims_idxs.items():
                template[f"{lgd}/AXISNAME[axis_{dim}]"] = {
                    "compress": np.asarray(
                        np.linspace(
                            0,
                            np.shape(img)[idx] - 1,
                            num=np.shape(img)[idx],
                            endpoint=True,
                        ),
                        np.uint32,
                    ),
                    "strength": 1,
                }
                template[f"{lgd}/AXISNAME[axis_{dim}]/@long_name"] = (
                    f"Pixel along {dim}-axis"
                )
                template[f"{lgd}/AXISNAME[axis_{dim}]/@units"] = "px"
        return template

    def process_roi_eds_spectra(self, inp: dict, template: dict) -> dict:
        for ckey in inp.keys():
            if ckey.startswith("eds_spc") and inp[ckey] != {}:
                trg = (
                    f"/ENTRY[entry{self.entry_id}]/measurement/event_data_em_set/"
                    f"EVENT_DATA_EM[event_data_em{self.id_mgn['event']}]/SPECTRUM_SET"
                    f"[spectrum_set{self.id_mgn['event_spc']}]/spectrum_0d"
                )
                template[f"{trg}/description"] = inp[ckey].tmp["source"]
                template[f"{trg}/title"] = f"Region-of-interest overview image"
                template[f"{trg}/@signal"] = "real"
                template[f"{trg}/@axes"] = ["axis_energy"]
                template[f"{trg}/real"] = {
                    "compress": inp[ckey].tmp["spectrum_0d/real"].value,
                    "strength": 1,
                }
                template[f"{trg}/real/@long_name"] = (
                    inp[ckey].tmp["spectrum_0d/real@long_name"].value
                )
                template[f"{trg}/@AXISNAME_indices[axis_energy_indices]"] = np.uint32(0)
                template[f"{trg}/AXISNAME[axis_energy]"] = {
                    "compress": inp[ckey].tmp[f"spectrum_0d/axis_energy"].value,
                    "strength": 1,
                }
                template[f"{trg}/AXISNAME[axis_energy]/@long_name"] = (
                    inp[ckey].tmp[f"spectrum_0d/axis_energy@long_name"].value
                )
                self.id_mgn["event_spc"] += 1
                self.id_mgn["event"] += 1
        return template

    def process_roi_eds_maps(self, inp: dict, template: dict) -> dict:
        for ckey in inp.keys():
            if ckey.startswith("eds_map") and inp[ckey] != {}:
                trg = (
                    f"/ENTRY[entry{self.entry_id}]/ROI[roi{self.id_mgn['roi']}]/"
                    f"eds/indexing"
                )
                template[f"{trg}/source"] = inp[ckey].tmp["source"]
                for img in inp[ckey].tmp["IMAGE_SET"]:
                    if not isinstance(img, NxImageRealSpaceSet):
                        continue
                    trg = (
                        f"/ENTRY[entry{self.entry_id}]/ROI[roi{self.id_mgn['roi']}]/eds/"
                        f"indexing/IMAGE_SET[image_set{self.id_mgn['eds_img']}]"
                    )
                    template[f"{trg}/source"] = img.tmp["source"]
                    template[f"{trg}/description"] = img.tmp["description"]
                    template[f"{trg}/energy_range"] = img.tmp["energy_range"].value
                    template[f"{trg}/energy_range/@units"] = img.tmp[
                        "energy_range"
                    ].unit
                    template[f"{trg}/iupac_line_candidates"] = img.tmp[
                        "iupac_line_candidates"
                    ]
                    template[f"{trg}/image_2d/@signal"] = "real"
                    template[f"{trg}/image_2d/@axes"] = ["axis_j", "axis_i"]
                    template[f"{trg}/image_2d/title"] = (
                        f"EDS map {img.tmp['description']}"
                    )
                    template[f"{trg}/image_2d/real"] = {
                        "compress": img.tmp["image_2d/real"].value,
                        "strength": 1,
                    }
                    template[f"{trg}/image_2d/real/@long_name"] = f"Signal"
                    dims = [("i", 0), ("j", 1)]
                    for dim in dims:
                        template[
                            f"{trg}/image_2d/@AXISNAME_indices[axis_{dim[0]}_indices]"
                        ] = np.uint32(dim[1])
                        template[f"{trg}/image_2d/AXISNAME[axis_{dim[0]}]"] = {
                            "compress": img.tmp[f"image_2d/axis_{dim[0]}"].value,
                            "strength": 1,
                        }
                        template[
                            f"{trg}/image_2d/AXISNAME[axis_{dim[0]}]/@long_name"
                        ] = img.tmp[f"image_2d/axis_{dim[0]}@long_name"].value
                    self.id_mgn["eds_img"] += 1
                self.id_mgn["roi"] += 1

        return template
