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
"""Parser for harmonizing point electronic DISS specific content in TIFF files."""

import mmap
from typing import Dict

import flatdict as fd
import numpy as np
from PIL import Image, ImageSequence

from pynxtools_em.concepts.mapping_functors_pint import add_specific_metadata_pint
from pynxtools_em.configurations.image_tiff_point_electronic_cfg import (
    DISS_DYNAMIC_VARIOUS_NX,
)
from pynxtools_em.utils.get_checksum import (
    DEFAULT_CHECKSUM_ALGORITHM,
    get_sha256_of_file_content,
)
from pynxtools_em.utils.pint_custom_unit_registry import ureg
from pynxtools_em.utils.string_conversions import string_to_number


class PointElectronicTiffParser:
    def __init__(self, file_path: str = "", entry_id: int = 1, verbose: bool = False):
        if file_path:
            self.file_path = file_path
        self.entry_id = entry_id if entry_id > 0 else 1
        self.verbose = verbose
        self.id_mgn: Dict[str, int] = {"event_id": 1}
        self.flat_metadata = fd.FlatDict({}, "/")
        self.version: Dict = {
            "trg": {
                "tech_partner": ["point electronic"],
                "schema_name": ["DISS"],
                "schema_version": ["5.15.31.0"],
            }
        }
        self.supported = False
        self.check_if_tiff_point_electronic()
        if not self.supported:
            print(
                f"Parser {self.__class__.__name__} finds no content in {file_path} that it supports"
            )

    def xmpmeta_to_flat_dict(self, meta: fd.FlatDict):
        """Flatten point-electronic formatting of XMPMeta data."""
        for entry in meta["xmpmeta/RDF/Description"]:
            tmp = fd.FlatDict(entry, "/")
            for key, obj in tmp.items():
                if isinstance(obj, list):
                    for dct in obj:
                        if isinstance(dct, dict):
                            lst = fd.FlatDict(dct, "/")
                            for kkey, kobj in lst.items():
                                if isinstance(kobj, str) and kobj != "":
                                    if f"{key}/{kkey}" not in self.flat_metadata:
                                        self.flat_metadata[f"{key}/{kkey}"] = (
                                            string_to_number(kobj)
                                        )
                elif isinstance(obj, str) and obj != "":
                    if key not in self.flat_metadata:
                        self.flat_metadata[key] = string_to_number(obj)
                    else:
                        print(f"Duplicated key {key} !")

    def check_if_tiff_point_electronic(self):
        """Check if resource behind self.file_path is a TaggedImageFormat file.

        This also loads the metadata first if possible as these contain details
        about which software was used to process the image data, e.g. DISS software.
        """
        self.supported = False
        try:
            with open(self.file_path, "rb", 0) as file:
                s = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)
                magic = s.read(4)
                if magic != b"II*\x00":  # https://en.wikipedia.org/wiki/TIFF
                    return
        except (FileNotFoundError, IOError):
            print(f"{self.file_path} either FileNotFound or IOError !")
            return

        votes_for_support = 0  # voting-based
        with Image.open(self.file_path, mode="r") as fp:
            # either hunt for metadata under tag_v2 key 700 or take advantage of the
            # fact that point electronic write xmpmeta/xmptk XMP Core 5.1.2
            meta = fd.FlatDict(fp.getxmp(), "/")
            if meta:
                if "xmpmeta/xmptk" in meta:
                    if meta["xmpmeta/xmptk"] == "XMP Core 5.1.2":
                        # load the metadata
                        self.flat_metadata = fd.FlatDict({}, "/")
                        self.xmpmeta_to_flat_dict(meta)

                        if self.verbose:
                            for key, value in self.flat_metadata.items():
                                print(f"{key}____{type(value)}____{value}")

                        # check if written about with supported DISS version
                        prefix = f"{self.version['trg']['tech_partner'][0]} {self.version['trg']['schema_name'][0]}"
                        supported_versions = [
                            f"{prefix} {val}"
                            for val in self.version["trg"]["schema_version"]
                        ]
                        print(supported_versions)
                        if self.flat_metadata["CreatorTool"] in supported_versions:
                            votes_for_support += 1  # found specific XMP metadata
        if votes_for_support == 1:
            self.supported = True

    def parse(self, template: dict) -> dict:
        """Perform actual parsing filling cache."""
        if self.supported:
            # metadata have at this point already been collected into an fd.FlatDict
            with open(self.file_path, "rb", 0) as fp:
                self.file_path_sha256 = get_sha256_of_file_content(fp)
            print(
                f"Parsing {self.file_path} point electronic DISS with SHA256 {self.file_path_sha256} ..."
            )
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

                sxy = {"i": ureg.Quantity(1.0), "j": ureg.Quantity(1.0)}
                if ("PixelSizeX" in self.flat_metadata) and (
                    "PixelSizeY" in self.flat_metadata
                ):
                    sxy = {
                        "i": ureg.Quantity(
                            self.flat_metadata["PixelSizeX"], ureg.meter
                        ),
                        "j": ureg.Quantity(
                            self.flat_metadata["PixelSizeY"], ureg.meter
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
        print(
            f"Mapping some of the point electronic DISS metadata on respective NeXus concepts..."
        )
        identifier = [self.entry_id, self.id_mgn["event_id"], 1]
        add_specific_metadata_pint(
            DISS_DYNAMIC_VARIOUS_NX,
            self.flat_metadata,
            identifier,
            template,
        )
        return template
