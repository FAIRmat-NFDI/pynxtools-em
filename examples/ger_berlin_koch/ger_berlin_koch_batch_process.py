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

"""Functionalities for batch processing data."""

# data should be stored in projects under some home directory
# a batch queue processes projects in this HOME directory based on
# a single coordinating OpenOffice sheet is used to inject
# additional ELN-style "missing" data and configure the projects parsed
# during this processing technology-partner specific content,
# e.g., nion, JEOL, Zeiss, stuff is parsed using pynxtools-em to generate
# one NeXus/HDF5 file per project

# python3 ger_berlin_koch_batch_process.py 'microscope_dir' '.' 'humans_and_companies.ods' 'nion_data_metadata.ods'
import os
import sys
import datetime
import logging
import pandas as pd
import numpy as np
import yaml
from pynxtools.dataconverter.convert import convert
from pynxtools.dataconverter.helpers import get_nxdl_root_and_path
from pynxtools_em.utils.get_checksum import get_sha256_of_file_content


INCREMENTAL_REPORTING = 1 * 1024 * 1024 * 1024  # in bytes
SEPARATOR = "____"
DEFAULT_LOGGER_NAME = "ger_berlin_koch_group_process"
logger = logging.getLogger(DEFAULT_LOGGER_NAME)
ffmt = "%(levelname)s %(asctime)s %(message)s"
tfmt = "%Y-%m-%dT%H:%M:%S%z"  # .%f%z"
logging.basicConfig(
    filename=f"{DEFAULT_LOGGER_NAME}.log",
    filemode="w",  # use "a" to collect all in a session, use "w" to overwrite
    format=ffmt,
    datefmt=tfmt,
    encoding="utf-8",
    level=logging.DEBUG,
)
# root = logging.getLogger()
# for handler in root.handlers:
#     handler.setFormatter(logging.Formatter(ffmt, tfmt))

config: dict[str, str] = {
    "program name": f"{__name__}",
    "python version": f"{sys.version}",
    "working_directory": f"{os.getcwd()}",
    "microscope_directory": sys.argv[1],  # 'microscope_dir'
    "target_directory": sys.argv[2],  # '.'
    "identifier_file_name": sys.argv[3],  # 'humans_and_companies.ods'
    "legacy_payload_file_name": sys.argv[4],  # 'nion_data_metadata.ods'
}
tic = datetime.datetime.now().timestamp()

logger.info(f"{tic}")
for key, value in config.items():
    logger.info(f"{key} {value}")

cnt = 0
byte_size_processed = 0
nxdl = "NXem"
nxdl_root, nxdl_file = get_nxdl_root_and_path(nxdl)
if not os.path.exists(nxdl_file):
    logger.warning(f"NXDL file {nxdl_file} for nxdl {nxdl} not found")

# load humans_and_companies.ods
identifier: dict[str, str] = {}
df = pd.read_excel(f"{config['identifier_file_name']}", engine="odf")
for idx in np.arange(0, np.shape(df)[0]):
    if all(isinstance(df.iat[idx, val], str) for val in [0, 2]):
        if all(df.iat[idx, val] != "" for val in [0, 2]):
            if df.iat[idx, 2] != "none_found":
                identifier[df.iat[idx, 0]] = df.iat[idx, 2]
del df
for key, value in identifier.items():
    logging.debug(f"{key}, {value}")

# load nion_data_additional_metadata.ods
# df = pd.read_excel(f"{config['legacy_payload_file_name']}", engine="odf")
# for row in df.itertuples(index=True):
# for idx in np.arange(0, np.shape(df)[0]):
#     if df.iat[idx, 1] != 1:
#         continue
#     logger.debug(f"")
nsproj_to_eln = {}
for root, dirs, files in os.walk(config["microscope_directory"]):
    for file in files:
        fpath = f"{root}/{file}".replace(os.sep * 2, os.sep)
        # if not fpath.endswith(".nsproj"):
        if (
            fpath
            != "../../nion_data/Haas/2022-02-18_Metadata_Kuehbach/2022-02-18_Metadata_Kuehbach.nsproj"
        ):
            continue

        logger.debug("Working on test case")
        # TODO::alternatively walk over nion_data, check if these exist, check if human has orcid
        # TODO::generate eln_data.yaml
        with open(fpath, "rb", 0) as fp:
            hash = get_sha256_of_file_content(fp)
        logger.debug(f"{hash}")
        eln_fpath = f"{config['working_directory']}/{hash}.eln_data.yaml"
        logger.debug(f"eln_fpath {eln_fpath}")
        nsproj_to_eln[fpath] = eln_fpath
        eln_data = {}
        with open(eln_fpath, "w") as fp:
            yaml.dump(eln_data, fp)
        del eln_data

        # READER_NAME = "em"
        # READER_CLASS = get_reader(READER_NAME)
        # NXDLS = ["NXem"]
        tmp_path = ""
        input_files_tuple: tuple = (eln_fpath, fpath)
        logger.debug(f"{input_files_tuple}")

        # caplog_level: Literal["ERROR", "WARNING"] = "WARNING"
        # Clear the log of `convert`
        # caplog.clear()
        # with caplog.at_level(caplog_level):
        logger.debug(f"Attempt converting {tmp_path}/{os.sep}/output.nxs")
        _ = convert(
            input_file=input_files_tuple,
            reader="em",
            nxdl=nxdl,
            skip_verify=False,
            ignore_undocumented=True,
            output=f"{tmp_path}/{os.sep}/output.nxs",
        )

        # fname = os.path.basename(fpath)
        # cnt += 1
        # always attempt to hash the file first
        try:
            # TODO::identify current directory
            # TODO::process nsproj file
            stat = os.stat(fpath)
            byte_size = stat.st_size
            byte_size_processed += byte_size
            logger.info(f"{fpath}{SEPARATOR}{byte_size}")
        except Exception as e:
            logger.warning(f"{fpath}{SEPARATOR}{e}")
        if byte_size_processed >= INCREMENTAL_REPORTING:
            print(f"Processed {byte_size_processed}")
            byte_size_processed = 0

toc = datetime.datetime.now().timestamp()
logger.info(f"{toc}")
print(f"Batch queue processed successfully")
