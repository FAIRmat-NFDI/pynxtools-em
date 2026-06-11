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

import flatdict as fd
import numpy as np
from PIL import Image, ImageSequence
from pynxtools.dataconverter.chunk import prioritized_axes_heuristic

from pynxtools_em.concepts.mapping_functors_pint import (
    add_specific_metadata_pint,
    var_path_to_specific_path,
)
from pynxtools_em.configurations.image_tiff_jeol_cfg import (
    JEOL_DYNAMIC_SCAN_NX,
    JEOL_DYNAMIC_VARIOUS_NX,
    JEOL_EXTRA_VARIOUS_NX,
    JEOL_KEYWORD_TO_PINT_UNITS,
    JEOL_STATIC_VARIOUS_NX,
)
from pynxtools_em.utils.custom_logging import logger
from pynxtools_em.utils.default_config import (
    DEFAULT_COMPRESSION_LEVEL,
    DEFAULT_VERBOSITY,
    SEPARATOR,
)
from pynxtools_em.utils.get_checksum import get_sha256_of_file_content
from pynxtools_em.utils.get_xmp import extract_full_xmp
from pynxtools_em.utils.image_utils import (
    PILLOW_IMAGE_MODE_EXOTIC,
    PILLOW_IMAGE_MODE_NOT_GREYSCALE,
)
from pynxtools_em.utils.pint_custom_unit_registry import ureg
from pynxtools_em.utils.schema_version import EmSchemaVersion
from pynxtools_em.utils.string_conversions import string_to_number

STRING_DECODER_CODECS = ["utf-8", "utf-16", "utf-16-be", "utf-16-le", "latin-1"]


