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
from typing import Any, Dict

import matplotlib.pyplot as plt  # in the hope that this closes figures with orix plot
import numpy as np
from orix import plot
from orix.quaternion import Rotation
from orix.quaternion.symmetry import get_point_group
from orix.vector import Vector3d
from PIL import Image as pil
from pynxtools_em.utils.hfive_web import (
    HFIVE_WEB_MAXIMUM_RGB,
    HFIVE_WEB_MAXIMUM_ROI,
)
from pynxtools_em.utils.hfive_web_utils import hfive_web_decorate_nxdata
from pynxtools_em.utils.image_processing import thumbnail
from pynxtools_em.utils.pint_custom_unit_registry import ureg
from scipy.spatial import KDTree

PROJECTION_VECTORS = [Vector3d.xvector(), Vector3d.yvector(), Vector3d.zvector()]
PROJECTION_DIRECTIONS = [
    ("X", Vector3d.xvector().data.flatten()),
    ("Y", Vector3d.yvector().data.flatten()),
    ("Z", Vector3d.zvector().data.flatten()),
]

# typical scan schemes used for EBSD
HEXAGONAL_FLAT_TOP_TILING = "hexagonal_flat_top_tiling"
SQUARE_TILING = "square_tiling"
REGULAR_TILING = "regular_tiling"
DEFAULT_LENGTH_UNIT = ureg.micrometer

# most frequently this is the sequence of set scan positions with actual positions
# based on grid type, spacing, and tiling
FLIGHT_PLAN = "start_top_left_stack_x_left_to_right_stack_x_line_along_end_bottom_right"


class EbsdPointCloud:
    """Cache for storing a single indexed EBSD point cloud with mark data."""

    def __init__(self):
        self.dimensionality: int = 0
        self.grid_type = None
        # the next two lines encode the typical assumption that is not reported in tech partner file!
        self.n: Dict[str, Any] = {}  # number of grid points along "x", "y", "z"
        self.s: Dict[str, Any] = {}  # scan step along "x", "y", "z"
        self.phase = []  # collection of phase class instances in order of self.phases
        self.space_group = []  # collection of space group in order of self.phases
        self.phases = {}  #  named phases
        self.euler = None  # Bunge-Euler ZXZ angle for each scan point np.nan otherwise
        self.phase_id = None  # phase_id for best solution found for each scan point
        self.pos: Dict[
            str, Any
        ] = {}  # "x", "y", "z" pos for each scan point unmodified/not rediscretized
        self.descr_type = None  # NXem_ebsd/roi/descriptor (band contrast, CI, MAD)
        self.descr_value = None


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


