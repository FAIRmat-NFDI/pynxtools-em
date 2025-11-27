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
from typing import Any, Dict, List

import matplotlib.pyplot as plt  # in the hope that this closes figures with orix plot
import numpy as np
from orix import plot
from orix.quaternion import Rotation
from orix.quaternion.symmetry import (
    get_point_group,
    Ci,
    C2h,
    D2h,
    S6,
    D3d,
    C4h,
    D4h,
    C6h,
    D6h,
    Th,
    Oh,
)
from orix.vector import Vector3d
from PIL import Image as pil
from scipy.spatial import KDTree

from pynxtools_em.utils.custom_logging import logger
from pynxtools_em.utils.hfive_web import (
    HFIVE_WEB_MAXIMUM_RGB,
    HFIVE_WEB_MAXIMUM_ROI,
)
from pynxtools_em.utils.hfive_web_utils import hfive_web_decorate_nxdata
from pynxtools_em.utils.image_processing import thumbnail
from pynxtools_em.utils.pint_custom_unit_registry import ureg

IPF_COLORMODEL_USED_BY_ORIX = "tsl"

PROJECTION_VECTORS = [("X", Vector3d.xvector())]

# typical scan schemes used for EBSD
HEXAGONAL_FLAT_TOP_TILING = "hexagonal_flat_top_tiling"
SQUARE_TILING = "square_tiling"
REGULAR_TILING = "regular_tiling"
DEFAULT_LENGTH_UNIT = ureg.micrometer

# most frequently this is the sequence of set scan positions with actual positions
# based on grid type, spacing, and tiling
FLIGHT_PLAN = "start_top_left_stack_x_left_to_right_stack_x_line_along_end_bottom_right"

ORIX_LAUEGROUP_LOOKUP = {
    1: Ci,
    2: C2h,
    3: D2h,
    4: S6,
    5: D3d,
    6: C4h,
    7: D4h,
    8: C6h,
    9: D6h,
    10: Th,
    11: Oh,
}


class EbsdPointCloud:
    """Cache for storing a single indexed EBSD point cloud with mark data."""

    def __init__(self):
        self.dimensionality: int = 0
        self.grid_type = None
        # the next two lines encode the typical assumption that is not reported in tech partner file!
        self.n: Dict[str, Any] = {}  # number of grid points along "x", "y", "z"
        self.s: Dict[str, Any] = {}  # scan step along "x", "y", "z"
        self.phase = []  # collection of phase class instances in order of self.phases
        self.laue_group = []  # collection of laue group in order of self.phases
        self.space_group = []  # collection of space group in order of self.phases
        self.phases = {}  #  named phases
        self.euler = None  # Bunge-Euler ZXZ angle for each scan point np.nan otherwise
        self.phase_id = None  # phase_id for best solution found for each scan point
        self.pos = {}  # "x", "y", "z" pos for each scan point unmodified/not rediscretized
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
    try:
        with open(file_path, "rb", 0) as file:
            s = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)
            magic = s.read(4)
            if magic == b"\x89HDF":
                return True
    except (FileNotFoundError, IOError):
        logger.warning(f"{file_path} either FileNotFound or IOError !")
    return False


