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
"""Parser for reading content from ThermoFisher Velox *.emd (HDF5) via rosettasciio."""

from typing import Dict, List

import flatdict as fd
import numpy as np
from pynxtools_em.concepts.mapping_functors_pint import add_specific_metadata_pint
from pynxtools_em.configurations.rsciio_velox_cfg import (
    VELOX_DYNAMIC_EBEAM_NX,
    VELOX_DYNAMIC_OPTICS_NX,
    VELOX_DYNAMIC_SCAN_NX,
    VELOX_DYNAMIC_STAGE_NX,
    VELOX_DYNAMIC_VARIOUS_NX,
    VELOX_STATIC_EBEAM_NX,
    VELOX_STATIC_ENTRY_NX,
    VELOX_STATIC_FABRICATION_NX,
    VELOX_WHICH_IMAGE,
    VELOX_WHICH_SPECTRUM,
)
from pynxtools_em.utils.get_file_checksum import (
    DEFAULT_CHECKSUM_ALGORITHM,
    get_sha256_of_file_content,
)
from pynxtools_em.utils.pint_custom_unit_registry import ureg
from pynxtools_em.utils.rsciio_hspy_utils import all_req_keywords_in_dict
from pynxtools_em.utils.string_conversions import string_to_number
from pynxtools_em.utils.velox_utils import velox_image_spectrum_or_generic_nxdata
from rsciio import emd