def regrid_onto_equisized_scan_points(
    src_grid: EbsdPointCloud, max_edge_discr: int
) -> dict:
    """Discretize point cloud in R^d (d=1, 2, 3) and mark data to grid with equisized bins."""

    if src_grid.dimensionality not in [1, 2]:
        print(
            f"The 1D and 3D gridding is currently not implemented because we do not "
            f"have a large enough dataset to test the 3D case with !"
        )
        return src_grid
    # take discretization of the source grid as a guide for the target_grid
    # optimization possible if square grid and matching maximum_extent

    dims = ["x", "y", "z"][0 : src_grid.dimensionality]
    tuples = []
    for dim_idx, dim in enumerate(dims):
        if dim in src_grid.n:
            tuples.append((src_grid.n[dim], dim_idx))
    max_extent, max_dim = sorted(tuples, key=lambda x: x[0])[::-1][0]  # descendingly

    # too large grid needs to be capped when gridded
    # cap to the maximum extent to comply with H5Web technical constraints
    if max_extent >= max_edge_discr:
        max_extent = max_edge_discr

    # all non-square grids or too large square grids will be
    # discretized onto a regular grid with square or cubic pixel/voxel
    for dim in dims:
        if dim in src_grid.pos:
            if src_grid.pos[dim].units != ureg.Quantity(1.0, ureg.micrometer).units:
                raise ValueError(f"Gridding demands values in micrometer !")

    aabb = {}
    for dim in dims:
        aabb[f"{dim}"] = [
            np.min(
                src_grid.pos[f"{dim}"].magnitude - 0.5 * src_grid.s[f"{dim}"].magnitude
            ),
            np.max(
                src_grid.pos[f"{dim}"].magnitude + 0.5 * src_grid.s[f"{dim}"].magnitude
            ),
        ]
    print(f"{aabb}")

    trg_s = {}
    trg_n = {}
    if src_grid.dimensionality == 1:
        trg_s["x"] = (aabb["x"][1] - aabb["x"][0]) / max_extent
        trg_n["x"] = max_extent
    elif src_grid.dimensionality == 2:
        if aabb["x"][1] - aabb["x"][0] >= aabb["y"][1] - aabb["y"][0]:
            trg_s["x"] = (aabb["x"][1] - aabb["x"][0]) / max_extent
            trg_s["y"] = (aabb["x"][1] - aabb["x"][0]) / max_extent
            trg_n["x"] = max_extent
            trg_n["y"] = int(np.ceil((aabb["y"][1] - aabb["y"][0]) / trg_s["x"]))
        else:
            trg_s["x"] = (aabb["y"][1] - aabb["y"][0]) / max_extent
            trg_s["y"] = (aabb["y"][1] - aabb["y"][0]) / max_extent
            trg_n["x"] = int(np.ceil((aabb["x"][1] - aabb["x"][0]) / trg_s["x"]))
            trg_n["y"] = max_extent
    elif src_grid.dimensionality == 3:
        print("TODO !!!!")

    print(f"H5Web default plot generation")
    for dim in dims:
        print(f"src_s {dim}: {src_grid.s[dim]} >>>> trg_s {dim}: {trg_s[dim]}")
        print(f"src_n {dim}: {src_grid.n[dim]} >>>> trg_n {dim}: {trg_n[dim]}")
    # the above estimate is not exactly correct (may create a slight real space shift)
    # of the EBSD map TODO:: regrid the real world axis-aligned bounding box aabb with
    # a regular tiling of squares or hexagons
    # https://stackoverflow.com/questions/18982650/differences-between-matlab-and-numpy-and-pythons-round-function
    # MTex/Matlab round not exactly the same as numpy round but reasonably close

    # scan point positions were normalized by tech partner parsers such that they
    # always build on pixel coordinates calibrated for step size not by giving absolute positions
    # in the sample surface frame of reference as this is typically not yet consistently documented
    # because we assume in addition that we always start at the top left corner the zeroth/first
    # coordinate is always 0., 0. !
    if src_grid.dimensionality == 1:
        trg_pos = np.column_stack(
            np.linspace(0, trg_n["x"] - 1, num=trg_n["x"], endpoint=True) * trg_s["x"],
            1,
        )
    elif src_grid.dimensionality == 2:
        trg_pos = np.column_stack(
            (
                np.tile(
                    np.linspace(0, trg_n["x"] - 1, num=trg_n["x"], endpoint=True)
                    * trg_s["x"],
                    trg_n["y"],
                ),
                np.repeat(
                    np.linspace(0, trg_n["y"] - 1, num=trg_n["y"], endpoint=True)
                    * trg_s["y"],
                    trg_n["x"],
                ),
            )
        )
    # TODO:: if scan_point_{dim} are calibrated this approach
    # here would shift the origin to 0, 0 implicitly which may not be desired
    if src_grid.dimensionality == 1:
        tree = KDTree(np.column_stack((src_grid.pos["x"])))
    elif src_grid.dimensionality == 2:
        tree = KDTree(np.column_stack((src_grid.pos["x"], src_grid.pos["y"])))
    d, idx = tree.query(trg_pos, k=1)
    if np.sum(idx == tree.n) > 0:
        raise ValueError(f"kdtree query left some query points without a neighbor!")
    del d
    del tree

    # rebuild src_grid container with only the relevant src_grid selected from src_grid
    trg_grid = EbsdPointCloud()
    trg_grid.dimensionality = src_grid.dimensionality

    for dim_idx, dim in enumerate(dims):
        trg_grid.s[dim] = ureg.Quantity(trg_s[dim], ureg.micrometer)
        trg_grid.n[dim] = trg_n[dim]
        trg_grid.pos[dim] = ureg.Quantity(
            np.asarray(trg_pos[dim_idx], np.float64), ureg.micrometer
        )
    if hasattr(src_grid, "euler"):
        trg_grid.euler = np.empty((np.shape(trg_pos)[0], 3), np.float32)
        trg_grid.euler.fill(np.nan)
        trg_grid.euler = ureg.Quantity(
            np.asarray(src_grid.euler.magnitude[idx, :], np.float32), ureg.radian
        )
        if np.isnan(trg_grid.euler).any():
            raise ValueError(f"Gridding left scan points with incorrect euler !")
    if hasattr(src_grid, "phase_id"):
        trg_grid.phase_id = np.empty((np.shape(trg_pos)[0],), np.int32)
        trg_grid.phase_id.fill(np.int32(-2))
        # pyxem_id phase_id are at least as large -1
        trg_grid.phase_id = np.asarray(src_grid.phase_id[idx], np.int32)
        if np.sum(trg_grid.phase_id == -2) > 0:
            raise ValueError(f"Gridding left scan points with incorrect phase_id !")
    if src_grid.descr_type == "band_contrast":
        # bc typically positive
        trg_grid.descr_type = "band_contrast"
        trg_grid.descr_value = np.empty((np.shape(trg_pos)[0]), np.uint32)
        trg_grid.descr_value.fill(np.uint32(-1))
        trg_grid.descr_value = ureg.Quantity(
            np.asarray(src_grid.descr_value[idx], np.uint32)
        )
    elif src_grid.descr_type == "confidence_index":
        trg_grid.descr_type = "confidence_index"
        trg_grid.descr_value = np.empty((np.shape(trg_pos)[0]), np.float32)
        trg_grid.descr_value.fill(np.nan)
        trg_grid.descr_value = ureg.Quantity(
            np.asarray(src_grid.descr_value[idx], np.float32)
        )
    elif src_grid.descr_type == "mean_angular_deviation":
        trg_grid.descr_type = "mean_angular_deviation"
        trg_grid.descr_value = np.empty((np.shape(trg_pos)[0]), np.float32)
        trg_grid.descr_value.fill(np.nan)
        trg_grid.descr_value = ureg.Quantity(
            np.asarray(src_grid.descr_value[idx], np.float32), ureg.radian
        )
    else:
        trg_grid.descr_type = None
        trg_grid.descr_value = None
    trg_grid.phase = src_grid.phase
    trg_grid.space_group = src_grid.space_group
    trg_grid.phases = src_grid.phases
    return trg_grid


