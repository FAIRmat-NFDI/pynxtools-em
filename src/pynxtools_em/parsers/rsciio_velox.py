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

import flatdict as fd
import numpy as np
from pynxtools.dataconverter.chunk import prioritized_axes_heuristic
from rsciio import emd

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
from pynxtools_em.methods.ebsd import has_hfive_magic_header
from pynxtools_em.utils.custom_logging import logger
from pynxtools_em.utils.default_config import (
    DEFAULT_COMPRESSION_LEVEL,
    DEFAULT_VERBOSITY,
    SEPARATOR,
)
from pynxtools_em.utils.get_checksum import (
    DEFAULT_CHECKSUM_ALGORITHM,
    get_sha256_of_file_content,
)
from pynxtools_em.utils.pint_custom_unit_registry import ureg
from pynxtools_em.utils.rsciio_hspy_utils import all_req_keywords_in_dict
from pynxtools_em.utils.string_conversions import string_to_number
from pynxtools_em.utils.velox_utils import velox_image_spectrum_or_generic_nxdata


class RsciioVeloxParser:
    """Read Velox EMD File Format emd."""

    def __init__(
        self, file_path: str = "", entry_id: int = 1, verbose: bool = DEFAULT_VERBOSITY
    ):
        if file_path:
            self.file_path: str = file_path
            self.entry_id: int = entry_id if entry_id > 0 else 1
            self.verbose: bool = verbose
            self.id_mgn: dict[str, int] = {
                "event_id": 1,
                "event_img": 1,
                "event_spc": 1,
                "roi": 1,
                "eds_img": 1,
            }
            self.version: dict[str, dict[str, list[str]]] = {
                "trg": {
                    "Core/MetadataDefinitionVersion": ["7.9"],
                    "Core/MetadataSchemaVersion": ["v1/2013/07"],
                },
                "src": {
                    "Core/MetadataDefinitionVersion": None,
                    "Core/MetadataSchemaVersion": None,
                },
            }
            self.obj_idx_supported: list[int] = []
            self.supported: bool = False
            self.check_if_supported()
            if not self.supported:
                logger.debug(
                    f"Parser {self.__class__.__name__} finds no content in {file_path} that it supports"
                )
        else:
            logger.warning(f"Parser {self.__class__.__name__} needs Velox EMD file")
            self.supported = False

    def check_if_supported(self):
        self.supported = False
        # TFS best practice, Velox EMD files mimetype emd and HDF5 file
        if not self.file_path.lower().endswith(".emd"):
            return
        if not has_hfive_magic_header(self.file_path):
            return
        try:
            self.objs = emd.file_reader(self.file_path)
            # TODO::what to do if the content of the file is larger than the available
            # main memory, one approach to handle this is to have the file_reader parsing
            # only the collection of the concepts without the actual instance data
            # based on this one could then plan how much memory has to be reserved
            # in the template and stream out accordingly
            reqs = ["data", "axes", "metadata", "original_metadata", "mapping"]
            for idx, obj in enumerate(self.objs):
                if not isinstance(obj, dict):
                    continue
                if not all_req_keywords_in_dict(obj, reqs):
                    continue
                original_metadata = fd.FlatDict(obj["original_metadata"], "/")
                if "Core/MetadataDefinitionVersion" in original_metadata:
                    logger.info(
                        f"Core/MetadataDefinitionVersion {original_metadata['Core/MetadataDefinitionVersion']}"
                    )
                    if (
                        original_metadata["Core/MetadataDefinitionVersion"]
                        not in self.version["trg"]["Core/MetadataDefinitionVersion"]
                    ):
                        continue
                    logger.info(
                        f"Core/MetadataSchemaVersion {original_metadata['Core/MetadataSchemaVersion']}"
                    )
                    if (
                        original_metadata["Core/MetadataSchemaVersion"]
                        not in self.version["trg"]["Core/MetadataSchemaVersion"]
                    ):
                        continue
                self.obj_idx_supported.append(idx)
                if self.verbose:
                    logger.debug(f"{idx}-th obj is supported")
            if (
                len(self.obj_idx_supported) > 0
            ):  # there is at least some supported content
                self.supported = True
        except (OSError, FileNotFoundError, ValueError):
            logger.error(f"{self.file_path} FileNotFound, IOError, or ValueError")
            return

    def parse(self, template: dict) -> dict:
        """Perform actual parsing."""
        if self.supported:
            with open(self.file_path, "rb", 0) as fp:
                self.file_path_sha256 = get_sha256_of_file_content(fp)
            logger.info(
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
                logger.debug(f"obj{idx}, dims {obj['axes']}")
        return template

    def process_event_data_em_metadata(self, obj: dict, template: dict) -> dict:
        """Map some of the TFS/FEI/Velox-specific metadata concepts on NeXus concepts."""
        identifier: list[int] = [self.entry_id, self.id_mgn["event_id"], 1]
        original_metadata = fd.FlatDict(obj["original_metadata"], "/")
        for keyword, value in original_metadata.items():
            original_metadata[keyword] = string_to_number(value)
        if self.verbose:
            for keyword, value in original_metadata.items():
                logger.info(f"{keyword}{SEPARATOR}{type(value)}{SEPARATOR}{value}")

        if (len(identifier) != 3) or (not all(isinstance(x, int) for x in identifier)):
            logger.warning(f"Argument identifier {identifier} needs three int values!")
        trg = f"/ENTRY[entry{identifier[0]}]/measurement/eventID[event{identifier[1]}]/instrument/ebeam_column"
        # using an own function like add_dynamic_lens_metadata may be needed
        # if specific NeXus group have some extra formatting
        lens_idx: int = 1
        for lens_name in [
            "C1",
            "C2",
            "C3",
            "Diffraction",
            "Gun",
            "Intermediate",
            "MiniCondenser",
            "Lorentz",
            "Objective",
            "Projector1",
            "Projector2",
        ]:
            toggle: bool = False
            if f"Optics/{lens_name}LensIntensity" in original_metadata:
                template[f"{trg}/lensID[lens{lens_idx}]/power_setting"] = (
                    string_to_number(
                        original_metadata[f"Optics/{lens_name}LensIntensity"]
                    )
                )
                if lens_name != "Gun":
                    template[f"{trg}/lensID[lens{lens_idx}]/power_setting/@units"] = "%"
                toggle = True
            if f"Optics/{lens_name}LensMode" in original_metadata:
                template[f"{trg}/lensID[lens{lens_idx}]/mode"] = string_to_number(
                    original_metadata[f"Optics/{lens_name}LensMode"]
                )
                toggle = True
            if toggle:
                template[
                    f"/ENTRY[entry{identifier[0]}]/measurement/instrument/ebeam_column/lensID[lens{lens_idx}]/name"
                ] = f"{lens_name}"
                lens_idx += 1

        aperture_idx: int = 1
        # condenser lenses
        for lens_name in [
            "C1",
            "C2",
            "C3",
        ]:
            if f"Optics/{lens_name} Aperture" in original_metadata:
                qnt = ureg.Quantity(
                    string_to_number(original_metadata[f"Optics/{lens_name} Aperture"]),
                    ureg.micrometer,
                )
                template[f"{trg}/apertureID[aperture{aperture_idx}]/setting"] = (
                    qnt.magnitude
                )
                template[f"{trg}/apertureID[aperture{aperture_idx}]/setting/@units"] = (
                    qnt.units
                )
                template[
                    f"/ENTRY[entry{identifier[0]}]/measurement/instrument/ebeam_column/apertureID[aperture{aperture_idx}]/name"
                ] = f"{lens_name}"
                aperture_idx += 1

        # other/special lenses
        for lens_name in ["OBJ", "SA"]:
            if f"Optics/{lens_name} Aperture" in original_metadata:
                template[f"{trg}/apertureID[aperture{aperture_idx}]/status"] = (
                    original_metadata[f"Optics/{lens_name} Aperture"]
                )
                template[
                    f"/ENTRY[entry{identifier[0]}]/measurement/instrument/ebeam_column/apertureID[aperture{aperture_idx}]/name"
                ] = f"{lens_name}"

        for cfg in [
            VELOX_STATIC_ENTRY_NX,
            VELOX_STATIC_EBEAM_NX,
            VELOX_DYNAMIC_SCAN_NX,
            VELOX_DYNAMIC_VARIOUS_NX,
            VELOX_DYNAMIC_OPTICS_NX,
        ]:
            add_specific_metadata_pint(cfg, original_metadata, identifier, template)

        add_specific_metadata_pint(
            VELOX_STATIC_FABRICATION_NX, original_metadata, identifier, template
        )
        add_specific_metadata_pint(
            VELOX_DYNAMIC_STAGE_NX, original_metadata, identifier, template
        )
        add_specific_metadata_pint(
            VELOX_DYNAMIC_EBEAM_NX, original_metadata, identifier, template
        )
        return template

    def annotate_information_source(
        self, src: str, trg: str, file_path: str, checksum: str, template: dict
    ) -> dict:
        """Add from where the information was obtained."""
        parent: str = f"{trg}/PROCESS[process]/input"
        template[f"{parent}/file_name"] = file_path
        template[f"{parent}/checksum"] = checksum
        template[f"{parent}/algorithm"] = DEFAULT_CHECKSUM_ALGORITHM
        if src != "":
            template[f"{parent}/context"] = f"{src}"
        return template

    def process_event_data_em_data(self, obj: dict, template: dict) -> dict:
        """Map Velox-specifically formatted data arrays on NeXus NXdata/NXimage/NXspectrum."""
        metadata = fd.FlatDict(obj["metadata"], "/")
        if "General/title" not in metadata:
            logger.warning(f"Missing General/title metadata keyword")
            return template

        axes = obj["axes"]
        unit_combination: str = velox_image_spectrum_or_generic_nxdata(axes)
        if unit_combination == "":
            return template
        if self.verbose:
            logger.info(axes)
            logger.info(f"{unit_combination}, {np.shape(obj['data'])}")
            logger.info(f"entry_id {self.entry_id}, event_id {self.id_mgn['event_id']}")

        prfx: str = f"/ENTRY[entry{self.entry_id}]/measurement/eventID[event{self.id_mgn['event_id']}]"
        # this is the place when you want to skip individually the writing of NXdata
        # return template
        if unit_combination in VELOX_WHICH_SPECTRUM:
            # self.annotate_information_source(
            #     "",
            #     f"{prfx}/spectrumID[spectrum1]",
            #     self.file_path,
            #     self.file_path_sha256,
            #     template,
            # )
            trg = f"{prfx}/spectrumID[spectrum1]/{VELOX_WHICH_SPECTRUM[unit_combination][0]}"
            template[f"{trg}/title"] = f"{metadata['General/title']}"
            template[f"{trg}/@signal"] = f"intensity"
            template[f"{trg}/intensity"] = {
                "compress": obj["data"],
                "chunks": prioritized_axes_heuristic(
                    obj["data"], np.arange(obj["data"].ndim)
                ),
                "strength": DEFAULT_COMPRESSION_LEVEL,
            }
            template[f"{trg}/intensity/@long_name"] = f"Counts"
            axis_names: str | list[str] = VELOX_WHICH_SPECTRUM[unit_combination][1]
        elif unit_combination in VELOX_WHICH_IMAGE:
            # self.annotate_information_source(
            #     "",
            #     f"{prfx}/imageID[image1]",
            #     self.file_path,
            #     self.file_path_sha256,
            #     template,
            # )
            trg = f"{prfx}/imageID[image1]/{VELOX_WHICH_IMAGE[unit_combination][0]}"
            template[f"{trg}/title"] = f"{metadata['General/title']}"
            template[f"{trg}/@signal"] = f"real"  # TODO::unless COMPLEX
            template[f"{trg}/real"] = {
                "compress": obj["data"],
                "chunks": prioritized_axes_heuristic(
                    obj["data"], np.arange(obj["data"].ndim)
                ),
                "strength": DEFAULT_COMPRESSION_LEVEL,
            }
            template[f"{trg}/real/@long_name"] = f"Real part of the image intensity"
            axis_names = VELOX_WHICH_IMAGE[unit_combination][1]
        else:
            # self.annotate_information_source(
            #     "",
            #     f"{prfx}/DATA[data1]",
            #     self.file_path,
            #     self.file_path_sha256,
            #     template,
            # )
            trg = f"{prfx}/DATA[data1]"
            template[f"{trg}/title"] = f"{metadata['General/title']}"
            template[f"{trg}/@signal"] = f"data"
            template[f"{trg}/data"] = {
                "compress": obj["data"],
                "chunks": prioritized_axes_heuristic(
                    obj["data"], np.arange(obj["data"].ndim)
                ),
                "strength": DEFAULT_COMPRESSION_LEVEL,
            }
            axis_names = ["axis_i", "axis_j", "axis_k", "axis_m", "axis_n"][
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
                    numpy_array = np.asarray(
                        offset
                        + np.linspace(0, count - 1, num=count, endpoint=True) * step,
                        np.float32,
                    )
                    template[f"{trg}/AXISNAME[{axis_name}]"] = {
                        "compress": numpy_array,
                        "chunks": prioritized_axes_heuristic(
                            numpy_array, np.arange(numpy_array.ndim)
                        ),
                        "strength": DEFAULT_COMPRESSION_LEVEL,
                    }
                    if unit_combination in VELOX_WHICH_SPECTRUM:
                        long_name = "Identifier spectrum"
                    elif unit_combination in VELOX_WHICH_IMAGE:
                        long_name = "Identifier image"
                    else:
                        long_name = axis_name
                        # unitless | dimensionless i.e. no unit in long_name
                    template[f"{trg}/AXISNAME[{axis_name}]/@long_name"] = long_name
                else:
                    numpy_array = np.asarray(
                        offset
                        + np.linspace(0, count - 1, num=count, endpoint=True) * step,
                        dtype=np.float32,
                    )
                    template[f"{trg}/AXISNAME[{axis_name}]"] = {
                        "compress": numpy_array,
                        "chunks": prioritized_axes_heuristic(
                            numpy_array, np.arange(numpy_array.ndim)
                        ),
                        "strength": DEFAULT_COMPRESSION_LEVEL,
                    }
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
                            f"Coordinate along {axis_name.replace('axis_', '')}-axis ({ureg.Unit(units)})"
                        )

        self.process_event_data_em_metadata(obj, template)
        self.id_mgn["event_id"] += 1
        return template
