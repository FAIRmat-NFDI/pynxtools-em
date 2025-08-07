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
"""Parser for harmonizing JEOL specific content in TIFF files."""

import mmap
from typing import Dict, List

import flatdict as fd
import numpy as np
from PIL import Image, ImageSequence

from pynxtools_em.concepts.mapping_functors_pint import add_specific_metadata_pint
from pynxtools_em.configurations.image_tiff_jeol_cfg import (
    JEOL_DYNAMIC_VARIOUS_NX,
    JEOL_STATIC_VARIOUS_NX,
)
from pynxtools_em.utils.config import DEFAULT_VERBOSITY
from pynxtools_em.utils.custom_logging import logger
from pynxtools_em.utils.get_checksum import (
    DEFAULT_CHECKSUM_ALGORITHM,
    get_sha256_of_file_content,
)
from pynxtools_em.utils.pint_custom_unit_registry import ureg
from pynxtools_em.utils.string_conversions import string_to_number


class JeolTiffParser:
    def __init__(
        self,
        file_paths: List[str],
        entry_id: int = 1,
        verbose: bool = DEFAULT_VERBOSITY,
    ):
        tif_txt = ["", ""]
        if (
            len(file_paths) == 2
            and file_paths[0][0 : file_paths[0].rfind(".")]
            == file_paths[1][0 : file_paths[0].rfind(".")]
        ):
            for entry in file_paths:
                if entry.lower().endswith((".tif", ".tiff")):
                    tif_txt[0] = entry
                elif entry.lower().endswith((".txt")):
                    tif_txt[1] = entry
            if all(value != "" for value in tif_txt):
                self.file_path = tif_txt[0]
                self.entry_id = entry_id if entry_id > 0 else 1
                self.verbose = verbose
                self.id_mgn: Dict[str, int] = {"event_id": 1}
                self.txt_file_path = tif_txt[1]
                self.flat_dict_meta = fd.FlatDict({}, "/")
                self.version: Dict = {}
                self.supported = False
                self.check_if_tiff_jeol()
            else:
                logger.warning(
                    f"Parser {self.__class__.__name__} needs TIF and TXT file !"
                )
                self.supported = False
        else:
            logger.debug(
                f"Parser {self.__class__.__name__} finds no content in {tif_txt} that it supports"
            )
            self.supported = False

    def check_if_tiff_jeol(self):
        """Check if resource behind self.file_path is a TaggedImageFormat file.

        This loads the metadata with the txt_file_path first to the formatting of that
        information can be used to tell JEOL data apart from other data.
        """
        self.supported = False
        try:
            with open(self.file_path, "rb", 0) as file:
                s = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)
                magic = s.read(4)
                if magic != b"II*\x00":  # https://en.wikipedia.org/wiki/TIFF
                    return
        except (FileNotFoundError, IOError):
            logger.warning(f"{self.file_path} either FileNotFound or IOError !")
            return

        with open(self.txt_file_path, "r") as txt:
            txt = [
                line.strip().lstrip("$")
                for line in txt.readlines()
                if line.strip() != "" and line.startswith("$")
            ]

            self.flat_dict_meta = fd.FlatDict({}, "/")
            for line in txt:
                tmp = line.split()
                if len(tmp) == 2:
                    if tmp[0] not in self.flat_dict_meta:
                        # replace with pint parsing and catching multiple exceptions
                        # as it is exemplified in the tiff_zeiss parser
                        if tmp[0] != "SM_MICRON_MARKER":
                            self.flat_dict_meta[tmp[0]] = string_to_number(tmp[1])
                        else:
                            self.flat_dict_meta[tmp[0]] = ureg.Quantity(tmp[1])
                    else:
                        logger.warning(f"Found duplicated key {tmp[0]} !")
                else:
                    logger.debug(f"{line} is currently ignored !")

            if self.verbose:
                for key, value in self.flat_dict_meta.items():
                    logger.info(f"{key}______{type(value)}____{value}")

            if all(
                key in self.flat_dict_meta for key in ["SEM_DATA_VERSION", "CM_LABEL"]
            ):
                if (self.flat_dict_meta["SEM_DATA_VERSION"] == 1) and (
                    self.flat_dict_meta["CM_LABEL"] == "JEOL"
                ):
                    self.supported = True

    def parse(self, template: dict) -> dict:
        """Perform actual parsing filling cache."""
        if self.supported:
            # metadata have at this point already been collected into an fd.FlatDict
            with open(self.file_path, "rb", 0) as fp:
                self.file_path_sha256 = get_sha256_of_file_content(fp)
            logger.info(
                f"Parsing {self.file_path} JEOL with SHA256 {self.file_path_sha256} ..."
            )
            self.process_event_data_em_metadata(template)
            self.process_event_data_em_data(template)
        return template

    def process_event_data_em_data(self, template: dict) -> dict:
        """Add respective heavy data."""
        # default display of the image(s) representing the data collected in this event
        logger.debug(
            f"Writing JEOL TIFF image data to the respective NeXus concept instances..."
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
                template[f"{trg}/real"] = {
                    "compress": nparr,
                    "strength": 1,
                }
                #  0 is y while 1 is x for 2d, 0 is z, 1 is y, while 2 is x for 3d
                template[f"{trg}/real/@long_name"] = f"Real part of the image intensity"

                sxy = {
                    "i": ureg.Quantity(1.0),
                    "j": ureg.Quantity(1.0),
                }
                if ("SM_MICRON_BAR" in self.flat_dict_meta) and (
                    "SM_MICRON_MARKER" in self.flat_dict_meta
                ):
                    # JEOL-specific conversion for micron bar pixel to physical length
                    resolution = int(self.flat_dict_meta["SM_MICRON_BAR"])
                    physical_length = self.flat_dict_meta["SM_MICRON_MARKER"].to(
                        ureg.meter
                    )
                    # resolution many pixel represent physical_length scanned surface
                    # assuming square pixel
                    logger.debug(f"resolution {resolution}, L {physical_length}")
                    sxy = {
                        "i": physical_length / resolution,
                        "j": physical_length / resolution,
                    }
                else:
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

    def add_various_dynamic(self, template: dict) -> dict:
        """Add several event-based concepts with similar template path prefixes dynamic."""
        identifier = [self.entry_id, self.id_mgn["event_id"], 1]
        add_specific_metadata_pint(
            JEOL_DYNAMIC_VARIOUS_NX,
            self.flat_dict_meta,
            identifier,
            template,
        )
        return template

    def add_various_static(self, template: dict) -> dict:
        """Add several event-based concepts with similar template path prefixes static."""
        identifier = [self.entry_id, self.id_mgn["event_id"], 1]
        add_specific_metadata_pint(
            JEOL_STATIC_VARIOUS_NX,
            self.flat_dict_meta,
            identifier,
            template,
        )
        return template

    def process_event_data_em_metadata(self, template: dict) -> dict:
        """Add respective metadata."""
        # contextualization to understand how the image relates to the EM session
        logger.debug(f"Mapping some of JEOL metadata on respective NeXus concepts...")
        self.add_various_dynamic(template)
        self.add_various_static(template)
        # ... add more as required ...
        return template
