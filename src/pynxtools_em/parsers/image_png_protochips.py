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
"""Parser for exemplar reading of raw PNG files collected on a TEM with Protochip heating_chip."""

import datetime
import mmap
import re
from typing import Dict, List
from zipfile import ZipFile

import flatdict as fd
import numpy as np
import xmltodict
from PIL import Image
from pynxtools_em.concepts.mapping_functors_pint import (
    add_specific_metadata_pint,
    var_path_to_spcfc_path,
)
from pynxtools_em.configurations.image_png_protochips_cfg import (
    AXON_DYNAMIC_AUX_NX,
    AXON_DYNAMIC_CHIP_NX,
    AXON_DYNAMIC_STAGE_NX,
    AXON_DYNAMIC_VARIOUS_NX,
    AXON_STATIC_DETECTOR_NX,
    AXON_STATIC_STAGE_NX,
    specific_to_variadic,
)
from pynxtools_em.parsers.image_base import ImgsBaseParser
from pynxtools_em.utils.get_file_checksum import (
    DEFAULT_CHECKSUM_ALGORITHM,
    get_sha256_of_file_content,
)
from pynxtools_em.utils.pint_custom_unit_registry import ureg
from pynxtools_em.utils.sorting import sort_ascendingly_by_second_argument_iso8601
from pynxtools_em.utils.string_conversions import string_to_number
from pynxtools_em.utils.xml_utils import flatten_xml_to_dict


