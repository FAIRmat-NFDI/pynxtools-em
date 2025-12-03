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

# python3 ger_berlin_koch_batch_process.py 'microscope_dir' '.'
import os
import sys
import datetime
import logging

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

microscope_directory = sys.argv[1]
target_directory = sys.argv[2]
tic = datetime.datetime.now().timestamp()

logger.info(f"{tic}")
logger.info(f"program name {__name__}")
logger.info(f"python version {sys.version}")
logger.info(f"working_directory {os.getcwd()}")
logger.info(f"microscope_directory {microscope_directory}")
logger.info(f"target_directory {target_directory}")

# TODO::load humans_and_companies.ods
# TODO::load nion_data_additional_metadata.ods

cnt = 0
byte_size_processed = 0
# TODO::alternatively walk over nion_data, check if these exist, check if human has orcid
# TODO::generate eln_data.yaml
# TODO::for row_idx in projects:
for root, dirs, files in os.walk(microscope_directory):
    for file in files:
        fpath = f"{root}/{file}".replace(os.sep * 2, os.sep)
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
