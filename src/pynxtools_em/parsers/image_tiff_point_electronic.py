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
"""Subparser for harmonizing point electronic DISS specific content in TIFF files."""

import mmap
from typing import Dict

import flatdict as fd
import numpy as np
from PIL import Image, ImageSequence

# from pynxtools_em.concepts.mapping_functors import add_specific_metadata
# from pynxtools_em.configurations.image_tiff_tfs_cfg import
from pynxtools_em.parsers.image_tiff import TiffParser


class PointElectronicTiffParser(TiffParser):
    def __init__(self, file_path: str = "", entry_id: int = 1):
        super().__init__(file_path)
        self.entry_id = entry_id
        self.event_id = 1
        self.prfx = None
        self.tmp: Dict = {"data": None, "flat_dict_meta": fd.FlatDict({})}
        self.supported_version: Dict = {}
        self.version: Dict = {}
        self.tags: Dict = {}
        self.supported = False
        self.init_support()
        self.check_if_tiff_point_electronic()

    def init_support(self):
        """Init supported versions."""
        self.supported_version["tech_partner"] = ["point electronic"]
        self.supported_version["schema_name"] = ["DISS"]
        self.supported_version["schema_version"] = ["5.15.31.0"]

    def check_if_tiff_point_electronic(self):
        """Check if resource behind self.file_path is a TaggedImageFormat file.

        This also loads the metadata first if possible as these contain details
        about which software was used to process the image data, e.g. DISS software.
        """
        self.supported = 0  # voting-based
        with open(self.file_path, "rb", 0) as file:
            s = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)
            magic = s.read(4)
            if magic == b"II*\x00":  # https://en.wikipedia.org/wiki/TIFF
                self.supported += 1
            else:
                print(
                    f"Parser {self.__class__.__name__} finds no content in {self.file_path} that it supports"
                )
                self.supported = False
                return
        with Image.open(self.file_path, mode="r") as fp:
            # either hunt for metadata under tag_v2 key 700 or take advantage of the
            # fact that point electronic write xmpmeta/xmptk XMP Core 5.1.2
            meta = fd.FlatDict(fp.getxmp(), "/")
            if meta:
                if "xmpmeta/xmptk" in meta:
                    if meta["xmpmeta/xmptk"] in self.version:
                        if meta["xmpmeta/xmptk"] == "XMP Core 5.1.2":
                            # load the metadata
                            self.tmp["flatdict_meta"] = fd.FlatDict({}, "/")
                            for entry in meta["xmpmeta/RDF/Description"]:
                                tmp = fd.FlatDict(entry, "/")
                                for key, value in tmp.items():
                                    if value:
                                        if key not in self.tmp["flat_dict_meta"]:
                                            self.tmp["flat_dict_meta"][key] = value
                                        else:
                                            raise KeyError(f"Duplicated key {key} !")
                            # check if written about with supported DISS version
                            prefix = f"{self.supported_version['tech_partner']} {self.supported_version['schema_name']}"
                            supported_versions = [
                                f"{prefix} {val}"
                                for val in self.supported_version["schema_version"]
                            ]
                            print(supported_versions)
                            if (
                                self.tmp["flat_dict_meta"]["CreatorTool"]
                                in supported_versions
                            ):
                                self.supported += 1  # found specific XMP metadata
        if self.supported == 2:
            self.supported = True
        else:
            print(
                f"Parser {self.__class__.__name__} finds no content in {self.file_path} that it supports"
            )

    def parse_and_normalize(self):
        """Perform actual parsing filling cache self.tmp."""
        if self.supported is True:
            print(f"Parsing via point electronic DISS-specific metadata...")
            # metadata have at this point already been collected into an fd.FlatDict
        else:
            print(
                f"{self.file_path} is not a point electronic DISS-specific "
                f"TIFF file that this parser can process !"
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
            f"Writing point electronic DISS TIFF image data to the respective NeXus concept instances..."
        )
        # read image in-place
        image_identifier = 1
        with Image.open(self.file_path, mode="r") as fp:
            for img in ImageSequence.Iterator(fp):
                nparr = np.array(img)
                print(f"{type(nparr)}, {np.shape(nparr)}, {nparr.dtype}")
                print(fp.info)
                print(fp.size)
                print(np.mean(nparr))

                # eventually similar open discussions points as for the TFS TIFF parser
                trg = (
                    f"/ENTRY[entry{self.entry_id}]/measurement/EVENT_DATA_EM_SET[event_data_em_set]/"
                    f"EVENT_DATA_EM[event_data_em{self.event_id}]/"
                    f"IMAGE_R_SET[image_r_set{image_identifier}]/image_twod"
                )
                template[f"{trg}/title"] = f"Image"
                template[f"{trg}/@signal"] = "intensity"
                dims = ["x", "y"]
                idx = 0
                for dim in dims:
                    template[f"{trg}/@AXISNAME_indices[axis_{dim}_indices]"] = (
                        np.uint32(idx)
                    )
                    idx += 1
                template[f"{trg}/@axes"] = []
                for dim in dims[::-1]:
                    template[f"{trg}/@axes"].append(f"axis_{dim}")
                template[f"{trg}/intensity"] = {"compress": np.array(fp), "strength": 1}
                #  0 is y while 1 is x for 2d, 0 is z, 1 is y, while 2 is x for 3d
                template[f"{trg}/intensity/@long_name"] = f"Signal"

                sxy = {"x": 1.0, "y": 1.0}
                scan_unit = {"x": "m", "y": "m"}  # assuming FEI reports SI units
                # we may face the CCD overview camera for the chamber for which there might not be a calibration!
                if ("PixelSizeX" in self.tmp["flat_dict_meta"]) and (
                    "PixelSizeY" in self.tmp["flat_dict_meta"]
                ):
                    sxy = {
                        "x": self.tmp["flat_dict_meta"]["PixelSizeX"],
                        "y": self.tmp["flat_dict_meta"]["PixelSizeY"],
                    }
                else:
                    print("WARNING: Assuming pixel width and height unit is meter!")
                nxy = {"x": np.shape(np.array(fp))[1], "y": np.shape(np.array(fp))[0]}
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

    def add_change_me(self, template: dict) -> dict:
        # identifier = [self.entry_id, self.event_id, 1]
        # add_specific_metadata(
        #     TFS_APERTURE_STATIC_TO_NX_EM,
        #     self.tmp["flat_dict_meta"],
        #     identifier,
        #     template,
        # )
        return template

    def process_event_data_em_metadata(self, template: dict) -> dict:
        """Add respective metadata."""
        # contextualization to understand how the image relates to the EM session
        print(
            f"Mapping some of the point electronic DISS metadata on respective NeXus concepts..."
        )
        self.add_change_me(template)
        # TODO add more
        return template
