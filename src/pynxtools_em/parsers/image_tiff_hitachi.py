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
"""Parser for harmonizing Hitachi-specific content in TIFF files."""

import mmap
from tokenize import TokenError
from typing import Dict, List

import flatdict as fd
import numpy as np
from PIL import Image, ImageSequence
from pint import UndefinedUnitError
from pynxtools_em.concepts.mapping_functors_pint import add_specific_metadata_pint
from pynxtools_em.configurations.image_tiff_hitachi_cfg import (
    HITACHI_DYNAMIC_VARIOUS_NX,
    HITACHI_STATIC_VARIOUS_NX,
)
from pynxtools_em.parsers.image_tiff import TiffParser
from pynxtools_em.utils.pint_custom_unit_registry import ureg
from pynxtools_em.utils.string_conversions import string_to_number


class HitachiTiffParser(TiffParser):
    def __init__(self, file_paths: List[str], entry_id: int = 1, verbose=False):
        # TODO::instantiate super.__init__
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
            super().__init__(tif_txt[0])
            self.entry_id = entry_id
            self.event_id = 1
            self.verbose = verbose
            self.txt_file_path = tif_txt[1]
            self.flat_dict_meta = fd.FlatDict({}, "/")
            self.version: Dict = {}
            self.supported = False
            self.check_if_tiff_hitachi()
        else:
            print(f"Parser {self.__class__.__name__} needs TIF and TXT file !")
            self.supported = False

    def check_if_tiff_hitachi(self):
        """Check if resource behind self.file_path is a TaggedImageFormat file."""
        self.supported = False
        if not hasattr(self, "file_path"):
            print(
                f"... is not a Hitachi-specific TIFF file that this parser can process !"
            )
            return
        if self.txt_file_path is None:
            print(
                f"Parser {self.__class__.__name__} does not work without a Hitachi text file with the image metadata !"
                f"This file is required to have exactly the same file name as the file with the TIF image data !"
            )
            return
        with open(self.file_path, "rb", 0) as file:
            s = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)
            magic = s.read(4)
            if magic != b"II*\x00":  # https://en.wikipedia.org/wiki/TIFF
                print(
                    f"Parser {self.__class__.__name__} finds no content in {self.file_path} that it supports"
                )
                return
        with open(self.txt_file_path, "r", encoding="utf8") as fp:
            txt = fp.read()
            txt = txt.replace("\r\n", "\n")  # windows to unix EOL conversion
            txt = [
                line.strip()
                for line in txt.split("\n")
                if line.strip() != "" and line.startswith("#") is False
            ]
            # jump to typical header line
            idx = 0
            while not txt[idx].startswith(
                ("[SemImageFile]", "[TemImageFile]")
            ) and idx < (len(txt) - 1):
                idx += 1
            if idx < len(txt):
                if not txt[idx].startswith(("[SemImageFile]", "[TemImageFile]")):
                    return
            else:
                print(f"Parser {self.__class__.__name__} metadata section is empty !")
                return

            self.flat_dict_meta = fd.FlatDict({}, "/")
            for line in txt[idx + 1 :]:  # + 1 to jump over the header line
                tmp = [token.strip() for token in line.split("=")]
                if len(tmp) == 2 and all(token != "" for token in tmp):
                    try:
                        self.flat_dict_meta[tmp[0]] = ureg.Quantity(tmp[1])
                    except (UndefinedUnitError, TokenError):
                        self.flat_dict_meta[tmp[0]] = string_to_number(tmp[1])

            if self.verbose:
                for key, value in self.flat_dict_meta.items():
                    print(f"{key}______{type(value)}____{value}")
            self.supported = True

    def parse(self, template: dict) -> dict:
        """Perform actual parsing filling cache."""
        if self.supported:
            print(f"Parsing via Hitachi...")
            # metadata have at this point already been collected into an fd.FlatDict
            self.process_event_data_em_metadata(template)
            self.process_event_data_em_data(template)
        return template

    def process_event_data_em_data(self, template: dict) -> dict:
        """Add respective heavy data."""
        # default display of the image(s) representing the data collected in this event
        print(
            f"Writing Hitachi TIFF image data to the respective NeXus concept instances..."
        )
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
                    f"IMAGE_SET[image_set{image_identifier}]/image_2d"
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

                sxy = {
                    "i": ureg.Quantity(1.0, ureg.meter),
                    "j": ureg.Quantity(1.0, ureg.meter),
                }
                if "PixelSize" in self.flat_dict_meta:
                    sxy = {
                        "i": ureg.Quantity(
                            self.flat_dict_meta["PixelSize"], ureg.nanometer
                        ),
                        "j": ureg.Quantity(
                            self.flat_dict_meta["PixelSize"], ureg.nanometer
                        ),
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
                            * sxy[dim].magnitude,
                            np.float64,
                        ),
                        "strength": 1,
                    }
                    template[f"{trg}/AXISNAME[axis_{dim}]/@long_name"] = (
                        f"Coordinate along {dim}-axis ({sxy[dim].units})"
                    )
                    template[f"{trg}/AXISNAME[axis_{dim}]/@units"] = f"{sxy[dim].units}"
                image_identifier += 1
        return template

    def process_event_data_em_metadata(self, template: dict) -> dict:
        """Add respective metadata."""
        print(f"Mapping some of the Hitachi metadata on respective NeXus concepts...")
        # we assume for now dynamic quantities can just be repeated
        identifier = [self.entry_id, self.event_id, 1]
        for cfg in [HITACHI_DYNAMIC_VARIOUS_NX, HITACHI_STATIC_VARIOUS_NX]:
            add_specific_metadata_pint(cfg, self.flat_dict_meta, identifier, template)
        return template
