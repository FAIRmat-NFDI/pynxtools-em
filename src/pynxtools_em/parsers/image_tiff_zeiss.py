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
"""Parser for harmonizing Zeiss-specific content in TIFF files."""

import mmap
import re
from tokenize import TokenError

import flatdict as fd
import numpy as np
from PIL import Image, ImageSequence
from pint import UndefinedUnitError

from pynxtools_em.concepts.mapping_functors_pint import add_specific_metadata_pint
from pynxtools_em.configurations.image_tiff_zeiss_cfg import (
    ZEISS_CONCEPT_PREFIXES,
    ZEISS_DYNAMIC_STAGE_NX,
    ZEISS_DYNAMIC_VARIOUS_NX,
    ZEISS_STATIC_VARIOUS_NX,
)
from pynxtools_em.utils.config import DEFAULT_VERBOSITY
from pynxtools_em.utils.custom_logging import logger
from pynxtools_em.utils.get_checksum import get_sha256_of_file_content
from pynxtools_em.utils.pint_custom_unit_registry import ureg
from pynxtools_em.utils.string_conversions import string_to_number


class ZeissTiffParser:
    def __init__(
        self, file_path: str = "", entry_id: int = 1, verbose: bool = DEFAULT_VERBOSITY
    ):
        if file_path:
            self.file_path = file_path
            self.entry_id = entry_id if entry_id > 0 else 1
            self.verbose = verbose
            self.id_mgn: dict[str, int] = {"event_id": 1}
            self.flat_dict_meta = fd.FlatDict({}, "/")
            self.version: dict = {
                "trg": {
                    "tech_partner": ["Zeiss"],
                    "schema_name": ["Zeiss"],
                    "schema_version": [
                        "V06.00.00.00 : 09-Jun-16",
                        "V06.03.00.00 : 15-Dec-17",
                    ],
                }
            }
            self.supported = False
            self.check_if_tiff_zeiss()
            if not self.supported:
                logger.debug(
                    f"Parser {self.__class__.__name__} finds no content in {self.file_path} that it supports"
                )
        else:
            logger.warning(f"Parser {self.__class__.__name__} needs Zeiss TIFF file !")
            self.supported = False

    def get_metadata(self, payload: str):
        """Extract metadata in Zeiss-specific tags if present, return version if success."""
        logger.debug("Parsing Zeiss tags...")
        txt = [line.strip() for line in payload.split("\r") if line.strip() != ""]

        # skip over undocumented data to the first line of Zeiss metadata concepts
        idx = 0
        while not txt[idx].startswith(ZEISS_CONCEPT_PREFIXES):
            idx += 1

        self.flat_dict_meta = fd.FlatDict({}, "/")
        for line in txt[idx : len(txt) - 1]:
            match = re.search(r"^(\w{2})_", line)
            if (
                match
                and line.startswith(ZEISS_CONCEPT_PREFIXES)
                and line not in self.flat_dict_meta
            ):
                token = [value.strip() for value in txt[idx + 1].strip().split("=")]
                if len(token) == 1:
                    if token[0].startswith("Time :"):
                        if token[0].replace("Time :", ""):
                            self.flat_dict_meta[line] = token[0].replace("Time :", "")
                    elif token[0].startswith("Date :"):
                        if token[0].replace("Date :", ""):
                            self.flat_dict_meta[line] = token[0].replace("Date :", "")
                    else:
                        logger.warning(f"Ignoring line {line} token {token} !")
                else:
                    tmp = [value.strip() for value in token[1].split()]
                    if len(tmp) == 1 and tmp[0] in ["On", "Yes"]:
                        self.flat_dict_meta[line] = True
                    elif len(tmp) == 1 and tmp[0] in ["Off", "No"]:
                        self.flat_dict_meta[line] = False
                    elif len(tmp) == 2 and tmp[1] == "°C":
                        self.flat_dict_meta[line] = ureg.Quantity(tmp[0], ureg.degC)
                    elif len(tmp) == 2 and tmp[1] == "X":
                        self.flat_dict_meta[line] = ureg.Quantity(tmp[0])
                    elif len(tmp) == 3 and tmp[1] == "K" and tmp[2] == "X":
                        self.flat_dict_meta[line] = ureg.Quantity(tmp[0]) * 1000.0
                    else:
                        try:
                            self.flat_dict_meta[line] = ureg.Quantity(token[1])
                        except (
                            UndefinedUnitError,
                            TokenError,
                            ValueError,
                            AttributeError,
                            AssertionError,
                        ):
                            if token[1]:
                                self.flat_dict_meta[line] = string_to_number(token[1])
            idx += 1
        if self.verbose:
            for key, value in self.flat_dict_meta.items():
                # if isinstance(value, ureg.Quantity):
                # try:
                #     if not value.dimensionless:
                #         logger.debug(f"{value}, {type(value)}, {key}")
                # except:
                #     logger.debug(f"{value}, {type(value)}, {key}")
                # continue
                # else:
                logger.debug(f"{key}____{type(value)}____{value}")
        if "SV_VERSION" in self.flat_dict_meta:
            return self.flat_dict_meta["SV_VERSION"]

    def check_if_tiff_zeiss(self):
        """Check if resource behind self.file_path is a TaggedImageFormat file."""
        self.supported = False
        try:
            with open(self.file_path, "rb", 0) as file:
                s = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)
                magic = s.read(4)
                if magic != b"II*\x00":  # https://en.wikipedia.org/wiki/TIFF
                    return
        except (OSError, FileNotFoundError):
            logger.warning(f"{self.file_path} either FileNotFound or IOError !")
            return

        with Image.open(self.file_path, mode="r") as fp:
            zeiss_keys = [34118]
            for zeiss_key in zeiss_keys:
                if zeiss_key in fp.tag_v2:
                    this_version = self.get_metadata(fp.tag_v2[zeiss_key])

                    if this_version not in self.version["trg"]["schema_version"]:
                        return
                    self.supported = True

    def parse(self, template: dict) -> dict:
        """Perform actual parsing."""
        if self.supported:
            with open(self.file_path, "rb", 0) as fp:
                self.file_path_sha256 = get_sha256_of_file_content(fp)
            logger.info(
                f"Parsing {self.file_path} Zeiss with SHA256 {self.file_path_sha256} ..."
            )
            # metadata have at this point already been collected into an fd.FlatDict
            self.process_event_data_em_metadata(template)
            self.process_event_data_em_data(template)
        return template

    def process_event_data_em_data(self, template: dict) -> dict:
        """Add respective heavy data."""
        logger.debug(
            f"Writing Zeiss image data to the respective NeXus concept instances..."
        )
        identifier_image = 1
        with Image.open(self.file_path, mode="r") as fp:
            for img in ImageSequence.Iterator(fp):
                nparr = np.flipud(np.array(img))
                logger.debug(
                    f"Processing image {identifier_image} ... {type(nparr)}, {np.shape(nparr)}, {nparr.dtype}"
                )
                # eventually similar open discussions points as were raised for tiff_tfs parser
                trg = (
                    f"/ENTRY[entry{self.entry_id}]/measurement/eventID[event"
                    f"{self.id_mgn['event_id']}]/imageID[image{identifier_image}]/image_2d"
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
                template[f"{trg}/real"] = {"compress": nparr, "strength": 1}
                #  0 is y while 1 is x for 2d, 0 is z, 1 is y, while 2 is x for 3d
                template[f"{trg}/real/@long_name"] = f"Real part of the image intensity"

                sxy = {
                    "i": ureg.Quantity(1.0),
                    "j": ureg.Quantity(1.0),
                }
                found = False
                for key in [
                    "AP_PIXEL_SIZE",
                    "APImagePixelSize",
                ]:  # assuming square pixel
                    if key in self.flat_dict_meta:
                        sxy = {
                            "i": self.flat_dict_meta[key].to(ureg.meter),
                            "j": self.flat_dict_meta[key].to(ureg.meter),
                        }  # these are ureg.Quantity already
                        found = True
                        break
                if not found:
                    logger.warning("Assuming pixel width and height unit is unitless!")
                nxy = {"i": np.shape(nparr)[1], "j": np.shape(nparr)[0]}
                # TODO::be careful we assume here a very specific coordinate system
                # however, these assumptions need to be confirmed by point electronic
                # additional points as discussed already in comments to TFS TIFF reader
                for dim in dims:
                    template[f"{trg}/AXISNAME[axis_{dim}]"] = {
                        "compress": np.asarray(
                            np.linspace(0, nxy[dim] - 1, num=nxy[dim], endpoint=True)
                            * sxy[dim].magnitude,
                            dtype=np.float32,
                        ),
                        "strength": 1,
                    }
                    template[f"{trg}/AXISNAME[axis_{dim}]/@long_name"] = (
                        f"Coordinate along {dim}-axis ({sxy[dim].units if not sxy[dim].dimensionless else 'pixel'})"
                    )
                    if not sxy[dim].dimensionless:
                        template[f"{trg}/AXISNAME[axis_{dim}]/@units"] = (
                            f"{sxy[dim].units}"
                        )
                identifier_image += 1
                del nparr
        return template

    def process_event_data_em_metadata(self, template: dict) -> dict:
        """Add respective metadata."""
        # contextualization to understand how the image relates to the EM session
        logger.debug(
            f"Mapping some of the Zeiss metadata on respective NeXus concepts..."
        )
        identifier = [self.entry_id, self.id_mgn["event_id"], 1]
        for cfg in [
            ZEISS_DYNAMIC_VARIOUS_NX,
            ZEISS_STATIC_VARIOUS_NX,
        ]:
            add_specific_metadata_pint(
                cfg,
                self.flat_dict_meta,
                identifier,
                template,
            )
        add_specific_metadata_pint(
            ZEISS_DYNAMIC_STAGE_NX, self.flat_dict_meta, identifier, template
        )
        return template
