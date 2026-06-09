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
"""Parser for reading content from (E)MSA *.emsa via rosettasciio."""

from datetime import datetime

import flatdict as fd
import numpy as np
from pynxtools.dataconverter.chunk import prioritized_axes_heuristic
from rsciio import msa

from pynxtools_em.utils.custom_logging import logger
from pynxtools_em.utils.default_config import (
    DEFAULT_COMPRESSION_LEVEL,
    DEFAULT_VERBOSITY,
    SEPARATOR,
)
from pynxtools_em.utils.get_checksum import get_sha256_of_file_content
from pynxtools_em.utils.pint_custom_unit_registry import ureg
from pynxtools_em.utils.rsciio_hspy_utils import all_req_keywords_in_dict
from pynxtools_em.utils.string_conversions import string_to_number

"""
def proper_counts(array: np.ndarray) -> np.ndarray:
    if array.ndim == 1 and all(value.is_integer() for value in array):
        min = np.min(array)
        max = np.max(array)
        for bitdepth in [1, 2, 4, 8]:
            if 0 <= min and max <= 2**(8 * bitdepth):
                return array
    return array
"""


class RsciioEmsaParser:
    """Read EMSA/MSA File Format msa."""

    def __init__(
        self, file_path: str = "", entry_id: int = 1, verbose: bool = DEFAULT_VERBOSITY
    ):
        if file_path:
            self.file_path: str = file_path
            self.entry_id: int = entry_id if entry_id > 0 else 1
            self.verbose: bool = verbose
            self.id_mgn: dict[str, int] = {
                "event_id": 1,
                "event_spc": 1,
                "roi": 1,
            }
            # TODO version check
            self.supported: bool = False
            self.obj_idx_supported: list[int] = []
            self.check_if_supported()
            if not self.supported:
                logger.debug(
                    f"Parser {self.__class__.__name__} finds no content in {file_path} that it supports"
                )
        else:
            logger.warning(f"Parser {self.__class__.__name__} needs EMSA/MSA file !")
            self.supported = False

    def check_if_supported(self):
        self.supported = False
        if not self.file_path.lower().endswith(".msa"):
            return
        try:
            self.objs = msa.file_reader(self.file_path, lazy=False, encoding="latin-1")
            reqs = ["data", "axes", "metadata", "original_metadata"]
            if len(self.objs) > 1:
                logger.warning(
                    f"{self.file_path} EMSA files should have only one spectrum"
                )
                return
            for idx, obj in enumerate(self.objs):
                if not isinstance(obj, dict):
                    continue
                if not all_req_keywords_in_dict(obj, reqs):
                    continue
                # TODO version check
                if len(obj["axes"]) != 1:
                    logger.warning(
                        f"{self.file_path} EMSA files should have only one one-dimensional spectrum"
                    )
                    return
                self.obj_idx_supported.append(idx)
                if self.verbose:
                    logger.debug(f"{idx}-th obj is supported")
            if len(self.obj_idx_supported) > 0:
                self.supported = True
        except (OSError, FileNotFoundError, ValueError):
            logger.warning(f"{self.file_path} OS,FileNotFound, or ValueError !")
            return

    def parse(self, template: dict) -> dict:
        """Perform actual parsing."""
        if self.supported:
            with open(self.file_path, "rb", 0) as fp:
                self.file_path_sha256 = get_sha256_of_file_content(fp)
            logger.info(
                f"Parsing {self.file_path} EMSA with SHA256 {self.file_path_sha256} ..."
            )
            self.parse_content(template)
        return template

    def parse_content(self, template: dict) -> dict:
        """Translate tech partner concepts to NeXus concepts."""
        reqs = ["data", "axes", "metadata", "original_metadata"]
        for idx, obj in enumerate(self.objs):
            if not isinstance(obj, dict):
                continue
            if not all_req_keywords_in_dict(obj, reqs):
                continue
            if self.verbose:
                logger.info("original_metadata")
                for keyword, value in obj["original_metadata"].items():
                    logger.info(f"{keyword}{SEPARATOR}{type(value)}{SEPARATOR}{value}")
                logger.info("metadata")
                for keyword, value in obj["metadata"].items():
                    logger.info(f"{keyword}{SEPARATOR}{type(value)}{SEPARATOR}{value}")
                logger.info(f"{obj['axes']}")
            self.process_event_data_em_data(obj, template)
            if self.verbose:
                logger.debug(f"obj{idx}, dims {obj['axes']}")
        return template

    def process_event_data_em_metadata(self, obj: dict, template: dict) -> dict:
        """Map some of the EMSA/MSA-specific metadata concepts on NeXus concepts."""
        identifier: list[int] = [self.entry_id, self.id_mgn["event_id"], 1]
        original_metadata = fd.FlatDict(obj["original_metadata"], "/")
        for keyword, value in original_metadata.items():
            original_metadata[keyword] = string_to_number(value)

        if "DATE" in original_metadata and "TIME" in original_metadata:
            dt = datetime.strptime(
                f"{original_metadata['DATE']} {original_metadata['TIME']}",
                "%d-%b-%Y %H:%M",
            )
            template[f"/ENTRY[entry{identifier[0]}]/start_time"] = f"{dt.isoformat()}"

        for keyword in original_metadata:
            if keyword.startswith("BEAMKV"):
                trg = f"/ENTRY[entry{self.id_mgn['event_id']}]/measurement/eventID[event{self.id_mgn['event_id']}]instrument/ebeam_column/electron_source"
                quantity = ureg.Quantity(
                    np.float64(original_metadata[keyword]), ureg.kilovolt
                ).to(ureg.volt)
                template[f"{trg}/voltage"] = quantity.magnitude
                template[f"{trg}/voltage/@units"] = f"{quantity.units}"
                break

        # TODO extend
        return template

    def process_event_data_em_data(self, obj: dict, template: dict) -> dict:
        """Map Velox-specifically formatted data arrays on NeXus NXdata/NXimage/NXspectrum."""
        metadata = fd.FlatDict(obj["metadata"], "/")
        if "General/title" not in metadata:
            logger.warning(f"Missing General/title metadata keyword")
            return template

        original_metadata = fd.FlatDict(obj["original_metadata"], "/")
        if not all(keyword in original_metadata for keyword in ["XUNITS", "NCOLUMNS"]):
            logger.warning(
                f"Spectrum with irrecoverable energy axis or unsupported formatting"
            )
            return template
        # TODO: check that NCOLUMNS int == 1 and XUNITS = "Energy (EV)"

        axes = obj["axes"]
        if self.verbose:
            logger.debug(axes)
            logger.debug(
                f"entry_id {self.entry_id}, event_id {self.id_mgn['event_id']}"
            )

        # this is the place when you want to skip individually the writing of NXdata
        # return template
        axis_names = None
        # TODO source annotation
        trg = f"/ENTRY[entry{self.entry_id}]/measurement/eventID[event{self.id_mgn['event_id']}]/spectrumID[spectrum1]/spectrum_0d"
        template[f"{trg}/title"] = f"{metadata['General/title']}"
        template[f"{trg}/@signal"] = f"intensity"
        numpy_array = np.asarray(
            obj["data"],
            dtype=np.uint64
            if all(value.is_integer() and value >= 0 for value in obj["data"])
            else np.float64,
        )
        template[f"{trg}/intensity"] = {
            "compress": numpy_array,
            "strength": DEFAULT_COMPRESSION_LEVEL,
            "chunks": prioritized_axes_heuristic(
                numpy_array, np.arange(obj["data"].ndim)
            ),
        }
        template[f"{trg}/intensity/@long_name"] = f"Counts"
        template[f"{trg}/@AXISNAME_indices[axis_energy_indices]"] = np.uint32(0)
        template[f"{trg}/@axes"] = ["axis_energy"]

        # axis_name = axis_names[idx]
        offset = obj["axes"][0]["offset"]
        step = obj["axes"][0]["scale"]
        units = ureg.electron_volt
        count = obj["axes"][0]["size"]
        numpy_array = np.asarray(
            offset + np.linspace(0, count - 1, num=count, endpoint=True) * step,
            np.float32,
        )
        template[f"{trg}/AXISNAME[axis_energy]"] = {
            "compress": numpy_array,
            "strength": DEFAULT_COMPRESSION_LEVEL,
            "chunks": prioritized_axes_heuristic(
                numpy_array, np.arange(numpy_array.ndim)
            ),
        }
        template[f"{trg}/AXISNAME[axis_energy]/@units"] = f"{ureg.Unit(units)}"
        template[f"{trg}/AXISNAME[axis_energy]/@long_name"] = (
            f"Energy ({ureg.Unit(units)})"
        )

        self.process_event_data_em_metadata(obj, template)
        # only one spectrum for EMSA

        return template