def ebsd_roi_overview(inp: EbsdPointCloud, id_mgn: dict, template: dict) -> dict:
    """Create an H5Web-capable ENTRY[entry]/ROI[roi*]/ebsd/indexing/roi."""
    # EBSD maps are collected using different scan strategies but RDMs may not be
    # able to show all of them at the provided size and grid type
    # here a default plot is generated taking the OIM data per scan point
    # and regridding on a square_grid with the maximum resolution supported by H5Web
    # this is never an upsampled but may represent a downsampled representation of the
    # actual ROI using some regridding scheme
    if inp.dimensionality not in [1, 2, 3]:
        return template
    trg_grid: EbsdPointCloud = regrid_onto_equisized_scan_points(
        inp, HFIVE_WEB_MAXIMUM_ROI
    )
    if not trg_grid.descr_type:
        return template

    trg = f"/ENTRY[entry{id_mgn['entry_id']}]/ROI[roi{id_mgn['roi_id']}]/ebsd/indexing/roi"
    template[f"{trg}/descriptor"] = trg_grid.descr_type
    template[f"{trg}/title"] = (
        f"Region-of-interest overview image ({trg_grid.descr_type})"
    )
    template[f"{trg}/data/@long_name"] = f"Signal"

    template[f"{trg}/@signal"] = "data"
    dims = ["x", "y", "z"][0 : trg_grid.dimensionality]
    for idx, dim in enumerate(dims):
        template[f"{trg}/@AXISNAME_indices[axis_{dim}_indices]"] = np.uint32(idx)
        template[f"{trg}/AXISNAME[axis_{dim}]"] = {
            "compress": np.asarray(
                np.linspace(0, trg_grid.n[dim] - 1, num=trg_grid.n[dim], endpoint=True)
                * trg_grid.s[dim]
            ),
            "strength": 1,
        }
        template[f"{trg}/AXISNAME[axis_{dim}]/@long_name"] = (
            f"Point coordinate along {dim}-axis ({trg_grid.pos[dim].units})"
        )
        template[f"{trg}/AXISNAME[axis_{dim}]/@units"] = f"{trg_grid.pos[dim].units}"
    template[f"{trg}/@axes"] = []
    for dim in dims[::-1]:
        template[f"{trg}/@axes"].append(f"axis_{dim}")

    if trg_grid.dimensionality == 1:
        template[f"{trg}/data"] = {
            "compress": trg_grid.descr_value.magnitude,
            "strength": 1,
        }
    elif trg_grid.dimensionality == 2:
        template[f"{trg}/data"] = {
            "compress": np.reshape(
                np.asarray(trg_grid.descr_value.magnitude),
                (trg_grid.n["y"], trg_grid.n["x"]),
                order="C",
            ),
            "strength": 1,
        }
    else:  # 3d
        template[f"{trg}/data"] = {
            "compress": np.reshape(
                np.asarray(trg_grid.descr_value.magnitude),
                (trg_grid.n["z"], trg_grid.n["y"], trg_grid.n["x"]),
                order="C",
            ),
            "strength": 1,
        }
    return template


