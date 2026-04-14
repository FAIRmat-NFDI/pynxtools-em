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
"""Parser for exemplar reading of ZIP-compressed collections of diffraction pattern."""

# this parser exemplifies how NXem can be used to report annotated collections of
# diffraction pattern that potentially are forming different sets of analyses
# the example is intentionally implement for a specific use case mainly to show first
# that there is value in organizing collections of pattern more condensed and with
# richer contextualization
# unstructured ad hoc collections of diffraction pattern are generated frequently in
# exploratory use cases where e.g. improved pattern indexing or analysis workflows are
# investigated, given their ad hoc nature different formats are in use such as tif, bmp,
# jpg, or png, including metadata or not, often with metadata encoded in the filename
# the here chosen example parser implements a solution for an exemplar collection
# of 360 sets of 100 Kikuchi diffraction pattern each taking the data from
# https://doi.org/10.1093/mam/ozae044.178 and https://zenodo.org/records/13368338
# specifically these authors simulated dynamic electron diffraction for 100 different
# orientations of each for a total of 360 single crystals. The single crystals form a
# set of 6 sub-sets for six exemplar high symmetry space groups
# to instantiate the simulations crystal structures were sampled from MaterialsProject
# and simulations with EMsoft performed. The authors published sections of the simulated
# Kikuchi diffraction pattern. Metadata were encoded in the filename, specifically
# the space group and materials project id, this parser shows how the resulting ZIP
# with a total of 36000 diffraction pattern can be converted into an NXem NeXus HDF5
# file with MaterialsProject metadata added for each single crystal simulation
# In effect, this is an example how pattern can be stored using NXem
# unfortunately configurations and other results from the EMsoft simulations were not
# shared and thus not possible to add to what NXem as a data model is capable of holding
# this parser is meant how combine the key commands with which such ad hoc studies
# can be organized using NeXus to contextualize using research data management software
# https://doi.org/10.1093/mam/ozae044.178

import mmap
import os
import re
from typing import Any
from zipfile import ZipFile

import numpy as np
import yaml
from PIL import Image
from pynxtools.dataconverter.chunk import prioritized_axes_heuristic

from pynxtools_em.utils.custom_logging import logger
from pynxtools_em.utils.default_config import (
    DEFAULT_COMPRESSION_LEVEL,
    DEFAULT_VERBOSITY,
    SEPARATOR,
)
from pynxtools_em.utils.hfive_web import HFIVE_WEB_MAXIMUM_ROI
from pynxtools_em.utils.pint_custom_unit_registry import ureg

THIS_MODULE_PATH = os.path.abspath(__file__).replace(
    "/usa_evanston_yan_ebsd_patterns.py", ""
)
EXAMPLE_FILE_PREFIX = "original_data/original_data_0/train/"
MATERIALS_PROJECT_METADATA = f"{THIS_MODULE_PATH}/usa_evanston_yan_ebsd_patterns.yaml"
SUPPORTED_FORMATS = ["bmp", "gif", "jpg", "png", "tif", "tiff"]
SUPPORTED_MODES = ["L", "I"]


def get_materialsproject_id_and_space_group(
    fpath: str, verbose: bool = False
) -> tuple[str, int] | tuple[None, None]:
    if 1 <= int(fpath[fpath.rfind("/") - 3 : fpath.rfind("/")]) <= 230:
        fname = fpath[fpath.rfind("/") + 1 :]
        materialsproject_id = re.compile(r"^mp-(?:\d+)_").search(fname)
        mp = materialsproject_id.group()[0:-1]
        space_group_id = re.compile(r"^(?:\d{1}|\d{2}|\d{3})_").search(
            fname.replace(materialsproject_id.group(), "")
        )
        spc = space_group_id.group()[0:-1]
        tail = fname.replace(
            f"{materialsproject_id.group()}{space_group_id.group()}", ""
        )
        if verbose:
            logger.debug(
                f"{fpath}\n{fname}\n{mp}{SEPARATOR}{type(mp)}\n{spc}{SEPARATOR}{type(spc)}\n{tail}{SEPARATOR}{type(tail)}"
            )
        return mp, int(spc)
    return None, None


# https://pillow.readthedocs.io/en/stable/handbook/concepts.html#concept-modes
PIL_DTYPE_TO_NPY_DTYPE = {
    "L": np.uint8,
    "I": np.int32,
}


