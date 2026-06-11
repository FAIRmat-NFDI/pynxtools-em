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
"""Parser for harmonizing TESCAN-specific content in TIFF files."""

import mmap
from pathlib import Path

import flatdict as fd
import numpy as np
from PIL import Image, ImageSequence
from pynxtools.dataconverter.chunk import prioritized_axes_heuristic

from pynxtools_em.concepts.mapping_functors_pint import add_specific_metadata_pint
from pynxtools_em.configurations.image_tiff_tescan_cfg import (
    TESCAN_DYNAMIC_STAGE_NX,
    TESCAN_DYNAMIC_STIGMATOR_NX,
    TESCAN_DYNAMIC_VARIOUS_NX,
    TESCAN_STATIC_VARIOUS_NX,
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


class TescanTiffParser:
    def __init__(
        self,
        file_paths: list[str] = [],
        entry_id: int = 1,
        verbose: bool = DEFAULT_VERBOSITY,
    ):
        tif_file = None
        hdr_file = None

        if len(file_paths) == 1:
            if file_paths[0].lower().endswith((".tif", ".tiff")):
                tif_file = file_paths[0]

        elif len(file_paths) == 2:
            p0, p1 = map(Path, file_paths)

            if p0.stem == p1.stem:
                tif_file = next(
                    (f for f in file_paths if f.lower().endswith((".tif", ".tiff"))),
                    None,
                )
                hdr_file = next(
                    (f for f in file_paths if f.lower().endswith(".hdr")),
                    None,
                )

        self.file_path = tif_file
        self.hdr_file_path = hdr_file or ""
        self.entry_id = max(1, entry_id)
        self.verbose = verbose
        self.id_mgn: dict[str, int] = {"event_id": 1}
        self.metadata = fd.FlatDict({}, "/")
        self.versions: list[EmSchemaVersion] = []
        self.supported = False

        if not self.file_path:
            logger.warning(
                f"Parser {self.__class__.__name__} needs TESCAN TIFF file, sidecar file optional"
            )
            return

        self.check_if_tiff_tescan()

        if not self.supported:
            logger.debug(
                f"Parser {self.__class__.__name__} finds no content in {self.file_path} that it supports"
            )

    def check_if_tiff_tescan(self):
        """Evaluate if file_path content complies with TESCAN in its structure and metadata concepts."""
        # note, so far mostly seen TIMA and "MIRA3 LMH" "Device" instances
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

        self.metadata = fd.FlatDict({}, "/")
        with Image.open(self.file_path, mode="r") as fp:
            tescan_keys = [50431]
            for tescan_key in tescan_keys:
                if tescan_key in fp.tag_v2:
                    payload = fp.tag_v2[tescan_key]
                    pos = payload.find(bytes("Description", "utf8"))
                    try:
                        txt = payload[pos:].decode("utf8")
                    except UnicodeDecodeError:
                        logger.warning(
                            f"{self.file_path} TESCAN TIFF tag {tescan_key} cannot be decoded using UTF8, trying to use sidecar file instead if that is available"
                        )
                        if self.hdr_file_path == "":
                            return
                    del payload

                    for line in txt.split():
                        parts: list[str] = [value.strip() for value in line.split("=")]
                        if len(parts) == 1:
                            logger.debug(f"Ignore line {line}")
                        elif len(parts) == 2:
                            if parts[0] and parts[0] not in self.metadata:
                                self.metadata[parts[0]] = string_to_number(parts[1])
                        else:
                            logger.debug(f"Ignore line {line}")

        # using sidecar files can create ambiguities: are the metadata in the
        # image and the sidecar file exactly the same, a subset, which information to
        # give preference in case of inconsistencies, system time when the sidecar file
        # is written differs from system time when the image was written, which time
        # to take for the event data?
        if len(self.metadata) == 0 and self.hdr_file_path != "":
            with open(self.hdr_file_path, encoding="utf8") as fp:
                txt = fp.read()
                txt = txt.replace("\r\n", "\n")  # windows to unix EOL conversion
                txt = [
                    line.strip()
                    for line in txt.split("\n")
                    if line.strip() != "" and line.startswith("#") is False
                ]
                if not all(value in txt for value in ["[MAIN]", "[SEM]"]):
                    logger.warning(
                        f"TESCAN HDR sidecar file exists but does not contain expected section headers"
                    )
                    return
                txt = [line for line in txt if line not in ["[MAIN]", "[SEM]"]]
                for line in txt:
                    parts = [value.strip() for value in line.split("=")]
                    if len(parts) == 1:
                        logger.debug(f"Ignore line {line} !")
                    elif len(parts) == 2:
                        if parts[0] and (parts[0] not in self.metadata):
                            self.metadata[parts[0]] = string_to_number(parts[1])
                    else:
                        logger.debug(f"Ignore line {line} !")

        if len(self.metadata) > 0:
            self.supported = True

        if self.verbose:
            for key, value in self.metadata.items():
                logger.info(f"{key}{SEPARATOR}{type(value)}{SEPARATOR}{value}")

    def parse(self, template: dict) -> dict:
        """Perform actual parsing."""
        if self.supported:
            # metadata have at this point already been collected into an fd.FlatDict
            with open(self.file_path, "rb", 0) as fp:
                self.file_path_sha256 = get_sha256_of_file_content(fp)
            logger.info(
                f"Parsing {self.file_path} TESCAN with SHA256 {self.file_path_sha256} ..."
            )
            self.process_event_data_em_metadata(template)
            self.process_event_data_em_data(template)
        return template

    def process_event_data_em_data(self, template: dict) -> dict:
        """Add respective heavy data."""
        logger.debug(
            f"Writing TESCAN image data to the respective NeXus concept instances..."
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
                if all(
                    value in self.metadata for value in ["PixelSizeX", "PixelSizeY"]
                ):
                    sxy = {
                        "i": ureg.Quantity(self.metadata["PixelSizeX"], ureg.meter),
                        "j": ureg.Quantity(self.metadata["PixelSizeY"], ureg.meter),
                    }
                else:
                    logger.warning("Assuming pixel width and height unit is unitless!")
                nxy = {"i": np.shape(numpy_array)[1], "j": np.shape(numpy_array)[0]}
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
                del numpy_array
        return template

    def process_event_data_em_metadata(self, template: dict) -> dict:
        """Add respective metadata."""
        # contextualization to understand how the image relates to the EM session
        logger.debug(
            f"Mapping some of the TESCAN metadata on respective NeXus concepts..."
        )
        identifier = [self.entry_id, self.id_mgn["event_id"], 1]
        for cfg in [
            TESCAN_DYNAMIC_STIGMATOR_NX,
            TESCAN_STATIC_VARIOUS_NX,
            TESCAN_DYNAMIC_VARIOUS_NX,
            TESCAN_DYNAMIC_STAGE_NX,
        ]:
            add_specific_metadata_pint(cfg, self.metadata, identifier, template)
        return template
