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

"""Parse Nion-specific content in a file containing a zip-compressed nionswift project."""

import glob
import json
import mmap
from typing import Dict
from zipfile import ZipFile

import flatdict as fd
import h5py
import nion.swift.model.NDataHandler as nsnd
import numpy as np
import yaml

# from pynxtools_em.utils.swift_generate_dimscale_axes \
#     import get_list_of_dimension_scale_axes
# from pynxtools_em.utils.swift_display_items_to_nx \
#     import nexus_concept_dict, identify_nexus_concept_key
# from pynxtools_em.concepts.concept_mapper \
#    import apply_modifier, variadic_path_to_specific_path
# from pynxtools_em.swift_to_nx_image_real_space \
#    import NxImageRealSpaceDict
from pynxtools_em.utils.get_file_checksum import (
    DEFAULT_CHECKSUM_ALGORITHM,
    get_sha256_of_file_content,
)
from pynxtools_em.utils.nion_utils import uuid_to_file_name


class NionProjectParser:
    """Parse (zip-compressed archive of a) nionswift project with its content."""

    def __init__(
        self, entry_id: int = 1, input_file_path: str = "", verbose: bool = True
    ):
        """Class wrapping swift parser."""
        if input_file_path is not None and input_file_path != "":
            self.file_path = input_file_path
        if entry_id > 0:
            self.entry_id = entry_id
        else:
            self.entry_id = 1
        # counters which keep track of how many instances of NXevent_data_em have
        # been instantiated, this implementation currently maps each display_items
        # onto an own NXevent_data_em instance
        self.prfx = None
        self.tmp: Dict = {}
        self.proj_file_dict: Dict = {}
        # assure that there is exactly one *.nsproj file only to parse from
        self.ndata_file_dict: Dict = {}
        # just get the *.ndata files irrespective whether parsed later or not
        self.hfive_file_dict: Dict = {}
        # just get the *.h5 files irrespective whether parsed later or not
        self.configure()
        self.supported = False
        self.verbose = verbose
        self.is_zipped = False
        self.check_if_nionswift_project()

    def configure(self):
        self.tmp["cfg"]: Dict = {}
        self.tmp["cfg"]["event_data_written"] = False
        self.tmp["cfg"]["event_data_em_id"] = 1
        self.tmp["cfg"]["image_id"] = 1
        self.tmp["cfg"]["spectrum_id"] = 1
        self.tmp["flat_dict_meta"] = fd.FlatDict({})

    def check_if_nionswift_project(self):
        """Inspect the content of the compressed project file to check if supported."""
        if self.file_path.endswith(".zip.nion"):
            self.is_zipped = True
        elif self.file_path.endswith(".nsproj"):
            self.is_zipped = False
        else:
            print(
                f"Parser NionProject finds no content in {self.file_path} that it supports"
            )
            return

        if self.is_zipped:
            with open(self.file_path, "rb", 0) as fp:
                s = mmap.mmap(fp.fileno(), 0, access=mmap.ACCESS_READ)
                magic = s.read(8)
                if self.verbose:
                    fp.seek(0, 2)
                    eof_byte_offset = fp.tell()
                    print(
                        f"Expecting zip-compressed file: ___{self.file_path}___{magic}___{get_sha256_of_file_content(fp)}___{eof_byte_offset}___"
                    )
                """
                if magic != b'PK\x03\x04':  # https://en.wikipedia.org/wiki/List_of_file_signatures
                    print(f"Test 1 failed, {self.file_path} is not a ZIP archive !")
                    return False
                """
            # analyze information content of the project and its granularization
            with ZipFile(self.file_path) as zip_file_hdl:
                for file in zip_file_hdl.namelist():
                    if file.endswith((".h5", ".hdf", ".hdf5")):
                        with zip_file_hdl.open(file) as fp:
                            magic = fp.read(8)
                            if self.verbose:
                                fp.seek(0, 2)
                                eof_byte_offset = fp.tell()
                                print(
                                    f"Expecting hfive: ___{file}___{magic}___{get_sha256_of_file_content(fp)}___{eof_byte_offset}___"
                                )
                            key = file[file.rfind("/") + 1 :].replace(".h5", "")
                            if key not in self.hfive_file_dict:
                                self.hfive_file_dict[key] = file
                    elif file.endswith(".ndata"):
                        with zip_file_hdl.open(file) as fp:
                            magic = fp.read(8)
                            if self.verbose:
                                fp.seek(0, 2)
                                eof_byte_offset = fp.tell()
                                print(
                                    f"Expecting ndata: ___{file}___{magic}___{get_sha256_of_file_content(fp)}___{eof_byte_offset}___"
                                )
                            key = file[file.rfind("/") + 1 :].replace(".ndata", "")
                            if key not in self.ndata_file_dict:
                                self.ndata_file_dict[key] = file
                    elif file.endswith(".nsproj"):
                        with zip_file_hdl.open(file) as fp:
                            magic = fp.read(8)
                            if self.verbose:
                                fp.seek(0, 2)
                                eof_byte_offset = fp.tell()
                                print(
                                    f"Expecting nsproj: ___{file}___{magic}___{get_sha256_of_file_content(fp)}___{eof_byte_offset}___"
                                )
                            key = file[file.rfind("/") + 1 :].replace(".nsproj", "")
                            if key not in self.proj_file_dict:
                                self.proj_file_dict[key] = file
                    else:
                        continue
        else:
            nsproj_data_path = f"{self.file_path[0:self.file_path.rfind('.')]} Data"
            print(f"nsproj_data_path __{nsproj_data_path}__")
            for file in glob.glob(f"{nsproj_data_path}/**/*", recursive=True):
                print(f"----->>>> {file}")
                if file.endswith((".h5", ".hdf", ".hdf5")):
                    with open(file, "rb") as fp:
                        magic = fp.read(8)
                        if self.verbose:
                            fp.seek(0, 2)
                            eof_byte_offset = fp.tell()
                            # get_sha256_of_file_content(fp)
                            print(
                                f"Expecting hfive: ___{file}___{magic}___{get_sha256_of_file_content(fp)}___{eof_byte_offset}___"
                            )
                        key = file[file.rfind("/") + 1 :].replace(".h5", "")
                        if key not in self.hfive_file_dict:
                            self.hfive_file_dict[key] = file
                elif file.endswith(".ndata"):
                    with open(file, "rb") as fp:
                        magic = fp.read(8)
                        if self.verbose:
                            fp.seek(0, 2)
                            eof_byte_offset = fp.tell()
                            print(
                                f"Expecting ndata: ___{file}___{magic}___{get_sha256_of_file_content(fp)}___{eof_byte_offset}___"
                            )
                        key = file[file.rfind("/") + 1 :].replace(".ndata", "")
                        if key not in self.ndata_file_dict:
                            self.ndata_file_dict[key] = file

        if not self.ndata_file_dict.keys().isdisjoint(self.hfive_file_dict.keys()):
            print(
                "Test 2 failed, UUID keys of *.ndata and *.h5 files in project are not disjoint!"
            )
            return
        if self.is_zipped and len(self.proj_file_dict.keys()) != 1:
            print(
                "Test 3 failed, he project contains either no or more than one nsproj file!"
            )
            return
        print(
            f"Content in zip-compressed nionswift project {self.file_path} passed all tests"
        )
        self.supported = True
        if self.verbose:
            for key, val in self.proj_file_dict.items():
                print(f"nsprj: ___{key}___{val}___")
            for key, val in self.ndata_file_dict.items():
                print(f"ndata: ___{key}___{val}___")
            for key, val in self.hfive_file_dict.items():
                print(f"hfive: ___{key}___{val}___")

    def update_event_identifier(self):
        """Advance and reset bookkeeping of event data em and data instances."""
        if self.tmp["cfg"]["event_data_written"] is True:
            self.tmp["cfg"]["event_data_em_id"] += 1
            self.tmp["cfg"]["event_data_written"] = False
        self.tmp["cfg"]["image_id"] = 1
        self.tmp["cfg"]["spectrum_id"] = 1

    def add_nx_image_real_space(self, meta, arr, template):
        """Create instance of NXimage_r_set"""
        # TODO::
        return template

    def map_to_nexus(self, meta, arr, concept_name, template):
        """Create the actual instance of a specific set of NeXus concepts in template."""
        # TODO::
        return template

    def process_ndata(self, file_hdl, full_path, template):
        """Handle reading and processing of opened *.ndata inside the ZIP file."""
        # assure that we start reading that file_hdl/pointer from the beginning...
        file_hdl.seek(0)
        local_files, dir_files, eocd = nsnd.parse_zip(file_hdl)
        flat_metadata_dict = {}
        """
        data_arr = None
        nx_concept_name = ""
        """
        print(
            f"Inspecting {full_path} with len(local_files.keys()) ___{len(local_files.keys())}___"
        )
        for offset, tpl in local_files.items():
            print(f"{offset}___{tpl}")
            # report to know there are more than metadata.json files in the ndata swift container format
            if tpl[0] == b"metadata.json":
                print(
                    f"Extract metadata.json from ___{full_path}___ at offset ___{offset}___"
                )
                # ... explicit jump back to beginning of the file
                file_hdl.seek(0)
                metadata_dict = nsnd.read_json(
                    file_hdl, local_files, dir_files, b"metadata.json"
                )
                """
                nx_concept_key = identify_nexus_concept_key(metadata_dict)
                nx_concept_name = nexus_concept_dict[nx_concept_key]
                print(f"Display_item {full_path}, concept {nx_concept_key}, maps {nx_concept_name}")
                """

                flat_metadata_dict = fd.FlatDict(metadata_dict, delimiter="/")
                if self.verbose:
                    print(f"Flattened content of this metadata.json")
                    for key, value in flat_metadata_dict.items():
                        print(f"ndata, metadata.json, flat: ___{key}___{value}___")
                # no break here, because we would like to inspect all content
                # expect (based on Benedikt's example) to find only one json file
                # in that *.ndata file pointed to by file_hdl
        if flat_metadata_dict == {}:  # only continue if some metadata were retrieved
            return template

        for offset, tpl in local_files.items():
            # print(f"{tpl}")
            if tpl[0] == b"data.npy":
                print(
                    f"Extract data.npy from ___{full_path}___ at offset ___{offset}___"
                )
                file_hdl.seek(0)
                data_arr = nsnd.read_data(file_hdl, local_files, dir_files, b"data.npy")
                if isinstance(data_arr, np.ndarray):
                    print(
                        f"ndata, data.npy, type, shape, dtype: ___{type(data_arr)}___{np.shape(data_arr)}___{data_arr.dtype}___"
                    )
                break
                # because we expect (based on Benedikt's example) to find only one npy file
                # in that *.ndata file pointed to by file_hdl

        # check on the integriety of the data_arr array that it is not None or empty
        # this should be done more elegantly by just writing the
        # data directly into the template and not creating another copy
        # TODO::only during inspection
        """
        self.map_to_nexus(flat_metadata_dict, data_arr, nx_concept_name, template)
        del flat_metadata_dict
        del data_arr
        del nx_concept_name
        """
        return template

    def process_hfive(self, file_hdl, full_path, template: dict):
        """Handle reading and processing of opened *.h5 inside the ZIP file."""
        flat_metadata_dict = {}
        """
        data_arr = None
        nx_concept_name = ""
        """
        file_hdl.seek(0)
        with h5py.File(file_hdl, "r") as h5r:
            print(
                f"Inspecting {full_path} with len(h5r.keys()) ___{len(h5r.keys())}___"
            )
            print(f"{h5r.keys()}")
            metadata_dict = json.loads(h5r["data"].attrs["properties"])

            """
            nx_concept_key = identify_nexus_concept_key(metadata_dict)
            nx_concept_name = nexus_concept_dict[nx_concept_key]
            print(f"Display_item {full_path}, concept {nx_concept_key}, maps {nx_concept_name}")
            """

            flat_metadata_dict = fd.FlatDict(metadata_dict, delimiter="/")
            if self.verbose:
                print(f"Flattened content of this metadata.json")
                for key, value in flat_metadata_dict.items():
                    print(f"hfive, data, flat: ___{key}___{value}___")

            if (
                flat_metadata_dict == {}
            ):  # only continue if some metadata were retrieved
                return template

            data_arr = h5r["data"][()]

            if isinstance(data_arr, np.ndarray):
                print(
                    f"hfive, data, type, shape, dtype: ___{type(data_arr)}___{np.shape(data_arr)}___{data_arr.dtype}___"
                )
            """
            print(f"data_arr type {data_arr.dtype}, shape {np.shape(data_arr)}")
            # check on the integriety of the data_arr array that it is not None or empty
            # this should be done more elegantly by just writing the
            # data directly into the template and not creating another copy
            self.map_to_nexus(flat_metadata_dict, data_arr, nx_concept_name, template)
            del flat_metadata_dict
            del data_arr
            del nx_concept_name
            """
        return template

    def parse_project_file(self, template: dict) -> dict:
        """Parse lazily from compressed NionSwift project (nsproj + directory)."""
        nionswift_proj_mdata = {}
        if self.is_zipped:
            with ZipFile(self.file_path) as zip_file_hdl:
                for pkey, proj_file_name in self.proj_file_dict.items():
                    with zip_file_hdl.open(proj_file_name) as file_hdl:
                        nionswift_proj_mdata = fd.FlatDict(
                            yaml.safe_load(file_hdl), delimiter="/"
                        )
        else:
            with open(self.file_path) as file_hdl:
                nionswift_proj_mdata = fd.FlatDict(
                    yaml.safe_load(file_hdl), delimiter="/"
                )
        # TODO::inspection phase, maybe with yaml to file?
        if self.verbose:
            if self.is_zipped:
                print(f"Flattened content of {proj_file_name}")
            else:
                print(f"Flattened content of {self.file_path}")
            for key, value in nionswift_proj_mdata.items():  # ["display_items"]:
                print(f"nsprj, flat: ___{key}___{value}___")
        if nionswift_proj_mdata == {}:
            return template

        for itm in nionswift_proj_mdata["display_items"]:
            if set(["type", "uuid", "created", "display_data_channels"]).issubset(
                itm.keys()
            ):
                if len(itm["display_data_channels"]) == 1:
                    if "data_item_reference" in itm["display_data_channels"][0].keys():
                        key = uuid_to_file_name(
                            itm["display_data_channels"][0]["data_item_reference"]
                        )
                        # file_name without the mime type
                        if key in self.ndata_file_dict.keys():
                            this_file = self.ndata_file_dict[key]
                            print(f"Key {key} is *.ndata maps to {this_file}")
                            print(f"Parsing {this_file}...")
                            if self.is_zipped:
                                with ZipFile(self.file_path) as zip_file_hdl:
                                    with zip_file_hdl.open(this_file) as file_hdl:
                                        self.process_ndata(
                                            file_hdl,
                                            this_file,
                                            template,
                                        )
                            else:
                                with open(this_file, "rb") as file_hdl:
                                    self.process_ndata(
                                        file_hdl,
                                        this_file,
                                        template,
                                    )
                        elif key in self.hfive_file_dict.keys():
                            this_file = self.hfive_file_dict[key]
                            print(f"Key {key} is *.h5 maps to {this_file}")
                            print(f"Parsing {this_file}...")
                            if self.is_zipped:
                                with ZipFile(self.file_path) as zip_file_hdl:
                                    with zip_file_hdl.open(this_file) as file_hdl:
                                        self.process_hfive(
                                            file_hdl,
                                            this_file,
                                            template,
                                        )
                            else:
                                with open(this_file, "rb") as file_hdl:
                                    self.process_hfive(
                                        file_hdl,
                                        this_file,
                                        template,
                                    )
                        else:
                            print(f"Key {key} has no corresponding data file")
        return template

    def parse(self, template: dict) -> dict:
        """Parse NOMAD OASIS relevant data and metadata from swift project."""
        if self.supported:
            if self.is_zipped:
                print(
                    "Parsing in-place zip-compressed nionswift project (nsproj + data)..."
                )
            else:
                print("Parsing in-place nionswift project (nsproj + data)...")
            self.parse_project_file(template)
        return template
