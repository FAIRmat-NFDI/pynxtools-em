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
# unstructure ad hoc collections of diffraction pattern are generated frequently in
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

import mmap
from typing import Any, Dict
from zipfile import ZipFile

import numpy as np
import yaml
from PIL import Image

from pynxtools_em.examples.diffraction_pattern_set import (
    EXAMPLE_FILE_PREFIX,
    MATERIALS_PROJECT_METADATA,
    PIL_DTYPE_TO_NPY_DTYPE,
    SUPPORTED_FORMATS,
    SUPPORTED_MODES,
    get_materialsproject_id_and_spacegroup,
)
from pynxtools_em.utils.hfive_web import HFIVE_WEB_MAXIMUM_ROI
from pynxtools_em.utils.pint_custom_unit_registry import ureg


class DiffractionPatternSetParser:
    def __init__(self, file_path: str = "", entry_id: int = 1, verbose: bool = True):
        self.file_path = file_path
        self.entry_id = entry_id if entry_id > 0 else 1
        self.verbose = verbose
        self.mp_entries: Dict[int, Any] = {}
        # details about the images of a specific space group and materials project
        self.mp_meta: Dict[int, Any] = {}
        # metadata to each space group and materials id project as cached in projects.yaml
        self.version: Dict = {}
        self.supported = False
        self.check_if_zipped_pattern()
        if not self.supported:
            print(
                f"Parser {self.__class__.__name__} finds no content in {file_path} that it supports"
            )

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
                    # print(f"Test 1 failed, {self.file_path} is not a ZIP archive !")
                    return
        except (FileNotFoundError, IOError):
            print(f"{self.file_path} either FileNotFound or IOError !")
            return

        try:
            with open(MATERIALS_PROJECT_METADATA, "r") as yml:
                self.mp_meta = yaml.safe_load(yml)
        except (FileNotFoundError, IOError):
            print(f"{self.file_path} either FileNotFound or IOError !")
            return

        # inspect zipfile for groups of pattern with the same properties and sub-sets
        with ZipFile(self.file_path) as zip_file_hdl:
            for fpath in zip_file_hdl.namelist():
                if fpath.startswith(EXAMPLE_FILE_PREFIX) and not fpath.endswith("/"):
                    # print(file)
                    # authors studied sets of space_groups with each
                    # sets of materialsproject crystal structures
                    # mp_entries maps this hierarchy
                    mpid, sgid = get_materialsproject_id_and_spacegroup(fpath)
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
            print(
                f"Parsing via DiffractionPatternSetParser ZIP-compressed project parser..."
            )
            with ZipFile(self.file_path) as zip_file_hdl:
                for sgid in self.mp_entries:
                    print(sgid)
                    for mpid in self.mp_entries[sgid]:
                        if (
                            len(self.mp_entries[sgid][mpid]["files"]) <= 0
                            or self.mp_meta[sgid][mpid] == {}
                        ):
                            continue

                        print(f"\t\t{mpid}")
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
        return template

    def process_stack_to_template(
        self, template: dict, meta: dict, stack_2d: np.ndarray
    ) -> dict:
        """Add respective heavy data."""
        trg = f"/ENTRY[entry{self.entry_id}]/simulation"
        template[f"{trg}/programID[program1]/program"] = "EMsoft"
        template[f"{trg}/programID[program1]/program/@version"] = (
            "not reported in the paper"
        )
        trg = f"/ENTRY[entry{self.entry_id}]/simulation/config"
        for concept in [
            "emmet_version",
            "pymatgen_version",
            "database_version",
            # "build_date",
            "license",
        ]:
            if concept in meta:
                template[f"{trg}/{concept}"] = meta[concept]

        if all(
            val in meta
            for val in [
                "identifier/identifier",
                "identifier/service",
                "a_b_c",
                "angles",
                "space_group",
            ]
        ):
            template[f"{trg}/identifier"] = meta["identifier/identifier"]
            template[f"{trg}/identifier/@type"] = meta["identifier/service"]
            template[f"{trg}/a_b_c"] = np.asarray(meta["a_b_c"], np.float32)
            template[f"{trg}/a_b_c/@units"] = f"{ureg.angstrom}"
            template[f"{trg}/alpha_beta_gamma"] = np.asarray(meta["angles"], np.float32)
            template[f"{trg}/alpha_beta_gamma/@units"] = f"{ureg.degree}"
            template[f"{trg}/space_group"] = f"{meta['space_group']}"

        # TODO::requery MaterialsProject to get missing information chemical_formula
        if "atom_types" in meta:
            template[f"/ENTRY[entry{self.entry_id}]/sampleID[sample]/atom_types"] = (
                meta["atom_types"]
            )
        if "chemical_formula" in meta:
            template[
                f"/ENTRY[entry{self.entry_id}]/sampleID[sample]/chemical_formula"
            ] = meta["chemical_formula"]
            # TODO::needs to be Hill

        trg = (
            f"/ENTRY[entry{self.entry_id}]/simulation/results/imageID[image1]/stack_2d"
        )
        if "identifier/identifier" in meta and "phase_name" in meta:
            template[f"{trg}/title"] = (
                f"{meta['identifier/identifier']}, {meta['phase_name']}"
            )
        else:
            template[f"{trg}/title"] = f"MaterialsProject ID was not API-retrievable"
        # trg = f"/ENTRY[entry{self.entry_id}]/simulation/config/phaseID[phase1]"
        # template[f"{trg}/@NX_class"] = "NXphase"  # TODO::should be made part of NXem
        # trg = f"/ENTRY[entry{self.entry_id}]/roiID[roi1]/ebsd/indexing/phaseID[phase1]"
        # template[f"{trg}/@NX_class"] = "NXdata"  # TODO::should be made part of NXem
        template[f"{trg}/@signal"] = "real"
        template[f"{trg}/@AXISNAME_indices[axis_i_indices]"] = np.uint32(2)
        template[f"{trg}/@AXISNAME_indices[axis_j_indices]"] = np.uint32(1)
        template[f"{trg}/@AXISNAME_indices[indices_image_indices]"] = np.uint32(0)
        template[f"{trg}/@axes"] = ["indices_image", "axis_j", "axis_i"]
        template[f"{trg}/real"] = {"compress": stack_2d, "strength": 1}
        template[f"{trg}/real/@long_name"] = f"Real part of the image intensity"
        niyx = {
            "indices_image": np.shape(stack_2d)[0],
            "axis_j": np.shape(stack_2d)[1],
            "axis_i": np.shape(stack_2d)[2],
        }
        # TODO::apply proper scaling because these are dimensions in diffraction space !
        for axis, n in niyx.items():
            template[f"{trg}/AXISNAME[{axis}]"] = {
                "compress": np.asarray(
                    np.linspace(0, n - 1, num=n, endpoint=True), np.uint32
                ),
                "strength": 1,
            }
            template[f"{trg}/AXISNAME[{axis}]/@long_name"] = (
                f"Coordinate along {axis.replace('axis_', '')}-axis (pixel)"
            )
            # TODO::template[f"{trg}/AXISNAME[axis_{dim}]/@units"]
        self.entry_id += 1
        return template