def regrid_onto_equisized_scan_points(
    src_grid: EbsdPointCloud, max_edge_discr: int
) -> EbsdPointCloud:
    """Discretize point cloud in R^d (d=1, 2, 3) and mark data to grid with equisized bins."""

    if src_grid.dimensionality not in [1, 2]:
        logger.warning(f"Facing unsupported dimensionality !")
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
    max_extent = min(max_edge_discr, max_extent)

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
    logger.debug(f"{aabb}")

    trg_s = {}
    trg_n = {}
    n_pts = 1
    if src_grid.dimensionality == 1:
        trg_s["x"] = (aabb["x"][1] - aabb["x"][0]) / max_extent  # square step
        trg_n["x"] = max_extent
        n_pts = trg_n["x"]
    elif src_grid.dimensionality == 2:
        if aabb["x"][1] - aabb["x"][0] >= aabb["y"][1] - aabb["y"][0]:
            step = (aabb["x"][1] - aabb["x"][0]) / max_extent  # square step
            trg_s["x"] = step
            trg_s["y"] = step
            trg_n["x"] = max_extent
            trg_n["y"] = int(np.ceil((aabb["y"][1] - aabb["y"][0]) / step))
            n_pts = trg_n["x"] * trg_n["y"]
        else:
            step = (aabb["y"][1] - aabb["y"][0]) / max_extent  # square step
            trg_s["x"] = step
            trg_s["y"] = step
            trg_n["x"] = int(np.ceil((aabb["x"][1] - aabb["x"][0]) / step))
            trg_n["y"] = max_extent
            n_pts = trg_n["x"] * trg_n["y"]
    elif src_grid.dimensionality == 3:
        logger.warning("TODO LEFT FOR IMPLEMENTATION !!!!")

    logger.debug(f"H5Web default plot generation")
    for dim in dims:
        logger.debug(f"src_s {dim}: {src_grid.s[dim]} >>>> trg_s {dim}: {trg_s[dim]}")
        logger.debug(f"src_n {dim}: {src_grid.n[dim]} >>>> trg_n {dim}: {trg_n[dim]}")
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
        trg_pos = np.empty((n_pts,), dtype=np.float32)
        trg_pos[:] = np.asarray(
            np.linspace(0, trg_n["x"] - 1, num=trg_n["x"], endpoint=True) * trg_s["x"],
            dtype=np.float32,
        )
    elif src_grid.dimensionality == 2:
        trg_pos = np.empty((n_pts, 2), dtype=np.float32)
        trg_pos[:, 0] = np.tile(
            np.asarray(
                np.linspace(0, trg_n["x"] - 1, num=trg_n["x"], endpoint=True)
                * trg_s["x"],
                dtype=np.float32,
            ),
            trg_n["y"],
        )
        trg_pos[:, 1] = np.repeat(
            np.asarray(
                np.linspace(0, trg_n["y"] - 1, num=trg_n["y"], endpoint=True)
                * trg_s["y"],
                dtype=np.float32,
            ),
            trg_n["x"],
        )
    # TODO:: if scan_point_{dim} are calibrated this approach
    # here would shift the origin to 0, 0 implicitly which may not be desired
    if src_grid.dimensionality == 1:
        tree = KDTree(np.column_stack((src_grid.pos["x"].magnitude)))
        d, idx = tree.query(trg_pos, k=1)
    elif src_grid.dimensionality == 2:
        tree = KDTree(
            np.column_stack((src_grid.pos["x"].magnitude, src_grid.pos["y"].magnitude))
        )
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
    trg_grid.pos = ureg.Quantity(trg_pos, ureg.micrometer)
    del trg_pos
    if hasattr(src_grid, "euler"):
        trg_grid.euler = np.empty((n_pts, 3), np.float32)
        trg_grid.euler.fill(np.nan)
        trg_grid.euler = ureg.Quantity(
            np.asarray(src_grid.euler.magnitude[idx, :], np.float32), ureg.radian
        )
        if np.isnan(trg_grid.euler).any():
            raise ValueError(f"Gridding left scan points with incorrect euler !")
    if hasattr(src_grid, "phase_id"):
        trg_grid.phase_id = np.empty((n_pts,), np.int32)
        trg_grid.phase_id.fill(np.int32(-2))
        # pyxem_id phase_id are at least as large -1
        trg_grid.phase_id = np.asarray(src_grid.phase_id[idx], np.int32)
        if np.sum(trg_grid.phase_id == -2) > 0:
            raise ValueError(f"Gridding left scan points with incorrect phase_id !")
    if src_grid.descr_type == "band_contrast":
        # bc typically positive
        trg_grid.descr_type = "band_contrast"
        trg_grid.descr_value = np.empty((n_pts,), np.uint32)
        trg_grid.descr_value.fill(np.uint32(0))
        trg_grid.descr_value = ureg.Quantity(
            np.asarray(src_grid.descr_value[idx], np.uint32)
        )
    elif src_grid.descr_type == "confidence_index":
        trg_grid.descr_type = "confidence_index"
        trg_grid.descr_value = np.empty((n_pts,), np.float32)
        trg_grid.descr_value.fill(np.nan)
        trg_grid.descr_value = ureg.Quantity(
            np.asarray(src_grid.descr_value[idx], np.float32)
        )
    elif src_grid.descr_type == "mean_angular_deviation":
        trg_grid.descr_type = "mean_angular_deviation"
        trg_grid.descr_value = np.empty((n_pts,), np.float32)
        trg_grid.descr_value.fill(np.nan)
        trg_grid.descr_value = ureg.Quantity(
            np.asarray(src_grid.descr_value[idx], np.float32), ureg.radian
        )
    else:
        trg_grid.descr_type = None
        trg_grid.descr_value = None
    trg_grid.phase = src_grid.phase
    trg_grid.laue_group = src_grid.laue_group
    trg_grid.space_group = src_grid.space_group
    trg_grid.phases = src_grid.phases
    return trg_grid


