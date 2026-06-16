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
"""Parser for reading content from EDAX binary (SPC, SPD, etc.) via rosettasciio."""



import flatdict as fd
import numpy as np
from pynxtools.dataconverter.chunk import prioritized_axes_heuristic
from rsciio import edax

from pynxtools_em.utils.custom_logging import logger
from pynxtools_em.utils.default_config import (
    DEFAULT_COMPRESSION_LEVEL,
    DEFAULT_VERBOSITY,
    SEPARATOR,
)
from pynxtools_em.utils.get_checksum import get_sha256_of_file_content
from pynxtools_em.utils.pint_custom_unit_registry import ureg
from pynxtools_em.utils.rsciio_hspy_utils import all_req_keywords_in_dict
from pynxtools_em.utils.schema_version import EmSchemaVersion

"""
itemsize_to_numpy_dtype: dict[str, dict[int, Any]] = {
    "unsigned": {1: np.uint8, 2: np.uint16, 4: np.uint32, 8: np.uint64},
    "signed": {1: np.int8, 2: np.int16, 4: np.int32, 8: np.int64},
}  # TODO type anno -> np.dtype


def get_compact_integer_datatype(data: np.ndarray):  # TODO type anno -> np.dtype:
    smallest = np.minimum(data)
    largest = np.maximum(data)
    if smallest >= 0:
        for itemsize in [1, 2, 4, 8]:
            if 2 ** (8 * itemsize) > largest:
                return itemsize_to_numpy_dtype["unsigned"][itemsize]
        return itemsize_to_numpy_dtype["unsigned"][8]
    else:
        for itemsize in [1, 2, 4, 8]:
            if (
                -1 * (2 ** (8 * itemsize)) / 2 < smallest
                and (2 ** (8 * itemsize)) / 2 > largest
            ):
                return itemsize_to_numpy_dtype["signed"][itemsize]
        return itemsize_to_numpy_dtype["signed"][8]
"""


