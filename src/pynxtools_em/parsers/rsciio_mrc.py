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
"""Parser for reading content from MRC via rosettasciio."""

import re
from typing import Any
from xml.parsers.expat import ExpatError

import numpy as np
import xmltodict
from rsciio import mrc

from pynxtools_em.utils.custom_logging import logger
from pynxtools_em.utils.default_config import DEFAULT_VERBOSITY, SEPARATOR
from pynxtools_em.utils.get_checksum import get_sha256_of_file_content
from pynxtools_em.utils.pint_custom_unit_registry import ureg
from pynxtools_em.utils.rsciio_mrc_utils import get_dimension_analysis_keyword
from pynxtools_em.utils.string_conversions import string_to_number


class RsciioMrcParser:
    """Read MRC file format."""

    def __init__(
        self,
        file_paths: list[str],
        entry_id: int = 1,
        verbose: bool = DEFAULT_VERBOSITY,
    ):
        # many individual combinations of detector systems and acquisition, analysis
        # software folks use for electron tomography, searched online easily found several
        # datasets, each using differently formatted metadata sidecar files if at all
        # if present, sidecar files were txt though
        self.supported = False
        mrc_txt = ["", ""]
        if len(file_paths) == 1:
            if file_paths[0].lower().endswith(".mrc"):
                mrc_txt[0] = file_paths[0]
        elif len(file_paths) == 2:
            if (
                file_paths[0][0 : file_paths[0].rfind(".")]
                == file_paths[1][0 : file_paths[0].rfind(".")]
            ):
                for entry in file_paths:
                    if entry.lower().endswith(".mrc"):
                        mrc_txt[0] = entry
                    elif entry.lower().endswith((".mrc.mdoc", ".rawtlt", ".xml")):
                        mrc_txt[1] = entry
        # exactly one mrc file is required, let aside sidecar file and its formatting
        if mrc_txt[0] != "":
            self.file_path = mrc_txt[0]
            self.entry_id = entry_id if entry_id > 0 else 1
            self.verbose = verbose
            self.id_mgn: dict[str, int] = {"event_id": 1}
            # self.flat_dict_meta = fd.FlatDict({}, "/")
            self.series_meta_data: dict[str, Any] = {}
            self.image_meta_data: dict[int, dict[str, Any]] = {}
            self.config: dict[str, Any] = {}
            self.version: dict = {}
            try:
                self.objs = mrc.file_reader(self.file_path)  # , lazy=True)
                if len(self.objs) != 1:
                    logger.warning(
                        f"{self.file_path} more than one obj currently not supported for MRC"
                    )
                    return
            except (OSError, FileNotFoundError):
                logger.warning(f"{self.file_path} either FileNotFound or IOError !")
                return
        if mrc_txt[1] != "":
            self.txt_file_path = mrc_txt[1]
            if mrc_txt[1].endswith(".mrc.mdoc"):
                if self.check_if_mrc_serial_em_electron_tomography():
                    self.config["mode"] = "et_mrc_mdoc"
            elif mrc_txt[1].endswith(".rawtlt"):
                if self.check_if_mrc_other_electron_tomography():
                    self.config["mode"] = "et_mrc_rawtlt"
            elif mrc_txt[1].endswith(".xml"):
                if self.check_if_mrc_fei():
                    self.config["mode"] = "em_mrc_xml"
            else:
                self.config["mode"] = "em_mrc_unsupported"
        else:  # no sidecar
            self.config["mode"] = "em_mrc_only"
            self.supported = True
        if "mode" not in self.config:
            logger.debug(
                f"Parser {self.__class__.__name__} finds no content in {file_paths} that it supports"
            )

    def check_if_mrc_serial_em_electron_tomography(self) -> bool:
        """Check if MRC file and sidecar TXT file exists, have payload, and are consistent.
        Consistency constraints:
        - Each tilt image in the MRC file should have exactly one metadata entry in TXT
        - Each metadata entry should have values for all the relevant same metadata concepts
        - Identifier for the tilt images should be the same within the MRC and TXT, 0 based.
        """
        with open(self.txt_file_path, encoding="utf8") as fp:
            txt = fp.read()
            txt = txt.replace("\r\n", "\n")  # windows to unix EOL conversion
            txt_stripped = [line for line in txt.split("\n") if line.strip() != ""]
            # txt = txt.replace(",", ".")  # use decimal dots instead of comma
            del txt

            # scalar quantities on specific lines
            for key, regex, data_type, src_unit, trg_unit, line_idx in [
                (
                    r"PixelSpacing",
                    r"(\d+(?:\.\d+)?)",
                    np.float64,
                    ureg.angstrom,
                    ureg.meter,
                    0,
                ),  # ???
                (r"Voltage", r"(\d+)", np.float64, ureg.kilovolt, ureg.volt, 1),  # ???
            ]:
                match = re.search(key + r"\s*=\s*" + regex, txt_stripped[line_idx])
                if match:
                    self.series_meta_data[key] = ureg.Quantity(
                        data_type(match.group(1)), src_unit
                    ).to(trg_unit)
                else:
                    logger.warning(f"{self.file_path} series_meta_data {key} not found")
                    return False

            # scalar settings and strings on specific lines
            for key, regex, data_type, line_idx in [
                (r"Version", r"(SerialEM.*)", str, 2),
                (r"ImageFile", r"(.*)", str, 3),
                (
                    r"DataMode",
                    r"(\d+)",
                    np.uint32,
                    5,
                ),  # distinguish setting and quantities ???
            ]:
                match = re.search(key + r"\s*=\s*" + regex, txt_stripped[line_idx])
                if match:
                    if isinstance(data_type, str):
                        self.series_meta_data[key] = match.group(1)
                    else:
                        self.series_meta_data[key] = data_type(match.group(1))
                else:
                    logger.warning(f"{self.file_path} series_meta_data {key} not found")
                    return False

            # array quantities on specific lines
            for key, regex, data_type, line_idx in [
                (r"ImageSize", r"(\d+)\s+(\d+)", np.uint32, 4),
            ]:
                match = re.search(r"\s*=\s*" + regex, txt_stripped[line_idx])
                if match:
                    self.series_meta_data[key] = np.asarray(
                        (match.group(1), match.group(2)), dtype=data_type
                    )
                else:
                    logger.warning(f"{self.file_path} series_meta_data {key} not found")

            if self.verbose:
                for key, value in self.series_meta_data.items():
                    logger.debug(f"series_meta_data{SEPARATOR}{key}{SEPARATOR}{value}")

            # process metadata for the individual metadata for each tilt image
            line_idx = 5
            metadata_block_start_end: dict[int, dict[str, int]] = {}
            block_id = 0
            while line_idx < len(txt_stripped):
                match = re.search(r"\[ZValue\s*=\s*(\d+)\]", txt_stripped[line_idx])
                if match:
                    if block_id == int(match.group(1)):
                        metadata_block_start_end[block_id] = {"start": line_idx}
                        if block_id - 1 >= 0:
                            metadata_block_start_end[block_id - 1]["end"] = line_idx
                        block_id += 1
                line_idx += 1
            if block_id - 1 >= 0:
                metadata_block_start_end[block_id - 1]["end"] = len(txt_stripped)

            for block_id, s_e in metadata_block_start_end.items():
                self.image_meta_data[block_id] = {}
                scalars = [
                    (r"TiltAngle", r"([+-]?\d+(?:\.\d+)?)", np.float64, ureg.degrees),
                    (
                        r"Magnification",
                        r"(\d+(?:\.\d+)?)",
                        np.float64,
                        ureg.dimensionless,
                    ),
                    # Intensity,
                    # ExposureDose,
                    (r"PixelSpacing", r"(\d+(?:\.\d+)?)", np.float64, ureg.angstrom),
                    (r"SpotSize", r"(\d+)", np.uint32, ureg.dimensionless),
                    (r"ProbeMode", r"(\d+)", np.uint32, ureg.dimensionless),
                    (r"Defocus", r"([+-]?\d+(?:\.\d+)?)", np.float64, ureg.nanometer),
                    (
                        r"RotationAngle",
                        r"([+-]?\d+(?:\.\d+)?)",
                        np.float64,
                        ureg.degrees,
                    ),
                    (r"ExposureTime", r"([+-]?\d+(?:\.\d+)?)", np.float64, ureg.second),
                    (r"Binning", r"(\d+)", np.uint32, ureg.dimensionless),
                    (r"CameraIndex", r"(\d+)", np.uint32, ureg.dimensionless),
                    # "DividedBy2",
                    (r"MagIndex", r"(\d+)", np.uint32, ureg.dimensionless),
                    (r"LowDoseConSet", r"[+-]?(\d+)", np.float64, ureg.dimensionless),
                    (
                        r"CountsPerElectron",
                        r"([+-]?\d+(?:\.\d+)?)",
                        np.float64,
                        ureg.dimensionless,
                    ),  # "1 / angstrom**2"),
                    # TimeStamp,
                ]
                for key, rgx, data_type, unit in scalars:
                    for jdx in range(s_e["start"], s_e["end"]):
                        match = re.search(key + r"\s*=\s*" + rgx, txt_stripped[jdx])
                        if match:
                            # print(f"{jdx}, {match}")
                            self.image_meta_data[block_id][f"{key}"] = ureg.Quantity(
                                string_to_number(match.group(1)), unit
                            )
                            # if f"{unit}" == "degree":  # TODO broken
                            #     md[blk_id][f"{key}"].to(ureg.radians)
                            break

                tuples = [
                    (
                        r"ImageShift",
                        r"([+-]?\d+(?:\.\d+)?)\s+([+-]?\d+(?:\.\d+)?)",
                        np.float64,
                        ureg.angstrom,
                        ureg.meter,
                    ),
                ]
                for key, rgx, data_type, src_unit, trg_unit in tuples:
                    for jdx in range(s_e["start"], s_e["end"]):
                        match = re.search(key + r"\s*=\s*" + rgx, txt_stripped[jdx])
                        if match:
                            self.image_meta_data[block_id][f"{key}"] = ureg.Quantity(
                                np.asarray(
                                    (
                                        string_to_number(match.group(1)),
                                        string_to_number(match.group(2)),
                                    ),
                                    dtype=data_type,
                                ),
                                src_unit,
                            ).to(trg_unit)
                            break
                # special case StagePosition
                stage_position = np.zeros((3,), dtype=np.float64)
                key, rgx = (
                    r"StagePosition",
                    r"([+-]?\d+(?:\.\d+)?)\s+([+-]?\d+(?:\.\d+)?)",
                )
                for jdx in range(s_e["start"], s_e["end"]):
                    match = re.search(key + r"\s*=\s*" + rgx, txt_stripped[jdx])
                    if match:
                        stage_position[0] = string_to_number(match.group(1))
                        stage_position[1] = string_to_number(match.group(2))
                        break
                key, rgx = (r"StageZ", r"([+-]?\d+(?:\.\d+)?)")
                for jdx in range(s_e["start"], s_e["end"]):
                    match = re.search(key + r"\s*=\s*" + rgx, txt_stripped[jdx])
                    if match:
                        stage_position[2] = string_to_number(match.group(1))
                        break
                # are both stage values XY and Z in nanometer ???
                self.image_meta_data[block_id]["StagePosition"] = ureg.Quantity(
                    stage_position, ureg.nanometer
                ).to(ureg.meter)

            # r"ChannelName", r"(.*)"),
            # r"DateTime", r"(.*)"),
            # MinMaxMean = 431 23324 1984.64
            # StagePosition = -167.145 -154.199
            # ImageShift = -0.163032 0.295584
            # UncroppedSize = -1024 -1024
        if self.verbose:
            for block_id in self.image_meta_data.keys():
                for key, value in self.image_meta_data[block_id].items():
                    logger.debug(
                        f"image_meta_data{SEPARATOR}{block_id}{SEPARATOR}{key}{SEPARATOR}{value}"
                    )

        # evaluate if required ones are there
        for block_id in self.image_meta_data.keys():
            for required in [
                "TiltAngle",
                "Magnification",
                "PixelSpacing",
                "SpotSize",
                "ProbeMode",
                "Defocus",
                "RotationAngle",
                "ExposureTime",
            ]:
                if required not in self.image_meta_data[block_id]:
                    logger.warning(
                        f"{self.file_path} image {block_id} {key} required but not found"
                    )
                    return False

        self.supported = True
        return True

    def check_if_mrc_other_electron_tomography(self) -> bool:
        """TODO"""
        tilts = []
        with open(self.txt_file_path, "rb") as fp:
            for line in fp.readlines():
                payload = line.decode("utf-8").strip()
                if payload != "":
                    token_list = payload.split()
                    if len(token_list) > 1:
                        for token in token_list:
                            if token != "":
                                try:
                                    tilts.append(float(token))
                                except ValueError:
                                    logger.warning(
                                        f"{self.file_path} unable to convert rawtlt"
                                    )
                                    return False
                            else:
                                logger.warning(f"{self.file_path} empty rawtlt")
                                return False
                    else:
                        try:
                            tilts.append(float(token))
                        except ValueError:
                            logger.warning(f"{self.file_path} unable to convert rawtlt")
                            return False
                else:
                    logger.warning(f"{self.file_path} empty payload")
                    return False
            # original order matters and is here retained
        # tilts = ureg.Quantity(np.asarray(tilts, np.float32), ureg.degree)
        for image_id, tilt_angle in enumerate(tilts):
            self.image_meta_data[image_id]["TiltAngle"] = ureg.Quantity(
                np.float32(tilt_angle), ureg.degree
            )
            if self.verbose:
                logger.info(
                    f"{image_id}{SEPARATOR}{self.image_meta_data[image_id]['TiltAngle']}"
                )

        self.supported = True
        return True

    def check_if_mrc_fei(self) -> bool:
        """TODO"""
        with open(self.txt_file_path, encoding="utf-8") as xml_fp:
            try:
                xml = xmltodict.parse(xml_fp.read())
            except ExpatError:
                logger.warning(f"{self.file_path} unable to parse XML content")
                return False

            # prototypic parsing of FEI, structure, needs to be made more robust
            try:
                info = xml["Acquisition"]["Info"]
            except (KeyError, TypeError):
                info = None
            try:
                images = xml["Acquisition"]["Images"]["Image"]
            except (KeyError, TypeError):
                images = None
            if info is not None and images is not None:
                hotfix_valid_keys = 0
                for image_id, image_dict in enumerate(
                    xml["Acquisition"]["Images"]["Image"]
                ):
                    if image_id == int(image_dict["ImageID"]):
                        self.image_meta_data[image_id]["TimeStamp"] = image_dict[
                            "DateTimeWithTimeZone"
                        ]
                        hotfix_valid_keys += 1
                logger.info(
                    f"{self.file_path} sidecar file yields {hotfix_valid_keys} timestamps"
                )
            else:
                logger.warning(
                    f"{self.file_path} XML sidecar file seems not to be an FEI one"
                )
                return False

        self.supported = True
        return True

    def parse(self, template: dict) -> dict:
        """Perform actual parsing."""
        if self.supported:
            with open(self.file_path, "rb", 0) as fp:
                self.file_path_sha256 = get_sha256_of_file_content(fp)
            logger.info(
                f"Parsing {self.file_path} MRC with SHA256 {self.file_path_sha256} ..."
            )
            if self.config["mode"] == "et_mrc_mdoc":
                self.process_data_mode_et_mrc_mdoc(template)
            elif self.config["mode"] == "et_mrc_rawtlt":
                self.process_data_mode_et_mrc_rawtlt(template)
            elif self.config["mode"] == "em_mrc_fei":
                self.process_data_mode_em_mrc_fei(template)
            elif self.config["mode"] == "em_mrc_only":
                self.process_data_mode_et_mrc_only(template)
        return template

    def process_data_mode_et_mrc_mdoc(self, template: dict) -> dict:
        """Translate tech partner concepts to NeXus concepts."""
        for obj_id, obj in enumerate(self.objs):
            if get_dimension_analysis_keyword(obj["axes"]) not in [
                "dimensionless;meter;meter"
            ]:
                logger.warning(f"{self.file_path} ignoring obj_id {obj_id}")
                continue
            number_of_images = np.shape(obj["data"])[0]
            trg = f"/ENTRY[entry{self.entry_id}]/measurement/eventID[event1]/imageID[image{obj_id + 1}]/stack_2d"
            template[f"{trg}/title"] = f"Electron tomography tilt series"
            template[f"{trg}/intensity"] = {"compress": obj["data"], "strength": 1}
            template[f"{trg}/intensity/@long_name"] = f"Counts"

            axis_names = ["indices_image", "axis_j", "axis_i"]
            template[f"{trg}/@signal"] = f"intensity"
            template[f"{trg}/@axes"] = axis_names
            for idx, axis_name in enumerate(axis_names[1:]):
                axis_idx = len(axis_names) - 1 - idx
                template[f"{trg}/@AXISNAME_indices[{axis_name}_indices]"] = np.uint32(
                    len(axis_names) - 1 - idx
                )
                offset = obj["axes"][axis_idx]["offset"]
                step = obj["axes"][axis_idx]["scale"]
                units = obj["axes"][axis_idx]["units"]
                count = obj["axes"][axis_idx]["size"]
                template[f"{trg}/AXISNAME[{axis_name}]"] = {
                    "compress": np.asarray(
                        offset
                        + np.linspace(0, count - 1, num=count, endpoint=True) * step,
                        np.float64,
                    ),
                    "strength": 1,
                }
                template[f"{trg}/AXISNAME[{axis_name}]/@long_name"] = (
                    f"Coordinate along {axis_name.replace('axis_', '')}-axis ({ureg.Unit(units)})"
                )
                template[f"{trg}/AXISNAME[{axis_name}]/@units"] = f"{ureg.Unit(units)}"
            # indices_image
            for idx, axis_name in enumerate(axis_names[0:1]):
                template[f"{trg}/@AXISNAME_indices[{axis_name}_indices]"] = np.uint32(
                    len(axis_names) - 1 - idx
                )
                count = number_of_images
                template[f"{trg}/AXISNAME[{axis_name}]"] = {
                    "compress": np.asarray(
                        np.linspace(0, count - 1, num=count, endpoint=True), np.uint32
                    ),
                    "strength": 1,
                }
                template[f"{trg}/AXISNAME[{axis_name}]/@long_name"] = f"Image ID"

            trg = f"/ENTRY[entry{self.entry_id}]/measurement/eventID[event1]/instrument"
            for key, n_columns, path in [
                ("TiltAngle", 1, f"{trg}/stageID[stage]/tilt1"),
                ("Magnification", 1, f"{trg}/optics/magnification"),
                ("Defocus", 1, f"{trg}/optics/defocus"),
                ("RotationAngle", 1, f"{trg}/optics/rotation"),
                ("ExposureTime", 1, f"{trg}/ebeam_column/scan_controller/dwell_time"),
                ("ImageShift", 2, f"{trg}/optics/image_shift"),
                ("StagePosition", 3, f"{trg}/stageID[stage]/position"),
            ]:
                if key in self.image_meta_data[0]:
                    # hot-fix better map all incoming metadata always to numpy types except for string
                    if n_columns <= 1:
                        data_type = np.dtype(
                            type(self.image_meta_data[0][key].magnitude)
                        )
                        numpy_array = np.zeros((number_of_images,), dtype=data_type)
                        for image_id in range(0, number_of_images):
                            numpy_array[image_id] = self.image_meta_data[image_id][
                                key
                            ].magnitude
                    else:
                        data_type = self.image_meta_data[0][key].magnitude.dtype
                        numpy_array = np.zeros(
                            (number_of_images, n_columns), dtype=data_type
                        )
                        for image_id in range(0, number_of_images):
                            numpy_array[image_id, :] = self.image_meta_data[image_id][
                                key
                            ].magnitude
                template[f"{path}"] = {"compress": numpy_array, "strength": 1}
                if f"{self.image_meta_data[0][key].units}" not in ("", "dimensionless"):
                    template[f"{path}/@units"] = f"{self.image_meta_data[0][key].units}"
                del numpy_array

            # alternative A from the rawtlt file
            # template[f"{trg}/tilt_angle"] = tilts.magnitude
            # template[f"{trg}/tilt_angle/@long_name"] = f"Tilt angle ({tilts.units})"
            # template[f"{trg}/tilt_angle/@units"] = f"{tilts.units}"
            # alternative B from the fei_header
            # for tilt_idx, tilt_axis in enumerate("a"):  # , "b"):
            #     count = obj.axes_manager[0].size
            #     template[f"{trg}/tilt_angle"] = {"compress": obj.original_metadata["fei_header"][f"{tilt_axis}_tilt"][0:count], "strength": 1}
            #     template[f"{trg}/tilt_angle/@long_name"] = f"Tilt angle ({tilts.units})"
            #     template[f"{trg}/tilt_angle/@units"] = f"{tilts.units}"
        return template

    def process_data_mode_et_mrc_rawtlt(self, template: dict) -> dict:
        for obj_id, obj in enumerate(self.objs):
            if get_dimension_analysis_keyword(obj["axes"]) not in [
                "dimensionless;meter;meter"
            ]:
                logger.warning(f"{self.file_path} ignoring obj_id {obj_id}")
                continue
            number_of_images = np.shape(obj["data"])[0]
            trg = f"/ENTRY[entry{self.entry_id}]/measurement/eventID[event1]/imageID[image{obj_id + 1}]/stack_2d"
            template[f"{trg}/title"] = f"Electron tomography tilt series"
            template[f"{trg}/intensity"] = {"compress": obj["data"], "strength": 1}
            template[f"{trg}/intensity/@long_name"] = f"Counts"

            axis_names = ["indices_image", "axis_j", "axis_i"]
            template[f"{trg}/@signal"] = f"intensity"
            template[f"{trg}/@axes"] = axis_names
            for idx, axis_name in enumerate(axis_names[1:]):
                axis_idx = len(axis_names) - 1 - idx
                template[f"{trg}/@AXISNAME_indices[{axis_name}_indices]"] = np.uint32(
                    len(axis_names) - 1 - idx
                )
                offset = obj["axes"][axis_idx]["offset"]
                step = obj["axes"][axis_idx]["scale"]
                units = obj["axes"][axis_idx]["units"]
                count = obj["axes"][axis_idx]["size"]
                template[f"{trg}/AXISNAME[{axis_name}]"] = {
                    "compress": np.asarray(
                        offset
                        + np.linspace(0, count - 1, num=count, endpoint=True) * step,
                        np.float64,
                    ),
                    "strength": 1,
                }
                template[f"{trg}/AXISNAME[{axis_name}]/@long_name"] = (
                    f"Coordinate along {axis_name.replace('axis_', '')}-axis ({ureg.Unit(units)})"
                )
                template[f"{trg}/AXISNAME[{axis_name}]/@units"] = f"{ureg.Unit(units)}"
            # indices_image
            for idx, axis_name in enumerate(axis_names[0:1]):
                template[f"{trg}/@AXISNAME_indices[{axis_name}_indices]"] = np.uint32(
                    len(axis_names) - 1 - idx
                )
                count = number_of_images
                template[f"{trg}/AXISNAME[{axis_name}]"] = {
                    "compress": np.asarray(
                        np.linspace(0, count - 1, num=count, endpoint=True), np.uint32
                    ),
                    "strength": 1,
                }
                template[f"{trg}/AXISNAME[{axis_name}]/@long_name"] = f"Image ID"

            trg = f"/ENTRY[entry{self.entry_id}]/measurement/eventID[event1]/instrument"
            for key, n_columns, path in [
                ("TiltAngle", 1, f"{trg}/stageID[stage]/tilt1"),
            ]:
                if key in self.image_meta_data[0]:
                    # hot-fix better map all incoming metadata always to numpy types except for string
                    if n_columns <= 1:
                        data_type = np.dtype(
                            type(self.image_meta_data[0][key].magnitude)
                        )
                        numpy_array = np.zeros((number_of_images,), dtype=data_type)
                        for image_id in range(0, number_of_images):
                            numpy_array[image_id] = self.image_meta_data[image_id][
                                key
                            ].magnitude
                    else:
                        data_type = self.image_meta_data[0][key].magnitude.dtype
                        numpy_array = np.zeros(
                            (number_of_images, n_columns), dtype=data_type
                        )
                        for image_id in range(0, number_of_images):
                            numpy_array[image_id, :] = self.image_meta_data[image_id][
                                key
                            ].magnitude
                template[f"{path}"] = {"compress": numpy_array, "strength": 1}
                if f"{self.image_meta_data[0][key].units}" not in ("", "dimensionless"):
                    template[f"{path}/@units"] = f"{self.image_meta_data[0][key].units}"
                del numpy_array

        return template

    def process_data_mode_em_mrc_fei(self, template: dict) -> dict:
        """TODO"""
        return template

    def process_data_mode_em_mrc_only(self, template: dict) -> dict:
        """TODO"""
        return template

    # maybe process_data_mode_{em_mrc_fei,em_mrc_other} can be combined
