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
from typing import Dict, List

import flatdict as fd
import numpy as np
from PIL import Image, ImageSequence

from pynxtools_em.concepts.mapping_functors_pint import add_specific_metadata_pint
from pynxtools_em.configurations.image_tiff_tescan_cfg import (
    TESCAN_DYNAMIC_STAGE_NX,
    TESCAN_DYNAMIC_STIGMATOR_NX,
    TESCAN_DYNAMIC_VARIOUS_NX,
    TESCAN_STATIC_VARIOUS_NX,
)
from pynxtools_em.utils.get_checksum import (
    DEFAULT_CHECKSUM_ALGORITHM,
    get_sha256_of_file_content,
)
from pynxtools_em.utils.pint_custom_unit_registry import ureg
from pynxtools_em.utils.string_conversions import string_to_number


class TescanTiffParser:
    def __init__(self, file_paths: List[str], entry_id: int = 1, verbose: bool = False):
        # file and sidecar file may not come in a specific order need to find which is which if any supported
        tif_hdr = ["", ""]
        if len(file_paths) == 1 and file_paths[0].lower().endswith((".tif", ".tiff")):
            tif_hdr[0] = file_paths[0]
        elif (
            len(file_paths) == 2
            and file_paths[0][0 : file_paths[0].rfind(".")]
            == file_paths[1][0 : file_paths[0].rfind(".")]
        ):
            for entry in file_paths:
                if entry.lower().endswith((".tif", ".tiff")) and entry != "":
                    tif_hdr[0] = entry
                elif entry.lower().endswith((".hdr")) and entry != "":
                    tif_hdr[1] = entry

        self.file_path = tif_hdr[0]
        self.entry_id = entry_id if entry_id > 0 else 1
        self.verbose = verbose
        self.id_mgn: Dict[str, int] = {"event_id": 1}
        self.flat_dict_meta = fd.FlatDict({}, "/")
        self.version: Dict = {}
        self.supported = False
        self.hdr_file_path = tif_hdr[1]
        self.check_if_tiff_tescan()
        if not self.supported:
            print(
                f"Parser {self.__class__.__name__} finds no content in {self.file_path} that it supports"
            )

    def check_if_tiff_tescan(self):
        self.supported = False
        if not hasattr(self, "file_path"):
            return
        try:
            with open(self.file_path, "rb", 0) as file:
                s = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)
                magic = s.read(4)
                if magic != b"II*\x00":  # https://en.wikipedia.org/wiki/TIFF
                    return
        except (FileNotFoundError, IOError):
            print(f"{self.file_path} either FileNotFound or IOError !")
            return

        self.flat_dict_meta = fd.FlatDict({}, "/")
        with Image.open(self.file_path, mode="r") as fp:
            tescan_keys = [50431]
            for tescan_key in tescan_keys:
                if tescan_key in fp.tag_v2:
                    payload = fp.tag_v2[tescan_key]
                    pos = payload.find(bytes("Description", "utf8"))
                    try:
                        txt = payload[pos:].decode("utf8")
                    except UnicodeDecodeError:
                        print(
                            f"WARNING::{self.file_path} TESCAN TIFF tag {tescan_key} cannot be decoded using UTF8, trying to use sidecar file instead if available !"
                        )
                        if hasattr(self, "hdr_file_path"):
                            continue
                        else:
                            return
                    del payload

                    for line in txt.split():
                        tmp = [value.strip() for value in line.split("=")]
                        if len(tmp) == 1:
                            print(f"Ignore line {line} !")
                        elif len(tmp) == 2:
                            if tmp[0] and tmp[0] not in self.flat_dict_meta:
                                self.flat_dict_meta[tmp[0]] = string_to_number(tmp[1])
                        else:
                            print(f"Ignore line {line} !")
        # very frequently using sidecar files create ambiguities: are the metadata in the
        # image and the sidecar file exactly the same, a subset, which information to
        # give preference in case of inconsistencies, system time when the sidecar file
        # is written differs from system time when the image was written, which time
        # to take for the event data?
        if len(self.flat_dict_meta) == 0:
            if self.hdr_file_path != "":
                with open(self.hdr_file_path, mode="r", encoding="utf8") as fp:
                    txt = fp.read()
                    txt = txt.replace("\r\n", "\n")  # windows to unix EOL conversion
                    txt = [
                        line.strip()
                        for line in txt.split("\n")
                        if line.strip() != "" and line.startswith("#") is False
                    ]
                    if not all(value in txt for value in ["[MAIN]", "[SEM]"]):
                        print(
                            f"WARNING::TESCAN HDR sidecar file exists but does not contain expected section headers !"
                        )
                    txt = [line for line in txt if line not in ["[MAIN]", "[SEM]"]]
                    for line in txt:
                        tmp = [value.strip() for value in line.split("=")]
                        if len(tmp) == 1:
                            print(f"Ignore line {line} !")
                        elif len(tmp) == 2:
                            if tmp[0] and (tmp[0] not in self.flat_dict_meta):
                                self.flat_dict_meta[tmp[0]] = string_to_number(tmp[1])
                        else:
                            print(f"Ignore line {line} !")
            else:
                print(f"WARNING::Potential TESCAN TIF without metadata !")

        if self.verbose:
            for key, value in self.flat_dict_meta.items():
                print(f"{key}____{type(value)}____{value}")

        # check if written about with supported DISS version
        supported_versions = ["TIMA", "MIRA3 LMH"]
        if "Device" in self.flat_dict_meta:
            if self.flat_dict_meta["Device"] in supported_versions:
                self.supported = True
                # but this is quite a weak test, more instance data are required
                # with TESCAN-specific concept names to make this here more robust

    def parse(self, template: dict) -> dict:
        """Perform actual parsing filling cache."""
        if self.supported:
            # metadata have at this point already been collected into an fd.FlatDict
            with open(self.file_path, "rb", 0) as fp:
                self.file_path_sha256 = get_sha256_of_file_content(fp)
            print(
                f"Parsing {self.file_path} TESCAN with SHA256 {self.file_path_sha256} ..."
            )
            self.process_event_data_em_metadata(template)
            self.process_event_data_em_data(template)
        return template

    def process_event_data_em_data(self, template: dict) -> dict:
        """Add respective heavy data."""
        print(f"Writing TESCAN image data to the respective NeXus concept instances...")
        identifier_image = 1
        with Image.open(self.file_path, mode="r") as fp:
            for img in ImageSequence.Iterator(fp):
                nparr = np.array(img)
                print(
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
                template[f"{trg}/real"] = {"compress": np.array(fp), "strength": 1}
                #  0 is y while 1 is x for 2d, 0 is z, 1 is y, while 2 is x for 3d
                template[f"{trg}/real/@long_name"] = f"Real part of the image intensity"

                sxy = {
                    "i": ureg.Quantity(1.0),
                    "j": ureg.Quantity(1.0),
                }
                if all(
                    value in self.flat_dict_meta
                    for value in ["PixelSizeX", "PixelSizeY"]
                ):
                    sxy = {
                        "i": ureg.Quantity(
                            self.flat_dict_meta["PixelSizeX"], ureg.meter
                        ),
                        "j": ureg.Quantity(
                            self.flat_dict_meta["PixelSizeY"], ureg.meter
                        ),
                    }
                else:
                    print("WARNING: Assuming pixel width and height unit is unitless!")
                nxy = {"i": np.shape(np.array(fp))[1], "j": np.shape(np.array(fp))[0]}
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
        return template

    def process_event_data_em_metadata(self, template: dict) -> dict:
        """Add respective metadata."""
        # contextualization to understand how the image relates to the EM session
        print(f"Mapping some of the TESCAN metadata on respective NeXus concepts...")
        identifier = [self.entry_id, self.id_mgn["event_id"], 1]
        for cfg in [
            TESCAN_DYNAMIC_STIGMATOR_NX,
            TESCAN_STATIC_VARIOUS_NX,
            TESCAN_DYNAMIC_VARIOUS_NX,
            TESCAN_DYNAMIC_STAGE_NX,
        ]:
            add_specific_metadata_pint(cfg, self.flat_dict_meta, identifier, template)
        return template
