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
"""Parser for harmonizing FEI-specific content in TIFF files for older legacy formats."""

# e.g. Tecnai TEM or Helios Nanolab FIB/SEM

import mmap
from typing import Dict

import flatdict as fd
import numpy as np
import xmltodict
from PIL import Image, ImageSequence
from pint import UndefinedUnitError

# https://www.loc.gov/preservation/digital/formats/content/tiff_tags.shtml
from pynxtools_em.concepts.mapping_functors_pint import add_specific_metadata_pint
from pynxtools_em.configurations.image_tiff_fei_cfg import (
    FEI_HELIOS_DYNAMIC_DETECTOR_NX,
    FEI_HELIOS_DYNAMIC_OPTICS_NX,
    FEI_HELIOS_DYNAMIC_SCAN_NX,
    FEI_HELIOS_DYNAMIC_STAGE_NX,
    FEI_HELIOS_DYNAMIC_STIGMATOR_NX,
    FEI_HELIOS_DYNAMIC_VARIOUS_NX,
    FEI_HELIOS_STATIC_VARIOUS_NX,
    FEI_TECNAI_DYNAMIC_OPTICS_NX,
    FEI_TECNAI_DYNAMIC_STAGE_NX,
    FEI_TECNAI_DYNAMIC_VARIOUS_NX,
    FEI_TECNAI_STATIC_VARIOUS_NX,
)
from pynxtools_em.utils.get_checksum import (
    DEFAULT_CHECKSUM_ALGORITHM,
    get_sha256_of_file_content,
)
from pynxtools_em.utils.pint_custom_unit_registry import ureg
from pynxtools_em.utils.string_conversions import string_to_number
from pynxtools_em.utils.xml_utils import flatten_xml_to_dict

# distinguish different types of legacy formats
FEI_LEGACY_UNKNOWN = 0
FEI_LEGACY_TECNAI_TEM = 1
FEI_LEGACY_HELIOS_SEM = 2