def ebsd_roi_phase_ipf(inp: dict, id_mgn: dict, template: dict) -> dict:
    dimensionality = inp["dimensionality"]
    print(f"Parse crystal_structure_models aka phases {dimensionality}D version...")
    nxem_phase_id = 0
    prfx = f"/ENTRY[entry{id_mgn['entry_id']}]/ROI[roi{id_mgn['roi_id']}]/ebsd/indexing"
    # bookkeeping for how many scan points solutions were found is always for src_grid
    # because the eventual discretization for h5web is solely
    # for the purpose of showing users a readily consumable default plot
    # to judge for each possible dataset in the same way if the
    # dataset is worthwhile and potentially valuable for ones on research
    n_pts = 0
    if dimensionality == 2:
        n_pts = inp["n_x"] * inp["n_y"]
    elif dimensionality == 3:
        n_pts = inp["n_x"] * inp["n_y"] * inp["n_z"]
    else:
        raise ValueError(f"Hitting unimplemented case {dimensionality} !")
    if n_pts == 0:
        print(f"No grid points !")
        return template

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
        # starting here at ID 1 because the specific parsers have already normalized the
        # tech-partner specific phase_id conventions to follow the NXem NeXus convention
        # that is 0 is notIndexed, all other phase contiguously, start count from 1
        print(f"inp[phases].keys(): {inp['phases'].keys()}")
        if nxem_phase_id not in inp["phases"]:
            raise ValueError(f"{nxem_phase_id} is not a key in inp['phases'] !")
        trg = f"{prfx}/phaseID[phase{nxem_phase_id}]"
        template[f"{trg}/number_of_scan_points"] = np.uint32(
            np.sum(inp["phase_id"] == nxem_phase_id)
        )
        template[f"{trg}/phase_identifier"] = np.uint32(nxem_phase_id)
        template[f"{trg}/phase_name"] = f"{inp['phases'][nxem_phase_id]['phase_name']}"
        # internally the following function may discretize a coarser IPF
        # if the input grid inp is too large for h5web to display
        # this remove fine details in the EBSD maps but keep in mind
        # that the purpose of the default plot is to guide the user
        # of the potential usefulness of the dataset when searching in
        # a RDMS like NOMAD OASIS, the purpose is NOT to take the coarse-grained
        # discretization and use this for scientific data analysis!
        process_roi_phase_ipfs_twod(
            inp,
            id_mgn["roi_id"],
            nxem_phase_id,
            inp["phases"][nxem_phase_id]["phase_name"],
            inp["phases"][nxem_phase_id]["space_group"],
            template,
        )
    return template


