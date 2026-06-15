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
from pynxtools.dataconverter.chunk import prioritized_axes_heuristic

from pynxtools_em.concepts.mapping_functors_pint import add_specific_metadata_pint
from pynxtools_em.configurations.image_tiff_zeiss_cfg import (
    ZEISS_CONCEPT_PREFIXES,
    ZEISS_DYNAMIC_STAGE_NX,
    ZEISS_DYNAMIC_VARIOUS_NX,
    ZEISS_STATIC_VARIOUS_NX,
)
from pynxtools_em.utils.custom_logging import logger
from pynxtools_em.utils.default_config import (
    DEFAULT_COMPRESSION_LEVEL,
    DEFAULT_VERBOSITY,
    SEPARATOR,
)
from pynxtools_em.utils.get_checksum import get_sha256_of_file_content
from pynxtools_em.utils.image_utils import (
    PILLOW_IMAGE_MODE_EXOTIC,
    PILLOW_IMAGE_MODE_NOT_GREYSCALE,
)
from pynxtools_em.utils.pint_custom_unit_registry import ureg
from pynxtools_em.utils.schema_version import EmSchemaVersion
from pynxtools_em.utils.string_conversions import string_to_number


class ZeissTiffParser:
    def __init__(
        self,
        file_path: str | None = None,
        entry_id: int = 1,
        verbose: bool = DEFAULT_VERBOSITY,
    ):
        self.file_path = file_path or ""
        self.entry_id = max(1, entry_id)
        self.verbose = verbose
        self.id_mgn: dict[str, int] = {"event_id": 1}
        self.metadata = fd.FlatDict({}, "/")
        self.versions: list[EmSchemaVersion] = [
            EmSchemaVersion("Zeiss", "Zeiss", "V06.00.00.00 : 09-Jun-16"),
            EmSchemaVersion("Zeiss", "Zeiss", "V06.03.00.00 : 15-Dec-17"),
            EmSchemaVersion("Zeiss", "Zeiss", "V08.00.00.00 : 29-Feb-24"),
        ]
        self.supported = False

        if not file_path:
            logger.warning(f"Parser {self.__class__.__name__} needs Zeiss TIFF file")
            return

        self.check_if_tiff_zeiss()

        if not self.supported:
            logger.info(
                f"Parser {self.__class__.__name__} finds no content in {self.file_path} that it supports"
            )

    def check_if_tiff_zeiss(self):
        """Evaluate if file_path content complies with ZEISS in its structure and metadata concepts."""
        self.supported = False
        try:
            with open(self.file_path, "rb", 0) as file:
                s = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)
                magic = s.read(4)
                if magic != b"II*\x00":  # https://en.wikipedia.org/wiki/TIFF
                    return
        except (OSError, FileNotFoundError):
            logger.warning(f"{self.file_path} either OS or FileNotFound error")
            return

        with Image.open(self.file_path, mode="r") as fp:
            for zeiss_key in [34118]:
                if zeiss_key in fp.tag_v2:
                    self.get_metadata(fp.tag_v2[zeiss_key])

        if len(self.metadata) > 0:
            self.supported = True

        if self.verbose:
            for key, value in self.metadata.items():
                logger.info(f"{key}{SEPARATOR}{type(value)}{SEPARATOR}{value}")

    def get_metadata(self, payload: str):
        """Extract metadata behind Zeiss-specific tags if present."""
        logger.debug("Parsing Zeiss tags...")
        txt = [line.strip() for line in payload.split("\r") if line.strip() != ""]

        # skip over undocumented data to the first line with Zeiss metadata concepts
        idx = 0
        while not txt[idx].startswith(ZEISS_CONCEPT_PREFIXES):
            idx += 1

        self.metadata = fd.FlatDict({}, "/")
        for line in txt[idx : len(txt) - 1]:
            match = re.search(r"^(\w{2})_", line)
            if (
                match
                and line.startswith(ZEISS_CONCEPT_PREFIXES)
                and line not in self.metadata
            ):
                token = [value.strip() for value in txt[idx + 1].strip().split("=")]
                if len(token) == 1:
                    if token[0].startswith("Time :"):
                        if token[0].replace("Time :", ""):
                            self.metadata[line] = token[0].replace("Time :", "")
                    elif token[0].startswith("Date :"):
                        if token[0].replace("Date :", ""):
                            self.metadata[line] = token[0].replace("Date :", "")
                    else:
                        logger.warning(f"Ignoring line {line} token {token} !")
                else:
                    parts = [value.strip() for value in token[1].split()]
                    if len(parts) == 1 and parts[0] in ["On", "Yes"]:
                        self.metadata[line] = True
                    elif len(parts) == 1 and parts[0] in ["Off", "No"]:
                        self.metadata[line] = False
                    elif len(parts) == 2 and parts[1] == "°C":
                        self.metadata[line] = ureg.Quantity(parts[0], ureg.degC)
                    elif len(parts) == 2 and parts[1] == "X":
                        self.metadata[line] = ureg.Quantity(parts[0])
                    elif len(parts) == 3 and parts[1] == "K" and parts[2] == "X":
                        self.metadata[line] = ureg.Quantity(parts[0]) * 1000.0
                    else:
                        try:
                            self.metadata[line] = ureg.Quantity(token[1])
                        except (
                            UndefinedUnitError,
                            TokenError,
                            ValueError,
                            AttributeError,
                            AssertionError,
                        ):
                            if token[1]:
                                self.metadata[line] = string_to_number(token[1])
            idx += 1

    def parse(self, template: dict) -> dict:
        """Perform actual parsing."""
        if self.supported:
            with open(self.file_path, "rb", 0) as fp:
                self.file_path_sha256 = get_sha256_of_file_content(fp)
            logger.info(
                f"Parsing {self.file_path} Zeiss TIFF with SHA256 {self.file_path_sha256} ..."
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
                if img.mode not in PILLOW_IMAGE_MODE_EXOTIC:
                    if img.mode in PILLOW_IMAGE_MODE_NOT_GREYSCALE:
                        numpy_array = np.flipud(np.array(img.convert("L")))
                    else:
                        numpy_array = np.flipud(np.array(img))
                else:
                    logger.warning(f"{img.mode} is an unsupported img.mode")
                    continue
                logger.debug(
                    f"Processing image {identifier_image} ... {type(numpy_array)}, {np.shape(numpy_array)}, {numpy_array.dtype}"
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
                    "compress": numpy_array,
                    "strength": DEFAULT_COMPRESSION_LEVEL,
                    "chunks": prioritized_axes_heuristic(
                        numpy_array, np.arange(numpy_array.ndim)
                    ),
                }
                #  0 is y while 1 is x for 2d, 0 is z, 1 is y, while 2 is x for 3d
                template[f"{trg}/real/@long_name"] = f"Real part of the image intensity"

                sxy = {
                    "i": ureg.Quantity(1.0),
                    "j": ureg.Quantity(1.0),
                }
                found = False
                for key in [
                    "AP_IMAGE_PIXEL_SIZE",  # this is the one to use in V08
                    "APImagePixelSize",
                    # version-dependent case distinction required here!
                    "AP_PIXEL_SIZE",  # this worked in V06 but is off by a factor two in V08
                ]:  # assuming square pixel
                    if key in self.metadata:
                        sxy = {
                            "i": self.metadata[key].to(ureg.meter),
                            "j": self.metadata[key].to(ureg.meter),
                        }  # these are ureg.Quantity already
                        found = True
                        break
                if not found:
                    logger.warning("Assuming pixel width and height unit is unitless!")
                nxy = {"i": np.shape(numpy_array)[1], "j": np.shape(numpy_array)[0]}
                # TODO::be careful we assume here a very specific coordinate system
                # however, these assumptions need to be confirmed by point electronic
                # additional points as discussed already in comments to TFS TIFF reader
                for dim in dims:
                    numpy_array = np.asarray(
                        np.linspace(0, nxy[dim] - 1, num=nxy[dim], endpoint=True)
                        * sxy[dim].magnitude,
                        dtype=np.float32,
                    )
                    template[f"{trg}/AXISNAME[axis_{dim}]"] = {
                        "compress": numpy_array,
                        "strength": DEFAULT_COMPRESSION_LEVEL,
                        "chunks": prioritized_axes_heuristic(
                            numpy_array, np.arange(numpy_array.ndim)
                        ),
                    }
                    template[f"{trg}/AXISNAME[axis_{dim}]/@long_name"] = (
                        f"Coordinate along {dim}-axis ({sxy[dim].units if not sxy[dim].dimensionless else 'pixel'})"
                    )
                    if not sxy[dim].dimensionless:
                        template[f"{trg}/AXISNAME[axis_{dim}]/@units"] = (
                            f"{sxy[dim].units}"
                        )
                identifier_image += 1
                del numpy_array
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
                self.metadata,
                identifier,
                template,
            )
        add_specific_metadata_pint(
            ZEISS_DYNAMIC_STAGE_NX, self.metadata, identifier, template
        )
        return template
