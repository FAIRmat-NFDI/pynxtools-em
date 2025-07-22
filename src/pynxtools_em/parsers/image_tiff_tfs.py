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
"""Parser for harmonizing ThermoFisher-specific content in TIFF files."""

import mmap
from typing import Dict

import flatdict as fd
import numpy as np
from PIL import Image, ImageSequence

# https://www.loc.gov/preservation/digital/formats/content/tiff_tags.shtml
from pynxtools_em.concepts.mapping_functors_pint import add_specific_metadata_pint
from pynxtools_em.configurations.image_tiff_tfs_cfg import (
    TFS_DYNAMIC_OPTICS_NX,
    TFS_DYNAMIC_SCAN_NX,
    TFS_DYNAMIC_STAGE_NX,
    TFS_DYNAMIC_STIGMATOR_NX,
    TFS_DYNAMIC_VARIOUS_NX,
    TFS_STATIC_APERTURE_NX,
    TFS_STATIC_DETECTOR_NX,
    TFS_STATIC_VARIOUS_NX,
    TIFF_TFS_PARENT_CONCEPTS,
)
from pynxtools_em.utils.get_checksum import (
    DEFAULT_CHECKSUM_ALGORITHM,
    get_sha256_of_file_content,
)
from pynxtools_em.utils.image_utils import (
    if_str_represents_float,
    sort_ascendingly_by_second_argument,
)
from pynxtools_em.utils.pint_custom_unit_registry import ureg
from pynxtools_em.utils.tfs_utils import get_fei_childs


