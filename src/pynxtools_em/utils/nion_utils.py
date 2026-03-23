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
"""Utility functions for working with Nion Co. content and concepts."""

import typing
import uuid

import numpy as np
from numpy.lib.format import read_array_header_1_0, read_array_header_2_0

from pynxtools_em.utils.custom_logging import logger

# see https://github.com/nion-software/nionswift/blob/e95839c5602d009006ea88a648e5f78dc77c1ea4/
# nion/swift/model/Profile.py line 146 and following


def encode(uuid_: uuid.UUID, alphabet: str) -> str:
    result = ""
    uuid_int = uuid_.int
    while uuid_int:
        uuid_int, digit = divmod(uuid_int, len(alphabet))
        result += alphabet[digit]
    return result


def uuid_to_file_name(data_item_uuid_str: str) -> str:
    data_item_uuid_uuid = uuid.UUID(f"{data_item_uuid_str}")
    return f"data_{encode(data_item_uuid_uuid, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890')}"
    # 25 character results


def nion_image_spectrum_or_generic_nxdata(list_of_dict) -> str:
    """Encode sequence of units to tell whether NXimage, NXspectrum, NXdata."""
    if len(list_of_dict) >= 1:
        token = []
        for obj in list_of_dict:
            if isinstance(obj, dict):
                if list(obj.keys()) == ["offset", "scale", "units"]:
                    if obj["units"] == "":
                        token.append("unitless")
                    else:
                        token.append(obj["units"])
                else:
                    logger.warning(
                        f"{obj.keys()} are not exactly the expected keywords!"
                    )
            else:
                logger.warning(f"{obj} is not a dict!")
        if len(token) >= 1:
            return "_".join(token)
    return ""


def read_numpy_array_metadata(
    fp: typing.BinaryIO,
    local_files: dict[int, tuple[bytes, int, int, int]],
    dir_files: dict[bytes, tuple[int, int]],
    name_bytes: bytes,
):
    """
    Read the metadata from a numpy data array that is stored in a nionswift zip file

    :param fp: a file pointer
    :param local_files: the local files structure
    :param dir_files: the directory headers
    :param name: the name of the data file to read
    :return: the numpy data array, if found

    The file pointer will be at a location following the
    local file entry after this method.

    The local_files and dir_files should be passed from
    the results of parse_zip.
    """
    # combining here the read_data from nionswift
    if name_bytes in dir_files:
        fp.seek(local_files[dir_files[name_bytes][1]][1])
        # instead of returning the entire file here only read the
        # header that contains shape, type, and storage order
        # use that fp was opened rb !
        magic = np.lib.format.read_magic(fp)
        if magic[0] == 1:
            header = read_array_header_1_0(fp)
        else:
            header = read_array_header_2_0(fp)
        return header
    return None