class JeolTiffParser:
    def __init__(
        self,
        file_paths: list[str],
        entry_id: int = 1,
        verbose: bool = DEFAULT_VERBOSITY,
    ):
        self.file_path = None
        self.txt_file_path = None
        self.metadata = fd.FlatDict({}, "/")
        self.entry_id = max(1, entry_id)
        self.verbose = verbose
        self.id_mgn: dict[str, int] = {"event_id": 1}
        self.versions: list[EmSchemaVersion] = []
        self.supported = False

        case_selector: dict[str, list[str]] = {"tif": [], "txt": []}
        for file_path in file_paths:
            if file_path.lower().endswith((".tif", ".tiff")):
                case_selector["tif"].append(file_path)
            elif file_path.lower().endswith(".txt"):
                case_selector["txt"].append(file_path)

        if len(case_selector["tif"]) == 1:
            self.file_path = case_selector["tif"][0]
            if len(case_selector["txt"]) == 1:
                self.txt_file_path = case_selector["txt"][0]
        else:
            logger.warning(
                f"Parser {self.__class__.__name__} needs JEOL TIFF file, sidecar file optional"
            )
            return

        self.check_if_tiff_jeol()

        if not self.supported:
            logger.info(
                f"Parser {self.__class__.__name__} finds no content in {file_paths} that it supports"
            )

    def check_if_tiff_jeol(self):
        """Evaluate if file_path content complies with JEOL in its structure and metadata concepts."""
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

        # metadata in TIFF file take precedence
        root = extract_full_xmp(self.file_path)
        if self.verbose:
            for element in root.iter():
                logger.info(f"{element.tag}, {element.text}")
        create_date = root.find(
            ".//xmp:CreateDate", {"xmp": "http://ns.adobe.com/xap/1.0/"}
        )
        if create_date is not None:
            self.metadata["xmp_create_date"] = create_date.text.strip()

        with Image.open(self.file_path, mode="r") as fp:  # custom TIFF tags
            for key, value in fp.tag_v2.items():
                if self.verbose:
                    logger.info(f"{key}, {value}")
                if key != 37500:
                    if key not in [270, 271, 272]:
                        continue
                    elif key == 270:
                        self.metadata["tif_tag_description"] = value.strip()
                    elif key == 271:
                        self.metadata["tif_tag_vendor"] = value.strip()
                    else:
                        self.metadata["tif_tag_model"] = value.strip()

                # JEOL custom TIFF tag 37500 includes encoded metadata for some cases
                # but for others we observed that the metadata come shipped in a sidecar text file
                payload = fp.tag_v2[37500]
                if not payload.startswith(b"UNICODE"):
                    continue
                decoded: str | None = None
                for codec in STRING_DECODER_CODECS:
                    try:
                        decoded = payload[len(b"UNICODE") :].decode(codec)
                        logger.info(f"JEOL metadata payload decoded with {codec}")
                        break
                    except UnicodeDecodeError:
                        continue
                if decoded is None:
                    logger.warning(
                        f"{self.file_path} JEOL TIFF without sidecar unable to retrieve metadata"
                    )
                for chunk in decoded.split("\t"):
                    if "=" not in chunk:
                        logger.info(f"Ignore line {SEPARATOR}{chunk}{SEPARATOR}")
                        continue
                    keyword, tokens = chunk.strip().replace("\x00", "").split("=")
                    keyword = keyword.replace(
                        keyword,
                        keyword[1:] if keyword.startswith("$") else keyword,
                    )
                    values = [string_to_number(token) for token in tokens.split()]
                    if JEOL_KEYWORD_TO_PINT_UNITS[keyword] == "":
                        quantity = values[0]
                    else:
                        if keyword == "CM_FIELD_OF_VIEW":
                            quantity = ureg.Quantity(
                                [
                                    string_to_number(value.replace("µm", "").strip())
                                    for value in values
                                ],
                                JEOL_KEYWORD_TO_PINT_UNITS[keyword],
                            )
                        elif keyword == "CM_PIXEL_SIZE":
                            quantity = ureg.Quantity(
                                [
                                    string_to_number(value.replace("nm", "").strip())
                                    for value in values
                                ],
                                JEOL_KEYWORD_TO_PINT_UNITS[keyword],
                            )
                        elif keyword == "SM_DWELL_TIME":
                            quantity = ureg.Quantity(values[0])
                        else:
                            if JEOL_KEYWORD_TO_PINT_UNITS[keyword] == "dimensionless":
                                quantity = (
                                    ureg.Quantity(values[0])
                                    if len(values) == 1
                                    else ureg.Quantity(np.asarray(values))
                                )
                            else:
                                quantity = (
                                    ureg.Quantity(
                                        values[0],
                                        JEOL_KEYWORD_TO_PINT_UNITS[keyword],
                                    )
                                    if len(values) == 1
                                    else ureg.Quantity(
                                        np.asarray(values),
                                        JEOL_KEYWORD_TO_PINT_UNITS[keyword],
                                    )
                                )
                    self.metadata[keyword] = quantity

        # hunt for metadata using sidecar file only if nothing found
        # otherwise, what to do if entries in TIFF and sidecar differ ?
        if len(self.metadata) == 0:
            try:
                with open(self.txt_file_path) as txt:
                    txt = [
                        line.strip().lstrip("$")
                        for line in txt.readlines()
                        if line.strip() != "" and line.startswith("$")
                    ]
                    for line in txt:
                        parts = line.split()
                        if len(parts) == 2:
                            if parts[0] not in self.metadata:
                                # replace with pint parsing and catching multiple exceptions
                                # as it is exemplified in the tiff_zeiss parser
                                if parts[0] != "SM_MICRON_MARKER":
                                    self.metadata[parts[0]] = string_to_number(parts[1])
                                else:
                                    self.metadata[parts[0]] = ureg.Quantity(parts[1])
                            else:
                                logger.warning(f"Found duplicated key {parts[0]} !")
                        else:
                            logger.debug(f"{line} is currently ignored !")
                if all(
                    key in self.metadata for key in ["SEM_DATA_VERSION", "CM_LABEL"]
                ):
                    if (self.metadata["SEM_DATA_VERSION"] == 1) and (
                        self.metadata["CM_LABEL"] == "JEOL"
                    ):
                        self.supported = True
            except (OSError, FileNotFoundError):
                logger.warning(f"{self.txt_file_path} either OS or FileNotFound error")
                return

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
                f"Parsing {self.file_path} JEOL with SHA256 {self.file_path_sha256} ..."
            )
            self.process_event_data_em_metadata(template)
            self.process_event_data_em_data(template)
        return template

    def process_event_data_em_data(self, template: dict) -> dict:
        """Add respective heavy data."""
        logger.debug(
            f"Writing JEOL TIFF image data to the respective NeXus concept instances..."
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
                if ("SM_MICRON_BAR" in self.metadata) and (
                    "SM_MICRON_MARKER" in self.metadata
                ):
                    # JEOL-specific conversion for micron bar pixel to physical length
                    resolution = int(self.metadata["SM_MICRON_BAR"])
                    physical_length = self.metadata["SM_MICRON_MARKER"].to(ureg.meter)
                    # resolution many pixel represent physical_length scanned surface
                    # assuming square pixel
                    logger.debug(f"resolution {resolution}, L {physical_length}")
                    sxy = {
                        "i": physical_length / resolution,
                        "j": physical_length / resolution,
                    }
                elif "CM_PIXEL_SIZE" in self.metadata and np.shape(
                    self.metadata["CM_PIXEL_SIZE"].magnitude
                ) == (2,):
                    sxy = {
                        "i": ureg.Quantity(
                            self.metadata["CM_PIXEL_SIZE"].magnitude[1],
                            self.metadata["CM_PIXEL_SIZE"].units,
                        ).to(ureg.meter),
                        "j": ureg.Quantity(
                            self.metadata["CM_PIXEL_SIZE"].magnitude[0],
                            self.metadata["CM_PIXEL_SIZE"].units,
                        ).to(ureg.meter),
                    }  # JEOL seems to report square pixel
                else:
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
        logger.debug(f"Mapping some of JEOL metadata on respective NeXus concepts...")
        identifier = [self.entry_id, self.id_mgn["event_id"], 1]

        if "SM_DETECTOR" in self.metadata:
            detection_mode_map: dict[str, str] = {"SED": "secondary_electron"}
            for jeol_term, nexus_term in detection_mode_map.items():
                if self.metadata["SM_DETECTOR"] == jeol_term:
                    trg = var_path_to_specific_path(
                        f"/ENTRY[entry*]/measurement/eventID[event*]", identifier
                    )
                    template[f"{trg}/type"] = nexus_term
                    break

        for mapping in [
            JEOL_DYNAMIC_VARIOUS_NX,
            JEOL_STATIC_VARIOUS_NX,
            JEOL_DYNAMIC_SCAN_NX,
            JEOL_EXTRA_VARIOUS_NX,
        ]:
            add_specific_metadata_pint(
                mapping,
                self.metadata,
                identifier,
                template,
            )
        return template