def ebsd_roi_overview(inp: EbsdPointCloud, id_mgn: dict, template: dict) -> dict:
    """Create an H5Web-capable ENTRY[entry]/roiID[roi*]/ebsd/indexing/roi."""
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

    trg = f"/ENTRY[entry{id_mgn['entry_id']}]/roiID[roi{id_mgn['roi_id']}]/ebsd/indexing/roi"
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
                * trg_grid.s[dim].magnitude,
                dtype=np.float32,
            ),
            "strength": 1,
        }
        template[f"{trg}/AXISNAME[axis_{dim}]/@units"] = f"{trg_grid.s[dim].units}"
        template[f"{trg}/AXISNAME[axis_{dim}]/@long_name"] = (
            f"Coordinate along {dim}-axis ({trg_grid.s[dim].units})"
        )

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


def ebsd_roi_phase_ipf(inp: EbsdPointCloud, id_mgn: dict, template: dict) -> dict:
    """Create for each phase three inverse pole figures (IPF) maps projected along X, Y using for each map only the respective scan points that were indexed for this phase."""
    if inp.dimensionality not in [1, 2, 3]:
        return template

    nxem_phase_id = 0
    prfx = (
        f"/ENTRY[entry{id_mgn['entry_id']}]/roiID[roi{id_mgn['roi_id']}]/ebsd/indexing"
    )
    # bookkeeping for how many scan points solutions were found is always for src_grid
    # because the eventual discretization for h5web is solely
    # for the purpose of showing users a readily consumable default plot
    # to judge for each possible dataset in the same way if the
    # dataset is worthwhile and potentially valuable for ones on research
    n_pts = 1
    dims = ["x", "y", "z"][0 : inp.dimensionality]
    for dim in dims:
        n_pts *= inp.n[dim]
    if n_pts == 1:
        logger.warning(f"Spot measurements are currently not supported !")
        return template
    if n_pts >= np.iinfo(np.uint32).max:
        logger.warning(
            f"EBSD maps with more than {np.iinfo(np.uint32).max} scan points are currently not supported !"
        )
        return template

    trg_grid: EbsdPointCloud = regrid_onto_equisized_scan_points(
        inp, HFIVE_WEB_MAXIMUM_RGB
    )

    n_pts_indexed = np.sum(inp.phase_id != 0)
    logger.debug(f"n_pts {n_pts}, n_pts_indexed {n_pts_indexed}")
    template[f"{prfx}/number_of_scan_points"] = np.uint32(n_pts)
    template[f"{prfx}/indexing_rate"] = np.float64(n_pts_indexed / n_pts)
    grp_name = f"{prfx}/phaseID[phase{nxem_phase_id}]"
    template[f"{grp_name}/number_of_scan_points"] = np.uint32(np.sum(inp.phase_id == 0))
    template[f"{grp_name}/phase_id"] = np.int32(nxem_phase_id)
    template[f"{grp_name}/name"] = f"notIndexed"

    logger.debug(f"----unique inp phase_id--->{np.unique(inp.phase_id)}")
    for nxem_phase_id in np.arange(1, np.max(np.unique(inp.phase_id)) + 1):
        # starting here at ID 1 because the specific parsers have already normalized the
        # tech-partner specific phase_id conventions to follow the NXem NeXus convention
        # that is 0 is notIndexed, all other phase contiguously, start count from 1
        logger.debug(f"inp[phases].keys(): {inp.phases.keys()}")
        if nxem_phase_id not in inp.phases:
            raise KeyError(f"{nxem_phase_id} is not a key in inp['phases'] !")
        trg = f"{prfx}/phaseID[phase{nxem_phase_id}]"
        template[f"{trg}/number_of_scan_points"] = np.uint32(
            np.sum(inp.phase_id == nxem_phase_id)
        )
        template[f"{trg}/phase_id"] = np.int32(nxem_phase_id)
        template[f"{trg}/name"] = f"{inp.phases[nxem_phase_id]['phase_name']}"

        if "a_b_c" in inp.phases[nxem_phase_id]:
            for idx, key in enumerate(["a", "b", "c"]):
                template[f"{trg}/UNIT_CELL[unit_cell]/{key}"] = np.float32(
                    inp.phases[nxem_phase_id]["a_b_c"].magnitude[idx]
                )
                template[f"{trg}/UNIT_CELL[unit_cell]/{key}/@units"] = (
                    f"{inp.phases[nxem_phase_id]['a_b_c'].units}"
                )
        if "alpha_beta_gamma" in inp.phases[nxem_phase_id]:
            for idx, key in enumerate(["alpha", "beta", "gamma"]):
                template[f"{trg}/UNIT_CELL[unit_cell]/{key}"] = np.float32(
                    inp.phases[nxem_phase_id]["alpha_beta_gamma"].magnitude[idx]
                )
                template[f"{trg}/UNIT_CELL[unit_cell]/{key}/@units"] = (
                    f"{inp.phases[nxem_phase_id]['alpha_beta_gamma'].units}"
                )
        if "space_group" in inp.phases[nxem_phase_id]:
            template[f"{trg}/UNIT_CELL[unit_cell]/space_group"] = (
                f"{inp.phases[nxem_phase_id]['space_group']}"
            )

            # internally the following function may discretize a coarser IPF
            # if the input grid inp is too large for h5web to display
            # this remove fine details in the EBSD maps but keep in mind
            # that the purpose of the default plot is to guide the user
            # of the potential usefulness of the dataset when searching in
            # a RDMS like NOMAD OASIS, the purpose is NOT to take the coarse-grained
            # discretization and use this for scientific data analysis!
            process_roi_phase_ipf(
                trg_grid,
                id_mgn,
                nxem_phase_id,
                trg_grid.phases[nxem_phase_id]["phase_name"],
                trg_grid.phases[nxem_phase_id]["laue_group"]
                if "laue_group" in trg_grid.phases[nxem_phase_id]
                else 0,
                trg_grid.phases[nxem_phase_id]["space_group"],
                template,
            )
    return template