def process_roi_phase_ipfs_twod(
    inp: dict,
    id_mgn: int,
    nxem_phase_id: int,
    phase_name: str,
    space_group: int,
    template: dict,
) -> dict:
    dimensionality = inp["dimensionality"]
    if dimensionality == 2:
        trg_grid = regrid_onto_equisized_scan_points(inp, HFIVE_WEB_MAXIMUM_RGB)
        trg_shape = (trg_grid["n_y"], trg_grid["n_x"], 3)
        trg_dims = (trg_grid["n_y"] * trg_grid["n_x"], 3)
    elif dimensionality == 3:
        trg_grid = inp
        #  grid would be required but havent see the plot limits exhausted because of the
        # measurement time it would take collect such large maps especially in the
        # serial-sectioning direction
        trg_shape = (trg_grid["n_z"], trg_grid["n_y"], trg_grid["n_x"], 3)
        trg_dims = (trg_grid["n_z"] * trg_grid["n_y"] * trg_grid["n_x"], 3)
    else:
        raise ValueError(f"Hitting unimplemented case {dimensionality} !")
    print(f"Generate {dimensionality}D IPF maps for {nxem_phase_id}, {phase_name}...")

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
            np.asarray(np.zeros(trg_dims) * 255.0, np.uint32), np.uint8
        )
        # background is black instead of white (which would be more pleasing)
        # but IPF color maps have a whitepoint which encodes in fact an orientation
        # and because of that we may have a map from a single crystal characterization
        # whose orientation could be close to the whitepoint which becomes a fully white
        # seemingly "empty" image, therefore we use black as empty, i.e. white reports an
        # orientation
        ipf_rgb_map[trg_grid["phase_id"] == nxem_phase_id, :] = rgb_px_with_phase_id
        ipf_rgb_map = np.reshape(ipf_rgb_map, trg_shape, order="C")
        # 0 is y, 1 is x, only valid for REGULAR_TILING and FLIGHT_PLAN !

        trg = (
            f"/ENTRY[entry{id_mgn['entry_id']}]/ROI[roi{id_mgn['roi_id']}]/ebsd/indexing"
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
        if dimensionality == 3:
            dims.append("z")
        template[f"{mpp}/@axes"] = []
        for dim in dims[::-1]:
            template[f"{mpp}/@axes"].append(f"axis_{dim}")
        for enum, dim in enumerate(dims):
            template[f"{mpp}/@AXISNAME_indices[axis_{dim}_indices]"] = np.uint32(enum)
        template[f"{mpp}/DATA[data]"] = {"compress": ipf_rgb_map, "strength": 1}
        hfive_web_decorate_nxdata(f"{mpp}/DATA[data]", template)

        scan_unit = trg_grid["s_unit"]  # TODO::this is not necessarily correct
        # could be a scale-invariant synthetic microstructure whose simulation
        # would work on multiple length-scales as atoms are not resolved directly!
        if scan_unit == "um":
            scan_unit = "µm"
        for dim in dims:
            template[f"{mpp}/AXISNAME[axis_{dim}]"] = {
                "compress": get_named_axis(trg_grid, f"{dim}"),
                "strength": 1,
            }
            template[f"{mpp}/AXISNAME[axis_{dim}]/@long_name"] = (
                f"Coordinate along {dim}-axis ({trg_grid['s_{dim}'].units})"
            )
            template[f"{mpp}/AXISNAME[axis_{dim}]/@units"] = (
                f"{trg_grid['s_{dim}'].units}"
            )

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
            template[f"{lgd}/@AXISNAME_indices[axis_{dim}_indices]"] = np.uint32(enum)
            enum += 1
        template[f"{lgd}/data"] = {"compress": img, "strength": 1}
        hfive_web_decorate_nxdata(f"{lgd}/data", template)

        dims_idxs = {"x": 1, "y": 0}
        for dim, enum in dims_idxs.items():
            template[f"{lgd}/AXISNAME[axis_{dim}]"] = {
                "compress": np.asarray(
                    np.linspace(
                        0,
                        np.shape(img)[enum] - 1,
                        num=np.shape(img)[enum],
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


# considered as deprecated


def get_scan_point_axis_values(inp: dict, dim_name: str):
    is_threed = False
    if "dimensionality" in inp.keys():
        if inp["dimensionality"] == 3:
            is_threed = True
    req_keys = ["grid_type", f"n_{dim_name}", f"s_{dim_name}"]
    for key in req_keys:
        if key not in inp.keys():
            raise ValueError(f"Unable to find required key {key} in inp !")

    if inp["grid_type"] in [HEXAGONAL_FLAT_TOP_TILING, SQUARE_TILING]:
        return np.asarray(
            np.linspace(
                0, inp[f"n_{dim_name}"] - 1, num=inp[f"n_{dim_name}"], endpoint=True
            )
            * inp[f"s_{dim_name}"],
            np.float32,
        )
    else:
        return None


def threed(inp: dict):
    """Identify if 3D triboolean."""
    if "dimensionality" in inp.keys():
        if inp["dimensionality"] == 3:
            return True
        return False
    return None


def square_grid(inp: dict):
    """Identify if square grid with specific assumptions."""
    if (
        inp["grid_type"] == SQUARE_TILING
        and inp["tiling"] == REGULAR_TILING
        and inp["flight_plan"] == FLIGHT_PLAN
    ):
        return True
    return False


def hexagonal_grid(inp: dict):
    """Identify if square grid with specific assumptions."""
    if (
        inp["grid_type"] == HEXAGONAL_FLAT_TOP_TILING
        and inp["tiling"] == REGULAR_TILING
        and inp["flight_plan"] == FLIGHT_PLAN
    ):
        return True
    return False


def get_scan_point_coords(inp: dict) -> dict:
    """Add scan_point_dim array assuming top-left to bottom-right snake style scanning."""
    is_threed = threed(inp)
    req_keys = ["grid_type", "tiling", "flight_plan"]
    dims = ["x", "y"]
    if is_threed is True:
        dims.append("z")
    for dim in dims:
        req_keys.append(f"n_{dim}")
        req_keys.append(f"s_{dim}")

    for key in req_keys:
        if key not in inp.keys():
            raise ValueError(f"Unable to find required key {key} in inp !")

    if is_threed is False:
        if square_grid(inp) is True:
            for dim in dims:
                if "scan_point_{dim}" in inp.keys():
                    print("WARNING::Overwriting scan_point_{dim} !")
            inp["scan_point_x"] = np.tile(
                np.linspace(0, inp["n_x"] - 1, num=inp["n_x"], endpoint=True)
                * inp["s_x"],
                inp["n_y"],
            )
            inp["scan_point_y"] = np.repeat(
                np.linspace(0, inp["n_y"] - 1, num=inp["n_y"], endpoint=True)
                * inp["s_y"],
                inp["n_x"],
            )
        elif hexagonal_grid(inp) is True:
            for dim in dims:
                if "scan_point_{dim}" in inp.keys():
                    print("WARNING::Overwriting scan_point_{dim} !")
            # the following code is only the same as for the sqrgrid because
            # typically the tech partners already take into account and export scan step
            # values such that for a hexagonal grid one s_{dim} (typically s_y) is sqrt(3)/2*s_{other_dim} !
            inp["scan_point_x"] = np.tile(
                np.linspace(0, inp["n_x"] - 1, num=inp["n_x"], endpoint=True)
                * inp["s_x"],
                inp["n_y"],
            )
            inp["scan_point_y"] = np.repeat(
                np.linspace(0, inp["n_y"] - 1, num=inp["n_y"], endpoint=True)
                * inp["s_y"],
                inp["n_x"],
            )
        else:
            print("WARNING::{__name__} facing an unknown scan strategy !")
    else:
        print("WARNING::{__name__} not implemented for 3D case !")
    return inp
