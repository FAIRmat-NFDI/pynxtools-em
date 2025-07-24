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
from typing import Dict, List
from zipfile import ZipFile

import flatdict as fd
import h5py
import nion.swift.model.NDataHandler as nsnd
import numpy as np
import yaml

from pynxtools_em.concepts.mapping_functors_pint import add_specific_metadata_pint
from pynxtools_em.configurations.nion_cfg import (
    NION_DYNAMIC_ABERRATION_NX,
    NION_DYNAMIC_DETECTOR_NX,
    NION_DYNAMIC_EVENT_TIME,
    NION_DYNAMIC_LENS_NX,
    NION_DYNAMIC_MAGBOARDS_NX,
    NION_DYNAMIC_SCAN_NX,
    NION_DYNAMIC_STAGE_NX,
    NION_DYNAMIC_VARIOUS_NX,
    NION_STATIC_DETECTOR_NX,
    NION_STATIC_LENS_NX,
    NION_WHICH_IMAGE,
    NION_WHICH_SPECTRUM,
)
from pynxtools_em.utils.get_checksum import (
    DEFAULT_CHECKSUM_ALGORITHM,
    get_sha256_of_file_content,
)
from pynxtools_em.utils.nion_utils import (
    nion_image_spectrum_or_generic_nxdata,
    uuid_to_file_name,
)
from pynxtools_em.utils.pint_custom_unit_registry import ureg