class RsciioEdaxParser:
    """Read EDAX SPC/SPD File Format msa."""

    def __init__(
        self,
        file_paths: list[str],
        entry_id: int = 1,
        verbose: bool = DEFAULT_VERBOSITY,
    ):
        self.file_path = file_paths[0] if len(file_paths) > 0 else None
        # TODO analyze stem
        self.entry_id = max(1, entry_id)
        self.verbose = verbose
        self.id_mgn: dict[str, int] = {
            "event_id": 1,
            "event_spc": 1,
            "roi": 1,
        }
        self.versions: list[EmSchemaVersion] = []
        self.supported: bool = False
        self.obj_idx_supported: list[int] = []

        if not self.file_path:
            logger.warning(
                f"Parser {self.__class__.__name__} needs EDAX binary (e.g. SPC, SPD) file !"
            )
            return

        self.check_if_supported()

        if not self.supported:
            logger.debug(
                f"Parser {self.__class__.__name__} finds no content in {self.file_path} that it supports"
            )

    def check_if_supported(self):
        self.supported = False
        if self.file_path.lower().endswith(".lsd"):
            # TODO better solution than renaming necessary
            pass

        if not self.file_path.lower().endswith((".spc", ".spd")):
            return
        try:
            self.objs = edax.file_reader(self.file_path, lazy=False)
            reqs = ["data", "axes", "metadata", "original_metadata"]
            # TODO how many objects to expect for SPC files ?
            for idx, obj in enumerate(self.objs):
                if not isinstance(obj, dict) or not all_req_keywords_in_dict(obj, reqs):
                    continue
                # TODO version check
                if len(obj["axes"]) != 1:
                    logger.warning(
                        f"{self.file_path} SPC files should have only one one-dimensional spectrum"
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
                f"Parsing {self.file_path} EDAX binary with SHA256 {self.file_path_sha256} ..."
            )
            self.parse_content(template)
        return template

    def parse_content(self, template: dict) -> dict:
        """Translate tech partner concepts to NeXus concepts."""
        for idx, obj in enumerate(self.objs):
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
        """Map some of the EDAX-binary-specific metadata concepts on NeXus concepts."""
        """
        identifier: list[int] = [self.entry_id, self.id_mgn["event_id"], 1]
        original_metadata = fd.FlatDict(obj["original_metadata"], "/")
        for key, value in original_metadata.items():
            original_metadata[key] = string_to_number(value)

        if all(key in original_metadata for key in ["DATE", "TIME"]):
            if all(original_metadata[key] != "" for key in ["DATE", "TIME"]):
                template[f"/ENTRY[entry{identifier[0]}]/start_time"] = (
                    f"{datetime.strptime(f'''{original_metadata['DATE']} {original_metadata['TIME']}''', '%d-%b-%Y %H:%M').isoformat()}"
                )

        for key in original_metadata:
            if key.startswith("BEAMKV"):
                trg = f"/ENTRY[entry{self.id_mgn['event_id']}]/measurement/eventID[event{self.id_mgn['event_id']}]instrument/ebeam_column/electron_source"
                quantity = ureg.Quantity(
                    np.float64(original_metadata[key]), ureg.kilovolt
                ).to(ureg.volt)
                template[f"{trg}/voltage"] = quantity.magnitude
                template[f"{trg}/voltage/@units"] = f"{quantity.units}"
                break
        """
        return template

    def process_event_data_em_data(self, obj: dict, template: dict) -> dict:
        """Map EDAX binary-specific formatted data arrays on NeXus NXdata/NXimage/NXspectrum."""
        metadata = fd.FlatDict(obj["metadata"], "/")
        if "General/title" not in metadata:
            logger.warning(f"Missing General/title metadata keyword")
            return template

        original_metadata = fd.FlatDict(obj["original_metadata"], "/")
        if not all(
            keyword in original_metadata
            for keyword in [
                "spc_header/numPts",
                "spc_header/evPerChan",
                "spc_header/startEnergy",
                "spc_header/endEnergy",
            ]
        ):
            logger.warning(
                f"Spectrum with unclear energy axis or unsupported formatting"
            )
            return template

        axes = obj["axes"]
        if self.verbose:
            logger.debug(axes)
            logger.debug(
                f"entry_id {self.entry_id}, event_id {self.id_mgn['event_id']}"
            )

        # this is the place when you want to skip individually the writing of NXdata
        # return template

        trg = f"/ENTRY[entry{self.entry_id}]/measurement/eventID[event{self.id_mgn['event_id']}]/spectrumID[spectrum1]/spectrum_0d"
        template[f"{trg}/title"] = f"{metadata['General/title']}"
        template[f"{trg}/@signal"] = f"intensity"
        numpy_array = np.asarray(
            obj["data"],
            dtype=np.uint64  # get_compact_integer_datatype(obj["data"])
            if all(value.is_integer() for value in obj["data"])
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

        # spc_header/endEnergy, 40.95000076293945  # keV
        offset = ureg.Quantity(
            original_metadata["spc_header/startEnergy"], ureg.kiloelectron_volt
        ).to(ureg.electron_volt)
        step = ureg.Quantity(
            original_metadata["spc_header/evPerChan"], ureg.electron_volt
        )
        count = original_metadata["spc_header/numPts"]
        numpy_array = np.asarray(
            offset.magnitude
            + np.linspace(0, count - 1, num=count, endpoint=True) * step.magnitude,
            np.float32,
        )
        template[f"{trg}/AXISNAME[axis_energy]"] = {
            "compress": numpy_array,
            "strength": DEFAULT_COMPRESSION_LEVEL,
            "chunks": prioritized_axes_heuristic(
                numpy_array, np.arange(numpy_array.ndim)
            ),
        }
        template[f"{trg}/AXISNAME[axis_energy]/@units"] = f"{step.units}"
        template[f"{trg}/AXISNAME[axis_energy]/@long_name"] = f"Energy ({step.units})"

        self.process_event_data_em_metadata(obj, template)

        return template