class RsciioVeloxParser:
    """Read Velox EMD File Format emd."""

    def __init__(self, file_path: str = "", entry_id: int = 1, verbose: bool = False):
        if file_path:
            self.file_path = file_path
        self.entry_id = entry_id if entry_id > 0 else 1
        self.verbose = verbose
        # for id_mgn check pynxtools-em v0.2 of this velox reader
        self.id_mgn: Dict = {
            "event_id": 1,
            "event_img": 1,
            "event_spc": 1,
            "roi": 1,
            "eds_img": 1,
        }
        self.version: Dict = {
            "trg": {
                "Core/MetadataDefinitionVersion": ["7.9"],
                "Core/MetadataSchemaVersion": ["v1/2013/07"],
            },
            "src": {
                "Core/MetadataDefinitionVersion": None,
                "Core/MetadataSchemaVersion": None,
            },
        }
        self.obj_idx_supported: List = []
        self.supported = False
        self.check_if_supported()
        if not self.supported:
            print(
                f"Parser {self.__class__.__name__} finds no content in {file_path} that it supports"
            )

    def check_if_supported(self):
        self.supported = False
        try:
            self.objs = emd.file_reader(self.file_path)
            # TODO::what to do if the content of the file is larger than the available
            # main memory, one approach to handle this is to have the file_reader parsing
            # only the collection of the concepts without the actual instance data
            # based on this one could then plan how much memory has to be reserved
            # in the template and stream out accordingly

            with open(self.file_path, "rb", 0) as fp:
                self.file_path_sha256 = get_sha256_of_file_content(fp)

            print(f"Parsing {self.file_path} with SHA256 {self.file_path_sha256} ...")

            reqs = ["data", "axes", "metadata", "original_metadata", "mapping"]
            for idx, obj in enumerate(self.objs):
                if not isinstance(obj, dict):
                    continue
                if not all_req_keywords_in_dict(obj, reqs):
                    continue
                orgmeta = fd.FlatDict(
                    obj["original_metadata"], "/"
                )  # could be optimized
                if "Core/MetadataDefinitionVersion" in orgmeta:
                    if (
                        orgmeta["Core/MetadataDefinitionVersion"]
                        not in self.version["trg"]["Core/MetadataDefinitionVersion"]
                    ):
                        continue
                    if (
                        orgmeta["Core/MetadataSchemaVersion"]
                        not in self.version["trg"]["Core/MetadataSchemaVersion"]
                    ):
                        continue
                self.obj_idx_supported.append(idx)
                if self.verbose:
                    print(f"{idx}-th obj is supported")
            if (
                len(self.obj_idx_supported) > 0
            ):  # there is at least some supported content
                self.supported = True
        except (FileNotFoundError, IOError, ValueError):
            print(f"{self.file_path} FileNotFound, IOError, or ValueError !")
            return

    def parse(self, template: dict) -> dict:
        """Perform actual parsing."""
        if self.supported:
            with open(self.file_path, "rb", 0) as fp:
                self.file_path_sha256 = get_sha256_of_file_content(fp)
            print(
                f"Parsing {self.file_path} Velox with SHA256 {self.file_path_sha256} ..."
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
            self.process_event_data_em_data(obj, template)
            if self.verbose:
                print(f"obj{idx}, dims {obj['axes']}")
        return template

    def process_event_data_em_metadata(self, obj: dict, template: dict) -> dict:
        """Map some of the TFS/FEI/Velox-specific metadata concepts on NeXus concepts."""
        identifier = [self.entry_id, self.id_mgn["event_id"], 1]
        flat_orig_meta = fd.FlatDict(obj["original_metadata"], "/")

        if (len(identifier) != 3) or (not all(isinstance(x, int) for x in identifier)):
            print(f"Argument identifier {identifier} needs three int values!")
        trg = (
            f"/ENTRY[entry{identifier[0]}]/measurement/event_data_em_set/EVENT_DATA_EM"
            f"[event_data_em{identifier[1]}]/em_lab/ebeam_column"
        )
        # using an own function like add_dynamic_lens_metadata may be needed
        # if specific NeXus group have some extra formatting
        lens_idx = 1
        for lens_name in [
            "C1",
            "C2",
            "Diffraction",
            "Gun",
            "Intermediate",
            "MiniCondenser",
            "Objective",
            "Projector1",
            "Projector2",
        ]:
            toggle = False
            if f"Optics/{lens_name}LensIntensity" in flat_orig_meta:
                template[f"{trg}/lensID[lens{lens_idx}]/value"] = string_to_number(
                    flat_orig_meta[f"Optics/{lens_name}LensIntensity"]
                )
                # TODO::unit?
                toggle = True
            if f"Optics/{lens_name}LensMode" in flat_orig_meta:
                template[f"{trg}/lensID[lens{lens_idx}]/mode"] = string_to_number(
                    flat_orig_meta[f"Optics/{lens_name}LensMode"]
                )
                toggle = True
            if toggle:
                template[f"{trg}/lensID[lens{lens_idx}]/name"] = f"{lens_name}"
                lens_idx += 1
        # Optics/GunLensSetting

        for cfg in [
            VELOX_STATIC_ENTRY_NX,
            VELOX_STATIC_EBEAM_NX,
            VELOX_DYNAMIC_SCAN_NX,
            VELOX_DYNAMIC_VARIOUS_NX,
            VELOX_DYNAMIC_OPTICS_NX,
        ]:
            add_specific_metadata_pint(cfg, flat_orig_meta, identifier, template)

        add_specific_metadata_pint(
            VELOX_STATIC_FABRICATION_NX, flat_orig_meta, identifier, template
        )
        add_specific_metadata_pint(
            VELOX_DYNAMIC_STAGE_NX, flat_orig_meta, identifier, template
        )
        add_specific_metadata_pint(
            VELOX_DYNAMIC_EBEAM_NX, flat_orig_meta, identifier, template
        )
        return template

    def annotate_information_source(
        self, trg: str, file_path: str, checksum: str, template: dict
    ) -> dict:
        """Add from where the information was obtained."""
        template[f"{trg}/PROCESS[process]/source/type"] = "file"
        template[f"{trg}/PROCESS[process]/source/path"] = file_path
        template[f"{trg}/PROCESS[process]/source/checksum"] = checksum
        template[f"{trg}/PROCESS[process]/source/algorithm"] = (
            DEFAULT_CHECKSUM_ALGORITHM
        )
        return template

    def process_event_data_em_data(self, obj: dict, template: dict) -> dict:
        """Map Velox-specifically formatted data arrays on NeXus NXdata/NXimage/NXspectrum."""
        flat_hspy_meta = fd.FlatDict(obj["metadata"], "/")
        if "General/title" not in flat_hspy_meta:
            return template

        # flat_orig_meta = fd.FlatDict(obj["original_metadata"], "/")
        axes = obj["axes"]
        unit_combination = velox_image_spectrum_or_generic_nxdata(axes)
        if unit_combination == "":
            return template
        if self.verbose:
            print(axes)
            print(f"{unit_combination}, {np.shape(obj['data'])}")
            print(f"entry_id {self.entry_id}, event_id {self.id_mgn['event_id']}")

        prfx = f"/ENTRY[entry{self.entry_id}]/measurement/event_data_em_set/EVENT_DATA_EM[event_data_em{self.id_mgn['event_id']}]"
        # this is the place when you want to skip individually the writing of NXdata
        # return template
        axis_names = None
        if unit_combination in VELOX_WHICH_SPECTRUM:
            self.annotate_information_source(
                f"{prfx}/SPECTRUM_SET[spectrum_set1]",
                self.file_path,
                self.file_path_sha256,
                template,
            )
            trg = f"{prfx}/SPECTRUM_SET[spectrum_set1]/{VELOX_WHICH_SPECTRUM[unit_combination][0]}"
            template[f"{trg}/title"] = f"{flat_hspy_meta['General/title']}"
            template[f"{trg}/@signal"] = f"intensity"
            template[f"{trg}/intensity"] = {"compress": obj["data"], "strength": 1}
            axis_names = VELOX_WHICH_SPECTRUM[unit_combination][1]
        elif unit_combination in VELOX_WHICH_IMAGE:
            self.annotate_information_source(
                f"{prfx}/IMAGE_SET[image_set1]",
                self.file_path,
                self.file_path_sha256,
                template,
            )
            trg = (
                f"{prfx}/IMAGE_SET[image_set1]/{VELOX_WHICH_IMAGE[unit_combination][0]}"
            )
            template[f"{trg}/title"] = f"{flat_hspy_meta['General/title']}"
            template[f"{trg}/@signal"] = f"real"  # TODO::unless COMPLEX
            template[f"{trg}/real"] = {"compress": obj["data"], "strength": 1}
            axis_names = VELOX_WHICH_IMAGE[unit_combination][1]
        else:
            self.annotate_information_source(
                f"{prfx}/DATA[data1]", self.file_path, self.file_path_sha256, template
            )
            trg = f"{prfx}/DATA[data1]"
            template[f"{trg}/title"] = f"{flat_hspy_meta['General/title']}"
            template[f"{trg}/@NX_class"] = f"NXdata"
            template[f"{trg}/@signal"] = f"data"
            template[f"{trg}/data"] = {"compress": obj["data"], "strength": 1}
            axis_names = ["axis_i", "axis_j", "axis_k", "axis_l", "axis_m"][
                0 : len(unit_combination.split("_"))
            ]  # TODO mind order

        if len(axis_names) >= 1:
            # TODO arrays axis_names and dimensional_calibrations are aligned in order
            # TODO but that order is reversed wrt to AXISNAME_indices !
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
                        np.float32,
                    )
                    if unit_combination in VELOX_WHICH_SPECTRUM:
                        template[f"{trg}/AXISNAME[{axis_name}]/@long_name"] = (
                            f"Spectrum identifier"
                        )
                    elif unit_combination in VELOX_WHICH_IMAGE:
                        template[f"{trg}/AXISNAME[{axis_name}]/@long_name"] = (
                            f"Image identifier"
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

        self.process_event_data_em_metadata(obj, template)
        self.id_mgn["event_id"] += 1
        return template
