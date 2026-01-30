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

import numpy as np
from rsciio import mrc

from pynxtools_em.utils.custom_logging import logger
from pynxtools_em.utils.default_config import DEFAULT_VERBOSITY, SEPARATOR
from pynxtools_em.utils.get_checksum import get_sha256_of_file_content
from pynxtools_em.utils.pint_custom_unit_registry import ureg


class RsciioMrcParser:
    """Read MRC file format."""

    def __init__(
        self,
        file_paths: list[str],
        entry_id: int = 1,
        verbose: bool = DEFAULT_VERBOSITY,
    ):
        # many individual combinations of detector systems and acquisition, analysis
        # software folks use for electron tomography, search online and just for mrc
        # gave three datasets each using differently formatted metadata sidecar files
        # all these sidecar files are txt though
        mrc_txt = ["", ""]
        if (
            len(file_paths) == 2
            and file_paths[0][0 : file_paths[0].rfind(".")]
            == file_paths[1][0 : file_paths[0].rfind(".")]
        ):
            for entry in file_paths:
                if entry.lower().endswith(".mrc"):
                    mrc_txt[0] = entry
                elif entry.lower().endswith(".mrc.mdoc"):
                    mrc_txt[1] = entry
            if all(value != "" for value in mrc_txt):
                self.file_path = mrc_txt[0]
                self.entry_id = entry_id if entry_id > 0 else 1
                self.verbose = verbose
                self.id_mgn: dict[str, int] = {"event_id": 1}
                self.txt_file_path = mrc_txt[1]
                # self.flat_dict_meta = fd.FlatDict({}, "/")
                self.series_meta_data: dict[str, Any] = {}
                self.image_meta_data: dict[int, dict[str, Any]] = {}
                self.version: dict = {}
                self.supported = 0
                self.check_if_mrc_serial_em_electron_tomography()
            else:
                logger.warning(
                    f"Parser {self.__class__.__name__} needs MRC and TXT file !"
                )
                self.supported = False
        else:
            logger.debug(
                f"Parser {self.__class__.__name__} finds no content in {file_paths} that it supports"
            )
            self.supported = False

    def check_if_mrc_serial_em_electron_tomography(self):
        """Check if MRC file and sidecar TXT file exists, have payload, and are consistent.
        Consistency constraints:
        - Each tilt image in the MRC file should have exactly one metadata entry in TXT
        - Each metadata entry should have values for all the relevant same metadata concepts
        - Identifier for the tilt images should be the same within the MRC and TXT, 0 based.
        """
        supported = 0  # voting based
        try:
            self.objs = mrc.file_reader(self.file_path)
            # TODO::out-of-memory
            if len(self.objs) == 1:
                supported += 1
            else:
                # more than one tilt series which is currently not supported"
                self.supported = False
        except (OSError, FileNotFoundError):
            logger.warning(f"{self.file_path} either FileNotFound or IOError !")
            self.supported = False
            return

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
                    return

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
                    return

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
                    (r"PixelSpacing", r"(\d+(?:\.\d+)?)", np.float64, ureg.meter),
                    (r"SpotSize", r"(\d+)", np.uint32, ureg.dimensionless),
                    (r"ProbeMode", r"(\d+)", np.uint32, ureg.dimensionless),
                    (r"Defocus", r"([+-]?\d+(?:\.\d+)?)", np.float64, ureg.meter),
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
                                match.group(1), unit
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
                                    (match.group(1), match.group(2)), dtype=data_type
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
                        stage_position[0:2] = (match.group(1), match.group(2))
                        break
                key, rgx = (r"StageZ", r"([+-]?\d+(?:\.\d+)?)")
                for jdx in range(s_e["start"], s_e["end"]):
                    match = re.search(key + r"\s*=\s*" + rgx, txt_stripped[jdx])
                    if match:
                        stage_position[2] = match.group(1)
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
                    return

        if supported == 1:
            self.supported = True
        return

    def parse(self, template: dict) -> dict:
        """Perform actual parsing."""
        if self.supported:
            with open(self.file_path, "rb", 0) as fp:
                self.file_path_sha256 = get_sha256_of_file_content(fp)
            logger.info(
                f"Parsing {self.file_path} MRC with SHA256 {self.file_path_sha256} ..."
            )
            self.parse_content(template)
        return template

    def parse_content(self, template: dict) -> dict:
        """Translate tech partner concepts to NeXus concepts."""
        return template
