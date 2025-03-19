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
"""Parser for reading content from Gatan Digital Micrograph *.dm3 and *.dm4 (HDF5) via rosettasciio."""

from typing import Dict, List

import flatdict as fd
import numpy as np
from rsciio import digitalmicrograph as gatan

from pynxtools_em.concepts.mapping_functors_pint import add_specific_metadata_pint
from pynxtools_em.configurations.rsciio_gatan_cfg import (
    GATAN_DYNAMIC_STAGE_NX,
    GATAN_DYNAMIC_VARIOUS_NX,
    GATAN_STATIC_VARIOUS_NX,
    GATAN_WHICH_IMAGE,
    GATAN_WHICH_SPECTRUM,
)
from pynxtools_em.utils.gatan_utils import gatan_image_spectrum_or_generic_nxdata
from pynxtools_em.utils.get_file_checksum import (
    DEFAULT_CHECKSUM_ALGORITHM,
    get_sha256_of_file_content,
)
from pynxtools_em.utils.pint_custom_unit_registry import ureg
from pynxtools_em.utils.rsciio_hspy_utils import all_req_keywords_in_dict


class RsciioGatanParser:
    """Read Gatan Digital Micrograph dm3/dm4 formats."""

    def __init__(self, file_path: str = "", entry_id: int = 1, verbose: bool = False):
        if file_path:
            self.file_path = file_path
        self.entry_id = entry_id if entry_id > 0 else 1
        self.verbose = verbose
        self.id_mgn: Dict[str, int] = {"event_id": 1}
        self.version: Dict = {}
        self.supported = False
        self.check_if_supported()
        if not self.supported:
            print(
                f"Parser {self.__class__.__name__} finds no content in {file_path} that it supports"
            )

    def check_if_supported(self):
        self.supported = False
        if not self.file_path.lower().endswith(("dm3", "dm4")):
            return
        try:
            self.objs = gatan.file_reader(
                self.file_path, lazy=False, order="C", optimize=True
            )
            # TODO::what to do if the content of the file is larger than the available
            # main memory, make use of lazy loading

            reqs = ["data", "axes", "metadata", "original_metadata", "mapping"]
            obj_idx_supported: List[int] = []
            for idx, obj in enumerate(self.objs):
                if not isinstance(obj, dict):
                    continue
                if not all_req_keywords_in_dict(obj, reqs):
                    continue
                # flat_metadata = fd.FlatDict(obj["original_metadata"], "/")
                # TODO::add version distinction logic from rsciio_velox
                obj_idx_supported.append(idx)
                if self.verbose:
                    print(f"{idx}-th obj is supported")
            if len(obj_idx_supported) > 0:  # at least some supported content
                self.supported = True
        except (FileNotFoundError, IOError):
            print(f"{self.file_path} either FileNotFound or IOError !")
            return

    def parse(self, template: dict) -> dict:
        """Perform actual parsing."""
        if self.supported:
            with open(self.file_path, "rb", 0) as fp:
                self.file_path_sha256 = get_sha256_of_file_content(fp)
            print(
                f"Parsing {self.file_path} Gatan with SHA256 {self.file_path_sha256} ..."
            )
            self.parse_content(template)
        return template

    def parse_content(self, template: dict) -> dict:
        """Translate tech partner concepts to NeXus concepts."""
        reqs = ["data", "axes", "metadata", "original_metadata", "mapping"]
        for idx, obj in enumerate(self.objs):
            if not isinstance(obj, dict):
                continue
            if not all_req_keywords_in_dict(obj, reqs):
                continue
            self.process_event_data_em_metadata(obj, template)
            self.process_event_data_em_data(obj, template)
            self.id_mgn["event_id"] += 1
            if self.verbose:
                print(f"obj{idx}, dims {obj['axes']}")
        return template

    def process_event_data_em_metadata(self, obj: dict, template: dict) -> dict:
        """Map Gatan Digital Micrograph-specific concept representations on NeXus concepts."""
        # use an own function for each instead of a loop of a template function call
        # as for each section there are typically always some extra formatting
        # steps required
        flat_metadata = fd.FlatDict(obj["original_metadata"], "/")
        identifier = [self.entry_id, self.id_mgn["event_id"], 1]
        for cfg in [
            GATAN_STATIC_VARIOUS_NX,
            GATAN_DYNAMIC_STAGE_NX,
            GATAN_DYNAMIC_VARIOUS_NX,
        ]:
            add_specific_metadata_pint(cfg, flat_metadata, identifier, template)
        return template

    def annotate_information_source(
        self, src: str, trg: str, file_path: str, checksum: str, template: dict
    ) -> dict:
        """Add from where the information was obtained."""
        abbrev = "PROCESS[process]/source"
        template[f"{trg}/{abbrev}/type"] = "file"
        template[f"{trg}/{abbrev}/file_name"] = file_path
        template[f"{trg}/{abbrev}/checksum"] = checksum
        template[f"{trg}/{abbrev}/algorithm"] = DEFAULT_CHECKSUM_ALGORITHM
        if src != "":
            template[f"{trg}/{abbrev}/context"] = src
        return template

    def process_event_data_em_data(self, obj: dict, template: dict) -> dict:
        """Map Gatan-specifically formatted data arrays on NeXus NXdata/NXimage/NXspectrum."""
        # assume rosettasciio-specific formatting of the obj informationemd parser
        # i.e. a dictionary with the following keys:
        # "data", "axes", "metadata", "original_metadata", "mapping"
        flat_hspy_meta = fd.FlatDict(obj["metadata"], "/")
        if "General/title" not in flat_hspy_meta:
            return template

        # flat_orig_meta = fd.FlatDict(obj["original_metadata"], "/")
        axes = obj["axes"]
        unit_combination = gatan_image_spectrum_or_generic_nxdata(axes)
        if unit_combination == "":
            return template
        if self.verbose:
            print(axes)
            print(f"{unit_combination}, {np.shape(obj['data'])}")
            print(f"entry_id {self.entry_id}, event_id {self.id_mgn['event_id']}")

        prfx = f"/ENTRY[entry{self.entry_id}]/measurement/events/EVENT_DATA_EM[event_data_em{self.id_mgn['event_id']}]"
        self.id_mgn["event_id"] += 1

        # this is the place when you want to skip individually the writing of NXdata
        # return template

        axis_names = None
        if unit_combination in GATAN_WHICH_SPECTRUM:
            self.annotate_information_source(
                "",
                f"{prfx}/SPECTRUM[spectrum1]",
                self.file_path,
                self.file_path_sha256,
                template,
            )
            trg = f"{prfx}/SPECTRUM[spectrum1]/{GATAN_WHICH_SPECTRUM[unit_combination][0]}"
            template[f"{trg}/title"] = f"{flat_hspy_meta['General/title']}"
            template[f"{trg}/@signal"] = f"intensity"
            template[f"{trg}/intensity"] = {"compress": obj["data"], "strength": 1}
            template[f"{trg}/intensity/@long_name"] = f"Counts"
            axis_names = GATAN_WHICH_SPECTRUM[unit_combination][1]
        elif unit_combination in GATAN_WHICH_IMAGE:
            self.annotate_information_source(
                "",
                f"{prfx}/IMAGE[image1]",
                self.file_path,
                self.file_path_sha256,
                template,
            )
            trg = f"{prfx}/IMAGE[image1]/{GATAN_WHICH_IMAGE[unit_combination][0]}"
            template[f"{trg}/title"] = f"{flat_hspy_meta['General/title']}"
            template[f"{trg}/@signal"] = f"real"  # TODO::unless COMPLEX
            template[f"{trg}/real"] = {"compress": obj["data"], "strength": 1}
            template[f"{trg}/real/@long_name"] = f"Real part of the image intensity"
            axis_names = GATAN_WHICH_IMAGE[unit_combination][1]
        else:
            self.annotate_information_source(
                "",
                f"{prfx}/DATA[data1]",
                self.file_path,
                self.file_path_sha256,
                template,
            )
            trg = f"{prfx}/DATA[data1]"
            template[f"{trg}/title"] = f"{flat_hspy_meta['General/title']}"
            template[f"{trg}/@signal"] = f"data"
            template[f"{trg}/data"] = {"compress": obj["data"], "strength": 1}
            axis_names = ["axis_i", "axis_j", "axis_k", "axis_l", "axis_m"][
                0 : len(unit_combination.split("_"))
            ]  # mind, different to Nion and other tech partners here no [::-1] reversal
            # of the indices 241.a2c338fd458e6b7023ec946a5e3ce8c85bd2befcb5d17dae7ae5f44b2dede81b.dm4
            # is a good example!

        if len(axis_names) >= 1:
            # arrays axis_names and dimensional_calibrations are aligned in order
            # but that order is reversed wrt to AXISNAME_indices !
            for idx, axis_name in enumerate(axis_names):
                template[f"{trg}/@AXISNAME_indices[{axis_name}_indices]"] = np.uint32(
                    len(axis_names) - 1 - idx
                )  # TODO::check with dissimilarly sized data array if this is idx !
            template[f"{trg}/@axes"] = axis_names

            for idx, axis in enumerate(axes):
                axis_name = axis_names[idx]
                offset = axis["offset"]
                step = axis["scale"]
                units = axis["units"]
                count = np.shape(obj["data"])[idx]
                if units == "":
                    template[f"{trg}/AXISNAME[{axis_name}]"] = np.asarray(
                        offset
                        + np.linspace(0, count - 1, num=count, endpoint=True) * step,
                        dtype=np.float32,
                    )
                    if unit_combination in GATAN_WHICH_SPECTRUM:
                        template[f"{trg}/AXISNAME[{axis_name}]/@long_name"] = (
                            f"Identifier spectrum"
                        )
                    elif unit_combination in GATAN_WHICH_IMAGE:
                        template[f"{trg}/AXISNAME[{axis_name}]/@long_name"] = (
                            f"Iidentifier image"
                        )
                    else:
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
                    if (
                        ureg.Quantity(units).to_base_units().units
                        == "kilogram * meter ** 2 / second ** 2"
                    ):
                        template[f"{trg}/AXISNAME[{axis_name}]/@long_name"] = (
                            f"Energy ({ureg.Unit(units)})"
                        )
                    else:
                        template[f"{trg}/AXISNAME[{axis_name}]/@long_name"] = (
                            f"Point coordinate along {axis_name} ({ureg.Unit(units)})"
                        )
        return template