class ProtochipsPngSetParser(ImgsBaseParser):
    def __init__(self, file_path: str = "", entry_id: int = 1, verbose: bool = False):
        super().__init__(file_path)
        self.entry_id = entry_id
        self.event_id = 1
        self.dict_meta: Dict[str, fd.FlatDict] = {}
        self.version: Dict = {}
        self.png_info: Dict = {}
        self.supported = False
        self.event_sequence: List = []
        self.verbose = verbose
        self.check_if_zipped_png_protochips()
        if not self.supported:
            print(
                f"Parser {self.__class__.__name__} finds no content in {file_path} that it supports"
            )

    def check_if_zipped_png_protochips(self):
        """Check if resource behind self.file_path is a TaggedImageFormat file."""
        # all tests have to be passed before the input self.file_path
        # can at all be processed with this parser
        # test 1: check if file is a zipfile
        self.supported = False
        with open(self.file_path, "rb", 0) as file:
            s = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)
            magic = s.read(8)
            if (
                magic != b"PK\x03\x04\x14\x00\x08\x00"
            ):  # https://en.wikipedia.org/wiki/List_of_file_signatures
                # print(f"Test 1 failed, {self.file_path} is not a ZIP archive !")
                return
        # test 2: check if there are at all PNG files with iTXt metadata from Protochips in this zip file
        # collect all those PNGs to work with and write a tuple of their image dimensions
        with ZipFile(self.file_path) as zip_file_hdl:
            for file in zip_file_hdl.namelist():
                if file.lower().endswith(".png") is True:
                    with zip_file_hdl.open(file) as fp:
                        magic = fp.read(8)
                        if magic == b"\x89PNG\r\n\x1a\n":
                            method = "smart"  # "lazy"
                            # get image dimensions
                            if (
                                method == "lazy"
                            ):  # lazy but paid with the price of reading the image content
                                fp.seek(
                                    0
                                )  # seek back to beginning of file required because fp.read advanced fp implicitly!
                                with Image.open(fp) as png:
                                    try:
                                        nparr = np.array(png)
                                        self.png_info[file] = np.shape(nparr)
                                    except IOError:
                                        print(
                                            f"Loading image data in-place from {self.file_path}:{file} failed !"
                                        )
                            if (
                                method == "smart"
                            ):  # knowing where to hunt width and height in PNG metadata
                                # https://dev.exiv2.org/projects/exiv2/wiki/The_Metadata_in_PNG_files
                                magic = fp.read(8)
                                self.png_info[file] = (
                                    np.frombuffer(fp.read(4), dtype=">i4"),
                                    np.frombuffer(fp.read(4), dtype=">i4"),
                                )

        # test 3: check there are some PNGs
        if len(self.png_info.keys()) == 0:
            print("Test 3 failed, there are no PNGs !")
            return
        # test 4: check that all PNGs have the same dimensions, TODO::could check for other things here
        target_dims = None
        for tpl in self.png_info.values():
            if target_dims is not None:
                if tpl == target_dims:
                    continue
                else:
                    print("Test 4 failed, not all PNGs have the same dimensions")
                    return
            else:
                target_dims = tpl
        print("All tests passed successfully")
        self.supported = True

    def get_xml_metadata(self, file, fp):
        """Parse content from the XML payload that PNGs from AXON Studio have."""
        try:
            fp.seek(0)
            with Image.open(fp) as png:
                png.load()
                if "MicroscopeControlImage" in png.info.keys():
                    meta = flatten_xml_to_dict(
                        xmltodict.parse(png.info["MicroscopeControlImage"])
                    )
                    # first phase analyse the collection of Protochips metadata concept instance symbols and reduce to unique concepts
                    grpnm_lookup = {}
                    for concept, value in meta.items():
                        # not every key is allowed to define a concept
                        idxs = re.finditer(r".\[[0-9]+\].", concept)
                        if sum(1 for _ in idxs) > 0:  # is_variadic
                            markers = [".Name", ".PositionerName"]
                            for marker in markers:
                                if concept.endswith(marker):
                                    grpnm_lookup[
                                        f"{concept[0:len(concept)-len(marker)]}"
                                    ] = value
                        else:
                            grpnm_lookup[concept] = value
                    # second phase, evaluate each concept instance symbol wrt to its prefix coming from the unique concept
                    self.dict_meta[file] = fd.FlatDict({}, "/")
                    for k, v in meta.items():
                        grpnms = None
                        idxs = re.finditer(r".\[[0-9]+\].", k)
                        if sum(1 for _ in idxs) > 0:  # is variadic
                            search_argument = k[0 : k.rfind("].") + 1]
                            for parent_grpnm, child_grpnm in grpnm_lookup.items():
                                if parent_grpnm.startswith(search_argument):
                                    grpnms = (parent_grpnm, child_grpnm)
                                    break
                            if grpnms is not None:
                                if len(grpnms) == 2:
                                    if (
                                        "PositionerSettings" in k
                                        and k.endswith(".PositionerName") is False
                                    ):
                                        key = specific_to_variadic(
                                            f"{grpnms[0]}.{grpnms[1]}.{k[k.rfind('.') + 1:]}"
                                        )
                                        if key not in self.dict_meta[file]:
                                            self.dict_meta[file][key] = (
                                                string_to_number(v)
                                            )
                                        else:
                                            print(
                                                "Trying to register a duplicated key {key}"
                                            )
                                    if k.endswith(".Value"):
                                        key = specific_to_variadic(
                                            f"{grpnms[0]}.{grpnms[1]}"
                                        )
                                        if key not in self.dict_meta[file]:
                                            self.dict_meta[file][key] = (
                                                string_to_number(v)
                                            )
                                        else:
                                            print(
                                                f"Trying to register duplicated key {key}"
                                            )
                        else:
                            key = f"{k}"
                            if key not in self.dict_meta[file]:
                                self.dict_meta[file][key] = string_to_number(v)
                            else:
                                print(f"Trying to register duplicated key {key}")
                        # TODO::simplify and check that metadata end up correctly in self.dict_meta[file]
                    if self.verbose:
                        for key, value in self.dict_meta[file].items():
                            print(f"{key}____{type(value)}____{type(value)}")
        except ValueError:
            print(f"Flattening XML metadata content {self.file_path}:{file} failed !")

    def get_file_hash(self, file, fp):
        self.dict_meta[file]["sha256"] = get_sha256_of_file_content(fp)

    def parse(self, template: dict) -> dict:
        """Perform actual parsing filling cache."""
        if self.supported:
            print(
                f"Parsing via Protochips AXON Studio ZIP-compressed project parser..."
            )
            # may need to set self.supported = False on error
            with ZipFile(self.file_path) as zip_file_hdl:
                for file in self.png_info.keys():
                    with zip_file_hdl.open(file) as fp:
                        self.get_xml_metadata(file, fp)
                        self.get_file_hash(file, fp)
                        # print(f"Debugging self.tmp.file.items {file}")
                        # for k, v in self.dict_meta[file].items():
                        #     if k == "MicroscopeControlImageMetadata.MicroscopeDateTime":
                        #     print(f"{k}: {v}")
            print(
                f"{self.file_path} metadata within PNG collection processed "
                f"successfully ({len(self.dict_meta)} PNGs evaluated)."
            )
            self.process_event_data_em_metadata(template)
            self.process_event_data_em_data(template)
        else:
            print(
                f"{self.file_path} is not a Protochips-specific "
                f"PNG file that this parser can process !"
            )
        return template

    def sort_event_data_em(self) -> List:
        """Sort event data by datetime."""
        events: List = []
        for file_name, mdata in self.dict_meta.items():
            key = f"MicroscopeControlImageMetadata.MicroscopeDateTime"
            if isinstance(mdata, fd.FlatDict):
                if key in mdata:
                    if mdata[key].count(".") == 1:
                        datetime_obj = datetime.datetime.strptime(
                            mdata[key], "%Y-%m-%dT%H:%M:%S.%f%z"
                        )
                    else:
                        datetime_obj = datetime.datetime.strptime(
                            mdata[key], "%Y-%m-%dT%H:%M:%S%z"
                        )
                    events.append((f"{file_name}", datetime_obj))

        events_sorted = sort_ascendingly_by_second_argument_iso8601(events)
        del events
        time_series_start = events_sorted[0][1]
        print(f"Time series start: {time_series_start}")
        for file_name, iso8601 in events_sorted:
            continue
            # print(f"{file_name}, {iso8601}, {(iso8601 - time_series_start).total_seconds()} s")
        print(
            f"Time series end: {events_sorted[-1][1]}, {(events_sorted[-1][1] - time_series_start).total_seconds()} s"
        )
        return events_sorted

    def process_event_data_em_metadata(self, template: dict) -> dict:
        """Add respective metadata."""
        # contextualization to understand how the image relates to the EM session
        print(
            f"Mapping some of the Protochips metadata on respective NeXus concepts..."
        )
        # individual PNGs in self.file_path may include time/date information in the file name
        # surplus eventually AXON-specific identifier it seems useful though to sort these
        # PNGs based on time stamped information directly from the AXON metadata
        # here we sort ascendingly in time the events and associate new event ids
        # static instrument data

        self.event_sequence = self.sort_event_data_em()
        event_id = self.event_id
        toggle = True
        for file_name, iso8601 in self.event_sequence:
            identifier = [self.entry_id, event_id, 1]
            trg = var_path_to_spcfc_path(
                f"/ENTRY[entry*]/measurement/event_data_em_set/"
                f"EVENT_DATA_EM[event_data_em*]/start_time",
                identifier,
            )
            template[trg] = f"{iso8601}".replace(" ", "T")
            # AXON reports "yyyy-mm-dd hh-mm-ss*" but NeXus requires yyyy-mm-ddThh-mm-ss*"

            # static
            if toggle:
                for cfg in [AXON_STATIC_DETECTOR_NX, AXON_STATIC_STAGE_NX]:
                    add_specific_metadata_pint(
                        cfg,
                        self.dict_meta[file_name],
                        [1, 1],
                        template,
                    )
                toggle = False
            # dynamic
            for cfg in [
                AXON_DYNAMIC_CHIP_NX,
                AXON_DYNAMIC_AUX_NX,
                AXON_DYNAMIC_VARIOUS_NX,
            ]:
                add_specific_metadata_pint(
                    cfg,
                    self.dict_meta[file_name],
                    identifier,
                    template,
                )
            # additional dynamic data with currently different formatting
            add_specific_metadata_pint(
                AXON_DYNAMIC_STAGE_NX,
                self.dict_meta[file_name],
                identifier,
                template,
            )
            event_id += 1
        return template

    def process_event_data_em_data(self, template: dict) -> dict:
        """Add respective heavy data."""
        # default display of the image(s) representing the data collected in this event
        print(
            f"Writing Protochips PNG images into respective NeXus event_data_em concept instances"
        )
        # read image in-place
        event_id = self.event_id
        with ZipFile(self.file_path) as zip_file_hdl:
            for file_name, iso8601 in self.event_sequence:
                identifier = [self.entry_id, event_id, 1]
                with zip_file_hdl.open(file_name) as fp:
                    with Image.open(fp) as png:
                        nparr = np.array(png)
                        image_identifier = 1
                        trg = (
                            f"/ENTRY[entry{self.entry_id}]/measurement/event_data_em_set"
                            f"/EVENT_DATA_EM[event_data_em{event_id}]"
                            f"/IMAGE_SET[image_set{image_identifier}]/image_2d"
                        )
                        # TODO::writer should decorate automatically!
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
                        template[f"{trg}/real"] = {"compress": nparr, "strength": 1}
                        #  0 is y while 1 is x for 2d, 0 is z, 1 is y, while 2 is x for 3d
                        template[f"{trg}/real/@long_name"] = f"Signal"

                        sxy = {
                            "i": ureg.Quantity(1.0, ureg.meter),
                            "j": ureg.Quantity(1.0, ureg.meter),
                        }
                        abbrev = "MicroscopeControlImageMetadata.ImagerSettings.ImagePhysicalSize"
                        if (
                            f"{abbrev}.X" in self.dict_meta[file_name]
                            and f"{abbrev}.Y" in self.dict_meta[file_name]
                        ):
                            sxy = {
                                "i": ureg.Quantity(
                                    self.dict_meta[file_name][f"{abbrev}.X"],
                                    ureg.nanometer,
                                ),
                                "j": ureg.Quantity(
                                    self.dict_meta[file_name][f"{abbrev}.Y"],
                                    ureg.nanometer,
                                ),
                            }
                        nxy = {"i": np.shape(nparr)[1], "j": np.shape(nparr)[0]}
                        del nparr
                        # TODO::we assume here a very specific coordinate system see image_tiff_tfs.py
                        # parser for further details of the limitations of this approach
                        for dim in dims:
                            template[f"{trg}/AXISNAME[axis_{dim}]"] = {
                                "compress": np.asarray(
                                    np.linspace(
                                        0, nxy[dim] - 1, num=nxy[dim], endpoint=True
                                    )
                                    * sxy[dim].magnitude,
                                    np.float64,
                                ),
                                "strength": 1,
                            }
                            template[f"{trg}/AXISNAME[axis_{dim}]/@long_name"] = (
                                f"Coordinate along {dim}-axis ({sxy[dim].units})"
                            )
                            template[f"{trg}/AXISNAME[axis_{dim}]/@units"] = (
                                f"{sxy[dim].units}"
                            )
                event_id += 1
        return template