class FeiLegacyTiffParser:
    def __init__(self, file_path: str = "", entry_id: int = 1, verbose: bool = False):
        if file_path:
            self.file_path = file_path
        self.entry_id = entry_id if entry_id > 0 else 1
        self.verbose = verbose
        self.id_mgn: Dict[str, int] = {"event_id": 1}
        self.flat_dict_meta = fd.FlatDict({}, "/")
        self.version: Dict = {}
        self.supported: int = FEI_LEGACY_UNKNOWN
        self.check_if_tiff_fei_legacy()
        if not self.supported:
            print(
                f"Parser {self.__class__.__name__} finds no content in {self.file_path} that it supports"
            )

    def check_if_tiff_fei_legacy(self):
        """Check if resource behind self.file_path is a TaggedImageFormat file."""
        self.supported = FEI_LEGACY_UNKNOWN
        try:
            with open(self.file_path, "rb", 0) as file:
                s = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)
                magic = s.read(4)
                if magic != b"II*\x00":  # https://en.wikipedia.org/wiki/TIFF
                    return

                s.seek(0)

                # XML content suggestive of e.g. FEI Tecnai instruments
                pos_s = s.find(bytes(f"<Root>", "utf8"))
                pos_e = s.find(bytes(f"</Root>", "utf8"))
                if -1 < pos_s < pos_e:
                    pos_e += len(f"</Root>")
                    s.seek(pos_s)
                    # root = ET.fromstring(value)
                    tmp = flatten_xml_to_dict(xmltodict.parse(s.read(pos_e - pos_s)))
                    for key in tmp:
                        if key.endswith("Label"):
                            prefix = key[: len(key) - 5]
                            if all(
                                f"{prefix}{suffix}" in tmp
                                for suffix in ["Label", "Value", "Unit"]
                            ):
                                try:
                                    self.flat_dict_meta[tmp[f"{prefix}Label"]] = (
                                        ureg.Quantity(
                                            f"""{tmp[f"{prefix}Value"]} {tmp[f"{prefix}Unit"]}"""
                                        )
                                    )
                                except UndefinedUnitError:
                                    if tmp[f"{prefix}Value"] is not None:
                                        self.flat_dict_meta[tmp[f"{prefix}Label"]] = (
                                            string_to_number(tmp[f"{prefix}Value"])
                                        )
                    if "Microscope" in self.flat_dict_meta:
                        if "Tecnai" in self.flat_dict_meta["Microscope"]:
                            if self.verbose:
                                for key, val in self.flat_dict_meta.items():
                                    print(f"{key}, {val}, {type(val)}")
                            self.supported = FEI_LEGACY_TECNAI_TEM
                            return

                pos_s = s.find(bytes(f"<Metadata", "utf8"))
                pos_e = s.find(bytes(f"</Metadata>", "utf8"))
                if -1 < pos_s < pos_e:
                    pos_e += len(f"</Metadata>")
                    s.seek(pos_s)
                    tmp = flatten_xml_to_dict(xmltodict.parse(s.read(pos_e - pos_s)))
                    # TODO::Implement mapping for FEI_LEGACY_HELIOS_SEM
                    for key, val in tmp.items():
                        self.flat_dict_meta[key] = string_to_number(val)
                    if all(
                        val in self.flat_dict_meta
                        for val in [
                            "Metadata.Instrument.ControlSoftwareVersion",
                            "Metadata.Instrument.Manufacturer",
                            "Metadata.Instrument.InstrumentClass",
                        ]
                    ):
                        if self.flat_dict_meta[
                            "Metadata.Instrument.Manufacturer"
                        ].startswith("FEI") and self.flat_dict_meta[
                            "Metadata.Instrument.InstrumentClass"
                        ].startswith("Helios NanoLab"):
                            if self.verbose:
                                for key, val in self.flat_dict_meta.items():
                                    print(f"{key}, {val}, {type(val)}")
                            self.supported = FEI_LEGACY_HELIOS_SEM
                            print(
                                f"WARNING::TFS/FEI for TIFF stores in some cases the metadata in an XML block surplus ! a structure text appendix to the binary payload of the TIFF file !"
                            )
                            # this part of the legacy parser has been switched off
                            # for now as we expect that rather the newer structured text strategy
                            # will be continued to find usage
                            return

        except (FileNotFoundError, IOError):
            print(f"{self.file_path} either FileNotFound or IOError !")
            return

    def parse(self, template: dict) -> dict:
        """Perform actual parsing."""
        if self.supported == FEI_LEGACY_TECNAI_TEM:
            # do not use != FEI_LEGACY_UNKNOWN as the FEI_FEI_LEGACY_HELIOS_SEM part
            # has been switched off intentionally
            with open(self.file_path, "rb", 0) as fp:
                self.file_path_sha256 = get_sha256_of_file_content(fp)
            print(
                f"Parsing {self.file_path} FEI Legacy with SHA256 {self.file_path_sha256} ..."
            )
            self.process_event_data_em_metadata(template)
            self.process_event_data_em_data(template)
        return template

    def process_event_data_em_data(self, template: dict) -> dict:
        """Add respective heavy data."""
        # default display of the image(s) representing the data collected in this event
        print(f"Writing legacy FEI TIFF image data to NeXus concept instances...")
        # assuming same image FEI_LEGACY_TECNAI_TEM, FEI_LEGACY_HELIOS_SEM
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

                if self.supported == FEI_LEGACY_TECNAI_TEM:
                    print(
                        "WARNING: Unresolvable case, Tecnai instruments may not come with physical dimension per pixel data!"
                    )
                elif self.supported == FEI_LEGACY_HELIOS_SEM:
                    sxy = {
                        "i": ureg.Quantity(1.0),
                        "j": ureg.Quantity(1.0),
                    }
                    # may face CCD overview camera of chamber that has no calibration!
                    abbrev = "Metadata.BinaryResult.PixelSize"
                    if all(
                        key in self.flat_dict_meta
                        for key in [
                            f"{abbrev}.X.@unit",
                            f"{abbrev}.X.#text",
                            f"{abbrev}.Y.@unit",
                            f"{abbrev}.Y.#text",
                        ]
                    ):
                        sxy = {
                            "i": ureg.Quantity(
                                f"{self.flat_dict_meta[f'''{abbrev}.X.#text''']} {self.flat_dict_meta[f'''{abbrev}.X.@unit''']}"
                            ),
                            "j": ureg.Quantity(
                                f"{self.flat_dict_meta[f'''{abbrev}.Y.#text''']} {self.flat_dict_meta[f'''{abbrev}.Y.@unit''']}"
                            ),
                        }
                    else:
                        print(
                            "WARNING: Assuming pixel width and height unit is unitless!"
                        )

                nxy = {"i": np.shape(np.array(fp))[1], "j": np.shape(np.array(fp))[0]}
                # TODO::be careful we assume here a very specific coordinate system
                # https://www.loc.gov/preservation/digital/formats/content/tiff_tags.shtml
                # tags 40962 and 40963 do not exist in example datasets from the community!
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
                    if self.supported == FEI_LEGACY_TECNAI_TEM:
                        template[f"{trg}/AXISNAME[axis_{dim}]"] = {
                            "compress": np.asarray(
                                np.linspace(
                                    0, nxy[dim] - 1, num=nxy[dim], endpoint=True
                                ),
                                dtype=np.float32,
                            ),
                            "strength": 1,
                        }
                        template[f"{trg}/AXISNAME[axis_{dim}]/@long_name"] = (
                            f"Coordinate along {dim}-axis (pixel)"
                        )
                    elif self.supported == FEI_LEGACY_HELIOS_SEM:
                        template[f"{trg}/AXISNAME[axis_{dim}]"] = {
                            "compress": np.asarray(
                                np.linspace(
                                    0, nxy[dim] - 1, num=nxy[dim], endpoint=True
                                )
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
            f"Mapping some of the FEI Legacy metadata on respective NeXus concepts..."
        )
        identifier = [self.entry_id, self.id_mgn["event_id"], 1]
        if self.supported == FEI_LEGACY_TECNAI_TEM:
            for cfg in [
                FEI_TECNAI_DYNAMIC_OPTICS_NX,
                FEI_TECNAI_DYNAMIC_VARIOUS_NX,
                FEI_TECNAI_STATIC_VARIOUS_NX,
            ]:  # TODO::static quantities may need to be splitted
                add_specific_metadata_pint(
                    cfg, self.flat_dict_meta, identifier, template
                )
            add_specific_metadata_pint(
                FEI_TECNAI_DYNAMIC_STAGE_NX, self.flat_dict_meta, identifier, template
            )
        elif self.supported == FEI_LEGACY_HELIOS_SEM:
            for cfg in [
                FEI_HELIOS_DYNAMIC_DETECTOR_NX,
                FEI_HELIOS_DYNAMIC_OPTICS_NX,
                FEI_HELIOS_DYNAMIC_SCAN_NX,
                FEI_HELIOS_DYNAMIC_STIGMATOR_NX,
                FEI_HELIOS_DYNAMIC_VARIOUS_NX,
                FEI_HELIOS_STATIC_VARIOUS_NX,
            ]:
                add_specific_metadata_pint(
                    cfg, self.flat_dict_meta, identifier, template
                )
            add_specific_metadata_pint(
                FEI_HELIOS_DYNAMIC_STAGE_NX, self.flat_dict_meta, identifier, template
            )
        return template
