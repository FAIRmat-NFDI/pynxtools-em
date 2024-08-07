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
"""Subparser for harmonizing JEOL specific content in TIFF files."""

import mmap
from typing import Dict

import flatdict as fd
import numpy as np
from PIL import Image, ImageSequence
from pynxtools_em.concepts.mapping_functors_pint import add_specific_metadata_pint

# from pynxtools_em.configurations.image_tiff_jeol_cfg import JEOL_VARIOUS_DYNAMIC_TO_NX_EM
from pynxtools_em.parsers.image_tiff import TiffParser
from pynxtools_em.utils.string_conversions import string_to_number


class JeolTiffParser(TiffParser):
    def __init__(
        self, tiff_file_path: str = "", txt_file_path: str = "", entry_id: int = 1
    ):
        super().__init__(tiff_file_path)
        self.entry_id = entry_id
        self.event_id = 1
        self.txt_file_path = None
        if txt_file_path is not None and txt_file_path != "":
            self.txt_file_path = txt_file_path
        self.prfx = None
        self.tmp: Dict = {"data": None, "flat_dict_meta": fd.FlatDict({})}
        self.supported_version: Dict = {}
        self.version: Dict = {}
        self.tags: Dict = {}
        self.supported = False
        self.check_if_tiff_jeol()

    def check_if_tiff_jeol(self):
        """Check if resource behind self.file_path is a TaggedImageFormat file.

        This loads the metadata with the txt_file_path first to the formatting of that
        information can be used to tell JEOL data apart from other data.
        """
        # currently not voting-based algorithm required as used in other parsers
        if self.txt_file_path is None:
            self.supported = False
            print(
                f"Parser {self.__class__.__name__} does not work with JEOL metadata text file !"
            )
            return
        with open(self.file_path, "rb", 0) as file:
            s = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)
            magic = s.read(4)
            if magic != b"II*\x00":  # https://en.wikipedia.org/wiki/TIFF
                self.supported = False
                print(
                    f"Parser {self.__class__.__name__} finds no content in {self.file_path} that it supports"
                )
                return

        with open(self.txt_file_path, "r") as txt:
            txt = [
                line.strip().lstrip("$")
                for line in txt.readlines()
                if line.strip() != "" and line.startswith("$")
            ]

            self.tmp["flat_dict_meta"] = fd.FlatDict({}, "/")
            for line in txt:
                tmp = line.split()
                if len(tmp) == 1:
                    print(f"WARNING::{line} is currently ignored !")
                elif len(tmp) == 2:
                    if tmp[0] not in self.tmp["flat_dict_meta"]:
                        self.tmp["flat_dict_meta"][tmp[0]] = string_to_number(tmp[1])
                    else:
                        raise KeyError(f"Found duplicated key {tmp[0]} !")
                else:  # len(tmp) > 2:
                    print(f"WARNING::{line} is currently ignored !")

            # report metadata just for verbose purposes right now
            for key, value in self.tmp["flat_dict_meta"].items():
                print(f"{key}______{type(value)}____{value}")

            if (
                self.tmp["flat_dict_meta"]["SEM_DATA_VERSION"] == "1"
                and self.tmp["flat_dict_meta"]["CM_LABEL"] == "JEOL"
            ):
                self.supported = True
            else:
                self.supported = False
                print(
                    f"Parser {self.__class__.__name__} finds no content in {self.file_path} that it supports"
                )

    def parse_and_normalize(self):
        """Perform actual parsing filling cache self.tmp."""
        if self.supported is True:
            print(f"Parsing via JEOL...")
            # metadata have at this point already been collected into an fd.FlatDict
        else:
            print(
                f"{self.file_path} is not a JEOL-specific TIFF file that this parser can process !"
            )

    def process_into_template(self, template: dict) -> dict:
        if self.supported is True:
            self.process_event_data_em_metadata(template)
            self.process_event_data_em_data(template)
        return template

    def process_event_data_em_data(self, template: dict) -> dict:
        """Add respective heavy data."""
        # default display of the image(s) representing the data collected in this event
        print(
            f"Writing JEOL TIFF image data to the respective NeXus concept instances..."
        )
        # read image in-place
        ####################################################
        image_identifier = 1
        with Image.open(self.file_path, mode="r") as fp:
            for img in ImageSequence.Iterator(fp):
                nparr = np.array(img)
                print(
                    f"Processing image {image_identifier} ... {type(nparr)}, {np.shape(nparr)}, {nparr.dtype}"
                )
                # eventually similar open discussions points as were raised for tiff_tfs parser
                trg = (
                    f"/ENTRY[entry{self.entry_id}]/measurement/event_data_em_set/"
                    f"EVENT_DATA_EM[event_data_em{self.event_id}]/"
                    f"IMAGE_SET[image_set{image_identifier}]/image_twod"
                )
                template[f"{trg}/title"] = f"Image"
                template[f"{trg}/@signal"] = "real"
                dims = ["i", "j"]  # i == x (fastest), j == y (fastest)
                idx = 0
                for dim in dims:
                    template[f"{trg}/@AXISNAME_indices[axis_{dim}_indices]"] = (
                        np.uint32(idx)
                    )
                    idx += 1
                template[f"{trg}/@axes"] = []
                for dim in dims[::-1]:
                    template[f"{trg}/@axes"].append(f"axis_{dim}")
                template[f"{trg}/real"] = {"compress": np.array(fp), "strength": 1}
                #  0 is y while 1 is x for 2d, 0 is z, 1 is y, while 2 is x for 3d
                template[f"{trg}/real/@long_name"] = f"Signal"

                sxy = {"i": 1.0, "j": 1.0}
                scan_unit = {"i": "m", "j": "m"}
                if ("PixelSizeX" in self.tmp["flat_dict_meta"]) and (
                    "PixelSizeY" in self.tmp["flat_dict_meta"]
                ):
                    sxy = {
                        "i": self.tmp["flat_dict_meta"]["PixelSizeX"],
                        "j": self.tmp["flat_dict_meta"]["PixelSizeY"],
                    }
                else:
                    print("WARNING: Assuming pixel width and height unit is meter!")
                nxy = {"i": np.shape(np.array(fp))[1], "j": np.shape(np.array(fp))[0]}
                # TODO::be careful we assume here a very specific coordinate system
                # however, these assumptions need to be confirmed by point electronic
                # additional points as discussed already in comments to TFS TIFF reader
                for dim in dims:
                    template[f"{trg}/AXISNAME[axis_{dim}]"] = {
                        "compress": np.asarray(
                            np.linspace(0, nxy[dim] - 1, num=nxy[dim], endpoint=True)
                            * sxy[dim],
                            np.float64,
                        ),
                        "strength": 1,
                    }
                    template[f"{trg}/AXISNAME[axis_{dim}]/@long_name"] = (
                        f"Coordinate along {dim}-axis ({scan_unit[dim]})"
                    )
                    template[f"{trg}/AXISNAME[axis_{dim}]/@units"] = f"{scan_unit[dim]}"
                image_identifier += 1
        return template

    def add_various_dynamic(self, template: dict) -> dict:
        identifier = [self.entry_id, self.event_id, 1]
        add_specific_metadata_pint(
            DISS_VARIOUS_DYNAMIC_TO_NX_EM,
            self.tmp["flat_dict_meta"],
            identifier,
            template,
        )
        return template

    def process_event_data_em_metadata(self, template: dict) -> dict:
        """Add respective metadata."""
        # contextualization to understand how the image relates to the EM session
        print(
            f"Mapping some of the point electronic DISS metadata on respective NeXus concepts..."
        )
        self.add_various_dynamic(template)
        # ... add more as required ...
        return template