def process_roi_phase_ipf(
    trg_grid: EbsdPointCloud,
    id_mgn: dict,
    nxem_phase_id: int,
    phase_name: str,
    laue_group: int,
    space_group: int,
    template: dict,
) -> dict:
    dims = ["x", "y", "z"]
    n_pts: int = 1
    n_shape: List[int] = []
    for dim in dims[0 : trg_grid.dimensionality]:
        n_pts *= trg_grid.n[dim]
    for dim in dims[0 : trg_grid.dimensionality][::-1]:
        n_shape.append(trg_grid.n[dim])
    n_shape.append(3)

    rotations = Rotation.from_euler(
        euler=trg_grid.euler[trg_grid.phase_id == nxem_phase_id].magnitude,
        direction="lab2crystal",
        degrees=False,
    )
    # logger.debug(f"shape rotations -----> {np.shape(rotations)}")

    for idx in np.arange(0, len(PROJECTION_VECTORS)):
        # https://orix.readthedocs.io/en/stable/tutorials/inverse_pole_figures.html
        if space_group != 0:
            laue_grp = get_point_group(space_group, proper=False).laue
        else:
            if laue_group in ORIX_LAUEGROUP_LOOKUP:
                laue_grp = ORIX_LAUEGROUP_LOOKUP[laue_group]
            else:
                logger.warning("Neither space group nor valid laue group reported!")
                return template
        ipf_key = plot.IPFColorKeyTSL(laue_grp, direction=PROJECTION_VECTORS[idx][1])
        img = get_ipfdir_legend(ipf_key)

        rgb_px_with_phase_id = np.asarray(
            np.asarray(ipf_key.orientation2color(rotations) * 255.0, np.uint32),
            np.uint8,
        )
        # logger.debug(f"shape rgb_px_with_phase_id -----> {np.shape(rgb_px_with_phase_id)}")

        ipf_rgb_map = np.zeros((n_pts, 3), np.uint8)
        # background is black instead of white (which would be more pleasing)
        # but IPF color maps have a whitepoint which encodes in fact an orientation
        # and because of that we may have a map from a single crystal characterization
        # whose orientation could be close to the whitepoint which becomes a fully white
        # seemingly "empty" image, therefore we use black as empty, i.e. white reports an
        # orientation
        ipf_rgb_map[trg_grid.phase_id == nxem_phase_id, :] = rgb_px_with_phase_id
        ipf_rgb_map = np.reshape(ipf_rgb_map, n_shape, order="C")
        # 3D, 0 > z, 1 > y, 2 > x
        # 2D, 0 > y, 1 > x
        # 1D, 0 > x
        trg = (
            f"/ENTRY[entry{id_mgn['entry_id']}]/roiID[roi{id_mgn['roi_id']}]/ebsd/indexing"
            f"/phaseID[phase{nxem_phase_id}]/ipfID[ipf{idx + 1}]"
        )
        template[f"{trg}/color_model"] = "tsl"  # as used by kikuchipy/orix
        template[f"{trg}/projection_direction"] = np.asarray(
            PROJECTION_VECTORS[idx][1].data.flatten(), np.float32
        )

        # add the IPF color map fundamental unit SO3 obeying crystal symmetry
        mpp = f"{trg}/map"
        template[f"{mpp}/title"] = (
            f"IPF, {PROJECTION_VECTORS[idx][0]}, {IPF_COLORMODEL_USED_BY_ORIX}, phase{nxem_phase_id}, {phase_name}"  # TODO add symmetry to follow the pattern for MTex: IPF, X, -1, tsl, phase1, BYTOWNITE An
        )
        template[f"{mpp}/@signal"] = "data"
        template[f"{mpp}/@axes"] = []
        for dim in dims[0 : trg_grid.dimensionality][::-1]:
            template[f"{mpp}/@axes"].append(f"axis_{dim}")
        for dim_idx, dim in enumerate(dims[0 : trg_grid.dimensionality]):
            template[f"{mpp}/@AXISNAME_indices[axis_{dim}_indices]"] = np.uint32(
                dim_idx
            )
        template[f"{mpp}/data"] = {"compress": ipf_rgb_map, "strength": 1}
        hfive_web_decorate_nxdata(f"{mpp}/data", template)

        # mind that EBSD map could be scale-invariant e.g. from synthetic microstructure
        # simulation that could work on multiple length-scales as atoms are not resolved
        # directly!
        for dim in dims[0 : trg_grid.dimensionality]:
            template[f"{mpp}/AXISNAME[axis_{dim}]"] = {
                "compress": np.asarray(
                    np.linspace(
                        0, trg_grid.n[dim] - 1, num=trg_grid.n[dim], endpoint=True
                    )
                    * trg_grid.s[dim].magnitude,
                    dtype=np.float32,
                ),
                "strength": 1,
            }
            template[f"{mpp}/AXISNAME[axis_{dim}]/@units"] = f"{trg_grid.s[dim].units}"
            template[f"{mpp}/AXISNAME[axis_{dim}]/@long_name"] = (
                f"Coordinate along {dim}-axis ({trg_grid.s[dim].units})"
            )
        # add the IPF color map legend/key
        lgd = f"{trg}/legend"
        template[f"{lgd}/title"] = (
            f"IPF, {PROJECTION_VECTORS[idx][0]}, {IPF_COLORMODEL_USED_BY_ORIX}, phase{nxem_phase_id}, {phase_name}"  # TODO add symmetry to follow the pattern for MTex: IPF, X, -1, tsl, phase1, BYTOWNITE An
        )
        # template[f"{trg}/title"] = f"Inverse pole figure color key with SST"
        template[f"{lgd}/@signal"] = "data"
        template[f"{lgd}/@axes"] = []
        dims = ["x", "y"]  # no longer the EBSD map just an RGB image of the legend!
        for dim in dims[::-1]:
            template[f"{lgd}/@axes"].append(f"axis_{dim}")
        for dim_idx, dim in enumerate(dims):
            template[f"{lgd}/@AXISNAME_indices[axis_{dim}_indices]"] = np.uint32(
                dim_idx
            )
        template[f"{lgd}/data"] = {"compress": img, "strength": 1}
        hfive_web_decorate_nxdata(f"{lgd}/data", template)

        dims_idxs = {"x": 1, "y": 0}
        for dim, dim_idx in dims_idxs.items():
            template[f"{lgd}/AXISNAME[axis_{dim}]"] = {
                "compress": np.asarray(
                    np.linspace(
                        0,
                        np.shape(img)[dim_idx] - 1,
                        num=np.shape(img)[dim_idx],
                        endpoint=True,
                    ),
                    dtype=np.uint32,
                ),
                "strength": 1,
            }
            template[f"{lgd}/AXISNAME[axis_{dim}]/@long_name"] = (
                f"Pixel along {dim}-axis"
            )
    return template