class TfsTiffParser:
    def __init__(self, file_path: str = "", entry_id: int = 1, verbose: bool = False):
        if file_path:
            self.file_path = file_path
        self.entry_id = entry_id if entry_id > 0 else 1
        self.verbose = verbose
        self.id_mgn: Dict[str, int] = {"event_id": 1}
        self.flat_dict_meta = fd.FlatDict({}, "/")
        self.version: Dict = {}
        self.supported = False
        self.check_if_tiff_tfs()
        if not self.supported:
            print(
                f"Parser {self.__class__.__name__} finds no content in {self.file_path} that it supports"
            )

    def check_if_tiff_tfs(self):
        """Check if resource behind self.file_path is a TaggedImageFormat file."""
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

        with Image.open(self.file_path, mode="r") as fp:
            tfs_keys = [34682]
            for tfs_key in tfs_keys:
                if tfs_key in fp.tag_v2:
                    if len(fp.tag_v2[tfs_key]) >= 1:
                        self.supported = True

    def get_metadata(self):
        """Extract metadata in TFS specific tags if present."""
        print("Parsing TIFF tags...")
        tfs_parent_concepts_byte_offset = {}
        for concept in TIFF_TFS_PARENT_CONCEPTS:
            tfs_parent_concepts_byte_offset[concept] = None
        with open(self.file_path, "rb", 0) as fp:
            s = mmap.mmap(fp.fileno(), 0, access=mmap.ACCESS_READ)
            for concept in TIFF_TFS_PARENT_CONCEPTS:
                pos = s.find(bytes(f"[{concept}]", "utf8"))  # != -1
                if pos != -1:
                    tfs_parent_concepts_byte_offset[concept] = pos
                # else:
                #     print(f"Instance of concept [{concept}] was not found !")
            if self.verbose:
                print(tfs_parent_concepts_byte_offset)

            sequence = []  # decide I/O order in which metadata for childs of parent concepts will be read
            for key, value in tfs_parent_concepts_byte_offset.items():
                if value is not None:
                    sequence.append((key, value))
                    # tuple of parent_concept name and byte offset
            sequence = sort_ascendingly_by_second_argument(sequence)
            if self.verbose:
                print(sequence)

            idx = 0
            for parent, byte_offset in sequence:
                pos_s = byte_offset
                pos_e = None
                if idx < len(sequence) - 1:
                    pos_e = sequence[idx + 1][1]
                else:
                    pos_e = np.iinfo(np.uint64).max
                    # TODO::better use official convention to not read beyond the end of file
                idx += 1
                if pos_s is None or pos_e is None:
                    print(
                        f"Definition of byte boundaries for reading childs of [{parent}] was unsuccessful !"
                    )
                # print(f"Search for [{parent}] in between byte offsets {pos_s} and {pos_e}")

                # fish metadata of e.g. the system section
                for term in get_fei_childs(parent):
                    s.seek(pos_s, 0)
                    pos = s.find(bytes(f"{term}=", "utf8"))
                    if -1 < pos < pos_e:  # check if pos_e is None
                        s.seek(pos, 0)
                        value = f"{s.readline().strip().decode('utf8').replace(f'{term}=', '')}"
                        self.flat_dict_meta[f"{parent}/{term}"] = None
                        if isinstance(value, str):
                            if value != "":
                                # execution order of the check here matters!
                                if value.isdigit() is True:
                                    self.flat_dict_meta[f"{parent}/{term}"] = np.int64(
                                        value
                                    )
                                elif if_str_represents_float(value) is True:
                                    self.flat_dict_meta[f"{parent}/{term}"] = (
                                        np.float64(value)
                                    )
                                else:
                                    self.flat_dict_meta[f"{parent}/{term}"] = value
                        else:
                            print(
                                f"Detected an unexpected case {parent}/{term}, type: {type(value)} !"
                            )
                    else:
                        break
            if self.verbose:
                for key, value in self.flat_dict_meta.items():
                    if value:
                        print(f"{key}____{type(value)}____{value}")

    def parse(self, template: dict) -> dict:
        """Perform actual parsing."""
        if self.supported:
            with open(self.file_path, "rb", 0) as fp:
                self.file_path_sha256 = get_sha256_of_file_content(fp)
            print(
                f"Parsing {self.file_path} TFS with SHA256 {self.file_path_sha256} ..."
            )
            self.get_metadata()
            self.process_event_data_em_metadata(template)
            self.process_event_data_em_data(template)
        return template

    def process_event_data_em_data(self, template: dict) -> dict:
        """Add respective heavy data."""
        # default display of the image(s) representing the data collected in this event
        print(f"Writing ThermoFisher TIFF image data to NeXus concept instances...")
        identifier_image = 1
        with Image.open(self.file_path, mode="r") as fp:
            for img in ImageSequence.Iterator(fp):
                nparr = np.array(img)
                # print(f"type: {type(nparr)}, dtype: {nparr.dtype}, shape: {np.shape(nparr)}")
                # TODO::discussion points
                # - how do you know we have an image of real space vs. imaginary space (from the metadata?)
                # - how do deal with the (ugly) scale bar that is typically stamped into the TIFF image content?
                # with H5Web and NeXus most of this is obsolete unless there are metadata stamped which are not
                # available in NeXus or in the respective metadata in the metadata section of the TIFF image
                # remember H5Web images can be scaled based on the metadata allowing basically the same
                # explorative viewing using H5Web than what traditionally typical image viewers are meant for
                trg = (
                    f"/ENTRY[entry{self.entry_id}]/measurement/eventID[event"
                    f"{self.id_mgn['event_id']}]/imageID[image{identifier_image}]/image_2d"
                )
                template[f"{trg}/title"] = f"Image"
                template[f"{trg}/@signal"] = "real"
                dims = ["i", "j"]
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
                # may face CCD overview camera of chamber that has no calibration!
                if ("EScan/PixelWidth" in self.flat_dict_meta) and (
                    "EScan/PixelHeight" in self.flat_dict_meta
                ):
                    sxy = {
                        "i": ureg.Quantity(
                            self.flat_dict_meta["EScan/PixelWidth"], ureg.meter
                        ),
                        "j": ureg.Quantity(
                            self.flat_dict_meta["EScan/PixelHeight"], ureg.meter
                        ),
                    }
                else:
                    print("WARNING: Assuming pixel width and height unit is unitless!")
                nxy = {"i": np.shape(np.array(fp))[1], "j": np.shape(np.array(fp))[0]}
                # TODO::be careful we assume here a very specific coordinate system
                # however the TIFF file gives no clue, TIFF just documents in which order
                # it arranges a bunch of pixels that have stream in into a n-d tiling
                # e.g. a 2D image
                # also we have to be careful because TFS just gives us here
                # typical case of an image without an information without its location
                # on the physical sample surface, therefore we can only scale
                # pixel_identifier by physical scaling quantities s_x, s_y
                # also the dimensions of the image are on us to fish with the image
                # reading library instead of TFS for consistency checks adding these
                # to the metadata the reason is that TFS TIFF use the TIFF tagging mechanism
                # and there is already a proper TIFF tag for the width and height of an
                # image in number of pixel
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
        print(f"Mapping some of the TFS/FEI metadata on respective NeXus concepts...")
        identifier = [self.entry_id, self.id_mgn["event_id"], 1]
        for cfg in [
            TFS_STATIC_APERTURE_NX,
            TFS_STATIC_DETECTOR_NX,
            TFS_STATIC_VARIOUS_NX,
            TFS_DYNAMIC_OPTICS_NX,
            TFS_DYNAMIC_SCAN_NX,
            TFS_DYNAMIC_VARIOUS_NX,
            TFS_DYNAMIC_STIGMATOR_NX,
        ]:  # TODO::static quantities may need to be splitted
            add_specific_metadata_pint(cfg, self.flat_dict_meta, identifier, template)
        add_specific_metadata_pint(
            TFS_DYNAMIC_STAGE_NX, self.flat_dict_meta, identifier, template
        )
        return template