class DiffractionPatternSetParser:
    def __init__(
        self, file_path: str = "", entry_id: int = 1, verbose: bool = DEFAULT_VERBOSITY
    ):
        if file_path:
            self.file_path = file_path
            self.entry_id = entry_id if entry_id > 0 else 1
            self.verbose = verbose
            self.mp_entries: dict[int, Any] = {}
            # details about the images of a specific space group and materials project
            self.mp_meta: dict[int, Any] = {}
            # metadata to each space group and materials id project as cached in projects.yaml
            self.version: dict = {}
            self.supported = False
            self.check_if_zipped_pattern()
            if not self.supported:
                logger.debug(
                    f"Parser {self.__class__.__name__} finds no content in {file_path} that it supports"
                )
        else:
            logger.warning(f"Parser {self.__class__.__name__} needs zipped content !")
            self.supported = False

    def check_if_zipped_pattern(self):
        """Check if resource behind self.file_path is a ZIP file with diffraction pattern."""
        self.supported = False
        try:
            with open(self.file_path, "rb", 0) as file:
                s = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)
                magic = s.read(4)
                if (
                    magic != b"PK\x03\x04"
                ):  # https://en.wikipedia.org/wiki/List_of_file_signatures
                    # logger.warning(f"Test 1 failed, {self.file_path} is not a ZIP archive !")
                    return
        except (OSError, FileNotFoundError):
            logger.warning(f"{self.file_path} either FileNotFound or IOError !")
            return

        try:
            with open(MATERIALS_PROJECT_METADATA) as yml:
                self.mp_meta = yaml.safe_load(yml)
        except (OSError, FileNotFoundError):
            logger.warning(f"{self.file_path} either FileNotFound or IOError !")
            return

        # inspect zipfile for groups of pattern with the same properties and sub-sets
        with ZipFile(self.file_path) as zip_file_hdl:
            for fpath in zip_file_hdl.namelist():
                if fpath.startswith(EXAMPLE_FILE_PREFIX) and not fpath.endswith("/"):
                    # logger.debug(file)
                    # authors studied sets of space_groups with each
                    # sets of materialsproject crystal structures
                    # mp_entries maps this hierarchy
                    mpid, sgid = get_materialsproject_id_and_space_group(fpath)
                    if mpid is not None and sgid is not None:
                        if sgid not in self.mp_entries:
                            self.mp_entries[sgid] = {}
                        if mpid in self.mp_entries[sgid]:
                            with zip_file_hdl.open(fpath) as file_hdl:
                                mime = fpath[fpath.rfind(".") + 1 :].lower()
                                img = Image.open(file_hdl, "r")
                                if (
                                    len(self.mp_entries[sgid][mpid]["files"]) > 0
                                    and self.mp_entries[sgid][mpid]["mode"] == img.mode
                                    and self.mp_entries[sgid][mpid]["shape"]
                                    == (img.height, img.width)
                                    and self.mp_entries[sgid][mpid]["mime"] == mime
                                ):
                                    self.mp_entries[sgid][mpid]["files"].append(fpath)
                        else:
                            # per crystal structures simulation parameter and reporting
                            # formats could have been different therefore first
                            # pattern defines dimensions, formatting and type
                            # that all subsequent images need to have
                            self.mp_entries[sgid][mpid] = {
                                "files": [],
                                "mode": None,
                                "shape": None,
                                "mime": None,
                            }
                            with zip_file_hdl.open(fpath) as file_hdl:
                                mime = fpath[fpath.rfind(".") + 1 :].lower()
                                img = Image.open(file_hdl, "r")
                                # https://pillow.readthedocs.io/en/stable/handbook/concepts.html#concept-modes
                                if (
                                    mime in SUPPORTED_FORMATS
                                    and img.mode in SUPPORTED_MODES
                                    and 1 <= img.height <= HFIVE_WEB_MAXIMUM_ROI
                                    and 1 <= img.width <= HFIVE_WEB_MAXIMUM_ROI
                                ):
                                    self.mp_entries[sgid][mpid] = {
                                        "files": [fpath],
                                        "mode": img.mode,
                                        "shape": (img.height, img.width),
                                        "mime": mime,
                                    }
        self.supported = True

    def parse(self, template: dict) -> dict:
        """Perform actual parsing filling cache."""
        if self.supported:
            logger.info(
                f"Parsing via DiffractionPatternSetParser ZIP-compressed project parser..."
            )
            with ZipFile(self.file_path) as zip_file_hdl:
                for sgid in self.mp_entries:
                    logger.debug(sgid)
                    for mpid in self.mp_entries[sgid]:
                        if (
                            len(self.mp_entries[sgid][mpid]["files"]) <= 0
                            or self.mp_meta[sgid][mpid] == {}
                        ):
                            continue

                        logger.debug(f"\t\t{mpid}")
                        dtyp = PIL_DTYPE_TO_NPY_DTYPE[
                            self.mp_entries[sgid][mpid]["mode"]
                        ]
                        stack_2d = np.zeros(
                            (
                                len(self.mp_entries[sgid][mpid]["files"]),
                                self.mp_entries[sgid][mpid]["shape"][0],
                                self.mp_entries[sgid][mpid]["shape"][1],
                            ),
                            dtype=dtyp,
                        )
                        for idx, file in enumerate(
                            self.mp_entries[sgid][mpid]["files"]
                        ):
                            with zip_file_hdl.open(file) as fp:
                                stack_2d[idx, :, :] = np.asarray(
                                    Image.open(fp, "r"), dtype=dtyp
                                )
                        self.process_stack_to_template(
                            template, self.mp_meta[sgid][mpid], stack_2d
                        )
                        del stack_2d

                        # if self.entry_id > 2:  # stop early for debugging purposes
                        #     break
        return template

    def process_stack_to_template(
        self, template: dict, meta: dict, stack_2d: np.ndarray
    ) -> dict:
        """Add respective heavy data."""
        trg = f"/ENTRY[entry{self.entry_id}]/simulation"
        template[f"{trg}/PROGRAM[program1]/program"] = "EMsoft"
        template[f"{trg}/PROGRAM[program1]/program/@version"] = (
            "not reported in the paper"
        )
        trg = f"/ENTRY[entry{self.entry_id}]/simulation/PROCESS[config]"
        for concept in [
            "emmet_version",
            "pymatgen_version",
            "database_version",
            # "build_date",
            # "license",
        ]:
            if concept in meta:
                template[f"{trg}/{concept}"] = meta[concept]

        if "identifier/identifier" in meta and "identifier/service" in meta:
            template[f"{trg}/identifier"] = meta["identifier/identifier"]
            template[f"{trg}/identifier/@type"] = meta["identifier/service"]

        if all(
            concept in meta
            for concept in ["phase_name", "space_group", "a_b_c", "angles"]
        ):
            trg = f"/ENTRY[entry{self.entry_id}]/simulation/PHASE[phase1]"
            template[f"{trg}/phase_name"] = meta["phase_name"]

            trg = f"/ENTRY[entry{self.entry_id}]/simulation/PHASE[phase1]/UNIT_CELL[unit_cell]"
            template[f"{trg}/space_group"] = f"{meta['space_group']}"
            for idx, suffix in enumerate("a_b_c".split("_")):
                template[f"{trg}/{suffix}"] = np.float32(meta["a_b_c"][idx])
                template[f"{trg}/{suffix}/@units"] = f"{ureg.angstrom}"
            for idx, suffix in enumerate("alpha_beta_gamma".split("_")):
                template[f"{trg}/{suffix}"] = np.float32(meta["angles"][idx])
                template[f"{trg}/{suffix}/@units"] = f"{ureg.degree}"

        if "elements" in meta:
            template[f"/ENTRY[entry{self.entry_id}]/sampleID[sample]/atom_types"] = (
                meta["elements"]
            )

        trg = f"/ENTRY[entry{self.entry_id}]/simulation/IMAGE[image1]/stack_2d"
        if "identifier/identifier" in meta and "phase_name" in meta:
            template[f"{trg}/title"] = (
                f"{meta['identifier/identifier']}, {meta['phase_name']}"
            )
        else:
            template[f"{trg}/title"] = f"MaterialsProject ID was not API-retrievable"
        template[f"{trg}/@signal"] = "real"
        template[f"{trg}/@AXISNAME_indices[axis_i_indices]"] = np.uint32(2)
        template[f"{trg}/@AXISNAME_indices[axis_j_indices]"] = np.uint32(1)
        template[f"{trg}/@AXISNAME_indices[indices_image_indices]"] = np.uint32(0)
        template[f"{trg}/@axes"] = ["indices_image", "axis_j", "axis_i"]
        template[f"{trg}/real"] = {
            "compress": stack_2d,
            "chunks": prioritized_axes_heuristic(stack_2d, (0, 1, 2)),
            "strength": DEFAULT_COMPRESSION_LEVEL,
        }
        template[f"{trg}/real/@long_name"] = f"Real part of the image intensity"
        n_i_y_x = {
            "indices_image": np.shape(stack_2d)[0],
            "axis_j": np.shape(stack_2d)[1],
            "axis_i": np.shape(stack_2d)[2],
        }
        # TODO::apply proper scaling because these are dimensions in diffraction space !
        for axis, n in n_i_y_x.items():
            numpy_array = np.asarray(
                np.linspace(0, n - 1, num=n, endpoint=True), np.uint32
            )
            template[f"{trg}/AXISNAME[{axis}]"] = {
                "compress": numpy_array,
                "chunks": prioritized_axes_heuristic(numpy_array, (0,)),
                "strength": DEFAULT_COMPRESSION_LEVEL,
            }
            if axis != "indices_image":
                template[f"{trg}/AXISNAME[{axis}]/@long_name"] = (
                    f"Coordinate along {axis.replace('axis_', '')}-axis (pixel)"
                )
            else:
                template[f"{trg}/AXISNAME[{axis}]/@long_name"] = (
                    f"Each image a random orientation"
                )
        self.entry_id += 1
        return template