class NionProjectParser:
    """Parse (zip-compressed archive of a) nionswift project with its content."""

    def __init__(self, file_path: str = "", entry_id: int = 1, verbose: bool = False):
        """Class wrapping swift parser."""
        if file_path:
            self.file_path = file_path
        self.entry_id = entry_id if entry_id > 0 else 1
        self.verbose = verbose
        self.id_mgn: Dict[str, int] = {"event_id": 1}
        # counters which keep track of how many instances of NXevent_data_em have
        # been instantiated, this implementation currently maps each display_items
        # onto an own NXevent_data_em instance
        self.file_path_sha256 = None
        self.proj_file_dict: Dict = {}
        # assure that there is exactly one *.nsproj file only to parse from
        self.ndata_file_dict: Dict = {}
        # just get the *.ndata files irrespective whether parsed later or not
        self.hfive_file_dict: Dict = {}
        # just get the *.h5 files irrespective whether parsed later or not
        self.supported = False
        self.is_zipped = False
        self.check_if_nionswift_project()
        # eventually allow https://github.com/miurahr/py7zr/ to work with 7z directly

    def check_if_nionswift_project(self):
        """Inspect the content of the compressed project file to check if supported."""
        self.supported = False
        if self.file_path.endswith(".zip"):
            self.is_zipped = True
        elif self.file_path.endswith(".nsproj"):
            self.is_zipped = False
        else:
            print(
                f"Parser NionProject finds no content in {self.file_path} that it supports"
            )
            return

        if self.is_zipped:
            try:
                with open(self.file_path, "rb", 0) as fp:
                    s = mmap.mmap(fp.fileno(), 0, access=mmap.ACCESS_READ)
                    magic = s.read(4)
                    if (
                        magic != b"PK\x03\x04"
                    ):  # https://en.wikipedia.org/wiki/List_of_file_signatures
                        return
                    if self.verbose:
                        fp.seek(0, 2)
                        eof_byte_offset = fp.tell()
                        print(
                            f"Expecting zip-compressed file: ___{self.file_path}___{magic}___{get_sha256_of_file_content(fp)}___{eof_byte_offset}___"
                        )
            except (FileNotFoundError, IOError):
                print(f"{self.file_path} either FileNotFound or IOError !")
                return

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
            nsproj_data_path = f"{self.file_path[0 : self.file_path.rfind('.')]} Data"
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

    def annotate_information_source(
        self, src: str, trg: str, file_path: str, checksum: str, template: dict
    ) -> dict:
        """Add from where the information was obtained."""
        abbrev = "PROCESS[process]/input"
        # template[f"{trg}/{abbrev}/type"] = "file"
        # template[f"{trg}/{abbrev}/file_name"] = file_path
        # deactivate checksum computation for to reduce computational costs
        # template[f"{trg}/{abbrev}/checksum"] = checksum
        # template[f"{trg}/{abbrev}/algorithm"] = DEFAULT_CHECKSUM_ALGORITHM
        if src != "":
            template[f"{trg}/{abbrev}/context"] = f"{src}"
        return template

    def process_ndata(self, file_hdl, full_path: str, template: dict) -> dict:
        """Handle reading and processing of opened *.ndata inside the ZIP file."""
        # assure that we start reading that file_hdl/pointer from the beginning...
        file_hdl.seek(0)
        local_files, dir_files, eocd = nsnd.parse_zip(file_hdl)
        flat_metadata = fd.FlatDict({}, "/")
        print(
            f"Inspecting {full_path} with len(local_files.keys()) ___{len(local_files.keys())}___"
        )
        for offset, tpl in local_files.items():
            if self.verbose:
                print(f"{offset}___{tpl}")
            # report to know there are more than metadata.json files in the ndata swift container format
            if tpl[0] == b"metadata.json":
                if self.verbose:
                    print(
                        f"Extract metadata.json from ___{full_path}___ at offset ___{offset}___"
                    )
                # ... explicit jump back to beginning of the file
                file_hdl.seek(0)
                flat_metadata = fd.FlatDict(
                    nsnd.read_json(file_hdl, local_files, dir_files, b"metadata.json"),
                    "/",
                )

                if self.verbose:
                    print(f"Flattened content of this metadata.json")
                    for key, value in flat_metadata.items():
                        print(f"ndata, metadata.json, flat: ___{key}___{value}___")
                else:
                    break
                # previously no break here because we used verbose == True to log the analysis
                # of all datasets that were collected in the last 5years on the NionHermes
                # within the HU EM group lead by C. Koch and team, specifically we exported the
                # metadata to learn about a much larger usage variety to guide the
                # implementation of this parser, we expected though always to find only
                # one file named metadata.json in that *.ndata file pointed to by file_hdl
        if len(flat_metadata) == 0:
            return template

        for offset, tpl in local_files.items():
            if tpl[0] == b"data.npy":
                if self.verbose:
                    print(
                        f"Extract data.npy from ___{full_path}___ at offset ___{offset}___"
                    )
                file_hdl.seek(0)
                nparr = nsnd.read_data(file_hdl, local_files, dir_files, b"data.npy")
                if isinstance(nparr, np.ndarray):
                    print(
                        f"ndata, data.npy, type, shape, dtype: ___{type(nparr)}___{np.shape(nparr)}___{nparr.dtype}___"
                    )
                # because we expect (based on Benedikt's example) to find only one npy
                # file in that *.ndata file pointed to by file_hdl and only one matching
                # metadata.json we can now write the data and its metadata into template
                self.process_event_data_em_metadata(flat_metadata, template)
                self.process_event_data_em_data(
                    full_path, nparr, flat_metadata, template
                )
                break
        return template

    def process_hfive(self, file_hdl, full_path: str, template: dict) -> dict:
        """Handle reading and processing of opened *.h5 inside the ZIP file."""
        flat_metadata = fd.FlatDict({}, "/")
        file_hdl.seek(0)
        with h5py.File(file_hdl, "r") as h5r:
            print(
                f"Inspecting {full_path} with len(h5r.keys()) ___{len(h5r.keys())}___"
            )
            print(f"{h5r.keys()}")
            flat_metadata = fd.FlatDict(
                json.loads(h5r["data"].attrs["properties"]), "/"
            )
            if self.verbose:
                print(f"Flattened content of this metadata.json")
                for key, value in flat_metadata.items():
                    print(f"hfive, data, flat: ___{key}___{value}___")

            if len(flat_metadata) == 0:
                return template

            self.process_event_data_em_metadata(flat_metadata, template)

            nparr = h5r["data"][()]
            if isinstance(nparr, np.ndarray):
                print(
                    f"hfive, data, type, shape, dtype: ___{type(nparr)}___{np.shape(nparr)}___{nparr.dtype}___"
                )
            self.process_event_data_em_data(full_path, nparr, flat_metadata, template)
        return template

    def parse_project_file(self, template: dict) -> dict:
        """Parse lazily from compressed NionSwift project (nsproj + directory)."""
        nionswift_proj_mdata = {}
        if self.is_zipped:
            with ZipFile(self.file_path) as zip_file_hdl:
                for pkey, proj_file_name in self.proj_file_dict.items():
                    with zip_file_hdl.open(proj_file_name) as file_hdl:
                        nionswift_proj_mdata = fd.FlatDict(
                            yaml.safe_load(file_hdl), "/"
                        )
        else:
            with open(self.file_path) as file_hdl:
                nionswift_proj_mdata = fd.FlatDict(yaml.safe_load(file_hdl), "/")
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

    def process_event_data_em_metadata(
        self, flat_metadata: fd.FlatDict, template: dict
    ) -> dict:
        print(f"Mapping some of the Nion metadata on respective NeXus concepts...")
        # we assume for now dynamic quantities can just be repeated
        identifier = [self.entry_id, self.id_mgn["event_id"], 1]
        for cfg in [
            NION_DYNAMIC_ABERRATION_NX,
            NION_DYNAMIC_DETECTOR_NX,
            NION_DYNAMIC_LENS_NX,
            NION_DYNAMIC_MAGBOARDS_NX,
            NION_DYNAMIC_SCAN_NX,
            NION_DYNAMIC_STAGE_NX,
            NION_DYNAMIC_VARIOUS_NX,
            NION_DYNAMIC_EVENT_TIME,
        ]:
            add_specific_metadata_pint(cfg, flat_metadata, identifier, template)
        # but not so static quantities, for these we ideally need to check if
        # exactly the same data havent already been written in an effort to avoid
        # redundancies
        # most use cases simply avoid this complication as they assume well these
        # metadata are delivered by the ELN and thus a different serialization code
        # is used, like oasis_cfg or eln_cfg parsing as also pynxtools-em offers

        # nasty assume there is only one e.g. direct electron detector
        identifier = [self.entry_id, 1]
        add_specific_metadata_pint(
            NION_STATIC_DETECTOR_NX, flat_metadata, identifier, template
        )
        add_specific_metadata_pint(
            NION_STATIC_LENS_NX, flat_metadata, identifier, template
        )
        return template

    def process_event_data_em_data(
        self,
        ifo_src: str,
        nparr: np.ndarray,
        flat_metadata: fd.FlatDict,
        template: dict,
    ) -> dict:
        """Map Nion-specifically formatted data arrays on NeXus NXdata/NXimage/NXspectrum."""
        axes = flat_metadata["dimensional_calibrations"]
        unit_combination = nion_image_spectrum_or_generic_nxdata(axes)
        print(f"{unit_combination}, {np.shape(nparr)}")
        print(axes)
        print(f"entry_id {self.entry_id}, event_id {self.id_mgn['event_id']}")
        if unit_combination == "":
            return template

        prfx = f"/ENTRY[entry{self.entry_id}]/measurement/eventID[event{self.id_mgn['event_id']}]"
        self.id_mgn["event_id"] += 1

        # this is the place when you want to skip individually the writing of NXdata
        # return template

        axis_names = None
        if unit_combination in NION_WHICH_SPECTRUM:
            trg = f"{prfx}/spectrumID[spectrum1]/{NION_WHICH_SPECTRUM[unit_combination][0]}"
            self.annotate_information_source(
                ifo_src, f"{prfx}/spectrumID[spectrum1]", "", "", template
            )
            template[f"{trg}/title"] = f"{flat_metadata['title']}"
            template[f"{trg}/@signal"] = f"intensity"
            template[f"{trg}/intensity"] = {"compress": nparr, "strength": 1}
            template[f"{trg}/intensity/@long_name"] = f"Counts"
            axis_names = NION_WHICH_SPECTRUM[unit_combination][1]
        elif unit_combination in NION_WHICH_IMAGE:
            trg = f"{prfx}/imageID[image1]/{NION_WHICH_IMAGE[unit_combination][0]}"
            self.annotate_information_source(
                ifo_src, f"{prfx}/imageID[image1]", "", "", template
            )
            template[f"{trg}/title"] = f"{flat_metadata['title']}"
            template[f"{trg}/@signal"] = f"real"  # TODO::unless COMPLEX
            template[f"{trg}/real"] = {"compress": nparr, "strength": 1}
            template[f"{trg}/real/@long_name"] = f"Real part of the image intensity"
            axis_names = NION_WHICH_IMAGE[unit_combination][1]
        elif not any(
            (value in ["1/", "iteration"]) for value in unit_combination.split(";")
        ):
            trg = f"{prfx}/DATA[data1]"
            self.annotate_information_source(
                ifo_src, f"{prfx}/DATA[data1]", "", "", template
            )
            template[f"{trg}/title"] = f"{flat_metadata['title']}"
            template[f"{trg}/@signal"] = f"data"
            template[f"{trg}/data"] = {"compress": nparr, "strength": 1}
            axis_names = ["axis_i", "axis_j", "axis_k", "axis_m", "axis_n"][
                0 : len(unit_combination.split("_"))
            ][::-1]
        else:
            print(f"WARNING::{unit_combination} unsupported unit_combination !")
            return template

        if len(axis_names) >= 1:
            # arrays axis_names and dimensional_calibrations are aligned in order
            # but that order is reversed wrt to AXISNAME_indices !
            for idx, axis_name in enumerate(axis_names):
                template[f"{trg}/@AXISNAME_indices[{axis_name}_indices]"] = np.uint32(
                    len(axis_names) - 1 - idx
                )
            template[f"{trg}/@axes"] = axis_names

            for idx, axis in enumerate(axes):
                axis_name = axis_names[idx]
                offset = axis["offset"]
                step = axis["scale"]
                units = axis["units"]
                count = np.shape(nparr)[idx]
                if units == "":
                    if unit_combination in NION_WHICH_SPECTRUM:
                        template[f"{trg}/AXISNAME[{axis_name}]"] = np.asarray(
                            offset
                            + np.linspace(0, count - 1, num=count, endpoint=True)
                            * step,
                            dtype=np.int32,
                        )
                        template[f"{trg}/AXISNAME[{axis_name}]/@long_name"] = (
                            f"Identifier spectrum"
                        )
                    elif unit_combination in NION_WHICH_IMAGE:
                        template[f"{trg}/AXISNAME[{axis_name}]"] = np.asarray(
                            offset
                            + np.linspace(0, count - 1, num=count, endpoint=True)
                            * step,
                            dtype=np.int32,
                        )
                        template[f"{trg}/AXISNAME[{axis_name}]/@long_name"] = (
                            f"Identifier image"
                        )
                    else:
                        template[f"{trg}/AXISNAME[{axis_name}]"] = np.asarray(
                            offset
                            + np.linspace(0, count - 1, num=count, endpoint=True)
                            * step,
                            dtype=np.float32,
                        )
                        template[f"{trg}/AXISNAME[{axis_name}]/@long_name"] = (
                            f"{axis_name}"
                            # unitless | dimensionless i.e. no unit in longname
                        )
                else:
                    template[f"{trg}/AXISNAME[{axis_name}]"] = np.asarray(
                        offset
                        + np.linspace(0, count - 1, num=count, endpoint=True) * step,
                        dtype=np.float32,
                    )
                    template[f"{trg}/AXISNAME[{axis_name}]/@units"] = (
                        f"{ureg.Unit(units)}"
                    )
                    if units == "eV":
                        # TODO::this is only robust if Nion reports always as eV and not with other prefix like kilo etc.
                        # in such case the solution from the gatan parser is required, i.e. conversion to base units
                        template[f"{trg}/AXISNAME[{axis_name}]/@long_name"] = (
                            f"Energy ({ureg.Unit(units)})"  # eV
                        )
                    else:
                        template[f"{trg}/AXISNAME[{axis_name}]/@long_name"] = (
                            f"Coordinate along {axis_name.replace('axis_', '')}-axis ({ureg.Unit(units)})"
                        )
        return template
