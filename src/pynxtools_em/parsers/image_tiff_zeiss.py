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
"""Subparser for harmonizing Zeiss-specific content in TIFF files."""

import mmap
import re
import tokenize
from typing import Dict

import flatdict as fd
import numpy as np
from PIL import Image, ImageSequence
from PIL.TiffTags import TAGS
from pint import UndefinedUnitError
from pynxtools_em.concepts.mapping_functors_pint import add_specific_metadata_pint
from pynxtools_em.configurations.image_tiff_zeiss_cfg import (
    ZEISS_VARIOUS_DYNAMIC_TO_NX_EM,
    ZEISS_VARIOUS_STATIC_TO_NX_EM,
)
from pynxtools_em.parsers.image_tiff import TiffParser
from pynxtools_em.utils.pint_custom_unit_registry import ureg
from pynxtools_em.utils.string_conversions import string_to_number

ZEISS_CONCEPT_PREFIXES = ("AP_", "DP_", "SV_")


class ZeissTiffParser(TiffParser):
    def __init__(self, file_path: str = "", entry_id: int = 1, verbose: bool = False):
        super().__init__(file_path)
        self.entry_id = entry_id
        self.event_id = 1
        self.verbose = verbose
        self.prfx = None
        self.tmp: Dict = {"data": None, "flat_dict_meta": fd.FlatDict({})}
        self.supported_version: Dict = {}
        self.version: Dict = {}
        self.tags: Dict = {}
        self.supported = False
        self.init_support()
        self.check_if_tiff_zeiss()

    def init_support(self):
        """Init supported versions."""
        self.supported_version["tech_partner"] = ["Zeiss"]
        self.supported_version["schema_name"] = ["Zeiss"]
        self.supported_version["schema_version"] = ["V06.03.00.00 : 15-Dec-17"]

    def get_metadata(self, payload: str):
        """Extract metadata in Zeiss-specific tags if present, return version if success."""
        print("Parsing Zeiss tags...")
        txt = [line.strip() for line in payload.split("\r") if line.strip() != ""]

        # skip over undocumented data to the first line of Zeiss metadata concepts
        idx = 0
        while not txt[idx].startswith(ZEISS_CONCEPT_PREFIXES):
            idx += 1

        self.tmp["flat_dict_meta"] = fd.FlatDict({}, "/")
        for line in txt[idx : len(txt) - 1]:
            match = re.search(r"^(\w{2})_", line)
            if (
                match
                and line.startswith(ZEISS_CONCEPT_PREFIXES)
                and line not in self.tmp["flat_dict_meta"]
            ):
                token = [value.strip() for value in txt[idx + 1].strip().split("=")]
                if len(token) == 1:
                    if token[0].startswith("Time :"):
                        if token[0].replace("Time :", ""):
                            self.tmp["flat_dict_meta"][line] = token[0].replace(
                                "Time :", ""
                            )
                    elif token[0].startswith("Date :"):
                        if token[0].replace("Date :", ""):
                            self.tmp["flat_dict_meta"][line] = token[0].replace(
                                "Date :", ""
                            )
                    else:
                        print(f"WARNING::Ignoring line {line} token {token} !")
                else:
                    tmp = [value.strip() for value in token[1].split()]
                    if len(tmp) == 1 and tmp[0] in ["On", "Yes"]:
                        self.tmp["flat_dict_meta"][line] = True
                    elif len(tmp) == 1 and tmp[0] in ["Off", "No"]:
                        self.tmp["flat_dict_meta"][line] = False
                    elif len(tmp) == 2 and tmp[1] == "°C":
                        self.tmp["flat_dict_meta"][line] = ureg.Quantity(
                            tmp[0], ureg.degC
                        )
                    elif len(tmp) == 2 and tmp[1] == "X":
                        self.tmp["flat_dict_meta"][line] = ureg.Quantity(tmp[0])
                    elif len(tmp) == 3 and tmp[1] == "K" and tmp[2] == "X":
                        self.tmp["flat_dict_meta"][line] = (
                            ureg.Quantity(tmp[0]) * 1000.0
                        )
                    else:
                        try:
                            self.tmp["flat_dict_meta"][line] = ureg.Quantity(token[1])
                        except UndefinedUnitError:
                            if token[1]:
                                self.tmp["flat_dict_meta"][line] = string_to_number(
                                    token[1]
                                )
                        except tokenize.TokenError:
                            if token[1]:
                                self.tmp["flat_dict_meta"][line] = string_to_number(
                                    token[1]
                                )
                        except ValueError:
                            if token[1]:
                                self.tmp["flat_dict_meta"][line] = string_to_number(
                                    token[1]
                                )
                        except AttributeError:
                            if token[1]:
                                self.tmp["flat_dict_meta"][line] = string_to_number(
                                    token[1]
                                )
            idx += 1
        if self.verbose:
            for key, value in self.tmp["flat_dict_meta"].items():
                if isinstance(value, ureg.Quantity):
                    # try:
                    #     if not value.dimensionless:
                    #         print(f"{value}, {type(value)}, {key}")
                    # except:
                    #     print(f"{value}, {type(value)}, {key}")
                    continue
                else:
                    print(f"{value}, {type(value)}, {key}")
        if "SV_VERSION" in self.tmp["flat_dict_meta"]:
            return self.tmp["flat_dict_meta"]["SV_VERSION"]

    def check_if_tiff_zeiss(self):
        """Check if resource behind self.file_path is a TaggedImageFormat file."""
        self.supported = False  # try to falsify
        with open(self.file_path, "rb", 0) as file:
            s = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)
            magic = s.read(4)
            if magic != b"II*\x00":  # https://en.wikipedia.org/wiki/TIFF
                print(
                    f"Parser {self.__class__.__name__} finds no content in {self.file_path} that it supports"
                )
                return

        with Image.open(self.file_path, mode="r") as fp:
            zeiss_keys = [34118]
            for zeiss_key in zeiss_keys:
                if zeiss_key in fp.tag_v2:
                    this_version = self.get_metadata(fp.tag_v2[zeiss_key])

                    if this_version not in self.supported_version["schema_version"]:
                        print(
                            f"Parser {self.__class__.__name__} finds no content in {self.file_path} that it supports"
                        )
                        return

        self.supported = True

    def parse_and_normalize(self):
        """Perform actual parsing filling cache self.tmp."""
        if self.supported is True:
            print(f"Parsing via Zeiss-specific metadata...")
            # metadata have at this point already been collected into an fd.FlatDict
        else:
            print(
                f"{self.file_path} is not a Zeiss-specific "
                f"TIFF file that this parser can process !"
            )

    def process_into_template(self, template: dict) -> dict:
        if self.supported is True:
            self.process_event_data_em_metadata(template)
            self.process_event_data_em_data(template)
        return template

    def process_event_data_em_data(self, template: dict) -> dict:
        """Add respective heavy data."""
        print(f"Writing Zeiss image data to the respective NeXus concept instances...")
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
                if "APImagePixelSize" in self.tmp["flat_dict_meta"]:
                    pixel_size = (
                        self.tmp["flat_dict_meta"]["APImagePixelSize"]
                        .to(ureg.meter)
                        .magnitude
                    )
                    sxy = {"i": pixel_size, "j": pixel_size}
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

    def add_various_dynamic_metadata(self, template: dict) -> dict:
        identifier = [self.entry_id, self.event_id, 1]
        add_specific_metadata_pint(
            ZEISS_VARIOUS_DYNAMIC_TO_NX_EM,
            self.tmp["flat_dict_meta"],
            identifier,
            template,
        )
        return template

    def add_various_static_metadata(self, template: dict) -> dict:
        identifier = [self.entry_id, self.event_id, 1]
        add_specific_metadata_pint(
            ZEISS_VARIOUS_STATIC_TO_NX_EM,
            self.tmp["flat_dict_meta"],
            identifier,
            template,
        )
        return template

    def process_event_data_em_metadata(self, template: dict) -> dict:
        """Add respective metadata."""
        # contextualization to understand how the image relates to the EM session
        print(f"Mapping some of the Zeiss metadata on respective NeXus concepts...")
        self.add_various_dynamic_metadata(template)
        self.add_various_static_metadata(template)
        return template