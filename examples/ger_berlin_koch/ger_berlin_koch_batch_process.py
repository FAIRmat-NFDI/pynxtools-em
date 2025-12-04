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

# from pathlib import Path
from pynxtools.dataconverter.convert import convert
from pynxtools.dataconverter.helpers import get_nxdl_root_and_path
from pynxtools_em.utils.get_checksum import get_sha256_of_file_content
from pynxtools_em.utils.versioning import __version__


def export_to_yaml(fpath: str, lookup_dict: dict[str, str | int]):
    """Write content of lookup_dict to yaml file."""
    with open(fpath, "w") as fp:
        yaml.dump(lookup_dict, fp, default_flow_style=False, width=float("inf"))


def export_to_text(fpath: str, the_set: set[str]):
    """Write sorted list of all entries of the_set."""
    with open(fpath, "w") as fp:
        for item in sorted(the_set):
            fp.write(f"{item}\n")


def get_user_name_alias(fpath: str, microscope: str = "nion"):
    if microscope == "nion":
        return fpath[len(f"../../{microscope}_data/") :].split("/")[0]
    return ""


def get_name_and_orcid_from_alias(alias: str, lookup: dict[str, dict[str, str]]):
    for aliases, mdict in lookup.items():
        if alias in [val.strip() for val in aliases.split(";")]:
            # if "id" in mdict[aliases]:
            return (mdict[aliases]["first_surname"], mdict[aliases]["id"])
    logger.warning(f"{alias} not resolvable")
    return ("", "")


INCREMENTAL_REPORTING = 100 * (1024**3)  # in bytes, right now each 100 GiB
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
    "python_version": f"{sys.version}",
    "working_directory": f"{os.getcwd()}",
    "program_name": f"pynxtools_em/{__name__}",
    "program_version": f"{__version__}",
    "microscope_directory": sys.argv[1],  # e.g. '../../nion_data/'
    "target_directory": sys.argv[2],  # e.g. '../'
    "identifier_file_name": sys.argv[3],  # e.g. 'humans_and_companies.ods'
    "legacy_payload_file_name": sys.argv[4],  # e.g. 'nion_data_metadata.ods'
}

ignore_these_directories = tuple(
    [
        f"{config['microscope_directory']}{val}"
        for val in (
            "$RECYCLE",
            "System Volume Information",
            "Swift Libraries",
            "cygdrive",
            "deleteme_test",
            "Bugs",
            "Bruker",
        )
    ]
)


tic = datetime.datetime.now().timestamp()

logger.info(f"{tic}")
for key, value in config.items():
    logger.info(f"{key} {value}")

total_bytes_processed = 0
bytes_processed = 0
nxdl = "NXem"
nxdl_root, nxdl_file = get_nxdl_root_and_path(nxdl)
if not os.path.exists(nxdl_file):
    logger.warning(f"NXDL file {nxdl_file} for nxdl {nxdl} not found")

# load humans_and_companies.ods
identifier: dict[str, dict[str, str]] = {}
df = pd.read_excel(f"{config['identifier_file_name']}", engine="odf")
for idx in np.arange(0, np.shape(df)[0]):
    if all(isinstance(df.iat[idx, val], str) for val in [0, 1, 3]):
        if all(df.iat[idx, val] != "" for val in [0, 1, 3]):
            # nion_data uses user_name_aliases
            if df.iat[idx, 3] != "none_found":
                aliases = df.iat[idx, 1]
                identifier[aliases] = {
                    "first_surname": df.iat[idx, 0],
                    "id": df.iat[idx, 3],
                }
del df
for user_name_aliases, user_metadata_dict in identifier.items():
    logging.debug(f"{user_name_aliases}, {user_metadata_dict}")

# load nion_data_additional_metadata.ods
# df = pd.read_excel(f"{config['legacy_payload_file_name']}", engine="odf")
# for row in df.itertuples(index=True):
# for idx in np.arange(0, np.shape(df)[0]):
#     if df.iat[idx, 1] != 1:
#         continue
#     logger.debug(f"")
# projects: set[str] = set()  # full path to nsproj file
nsproj_to_eln: dict[
    str, str
] = {}  # full path to nsproj file as key, full path to eln_data.yaml file as value
statistics: dict[str, int] = {}  # full path to file as key, byte size as value
# either or
generate_nexus_file = False
collect_statistics = True

for root, dirs, files in os.walk(config["microscope_directory"]):
    for file in files:
        fpath = f"{root}/{file}".replace(os.sep * 2, os.sep)
        if fpath.startswith(ignore_these_directories):
            continue

        if generate_nexus_file:
            # if not fpath.endswith(".nsproj"):
            # if (
            #     fpath
            #     != "../../nion_data/Haas/2022-02-18_Metadata_Kuehbach/2022-02-18_Metadata_Kuehbach.nsproj"
            # ):
            #     continue

            # TODO::alternatively walk over nion_data, check if these exist, check if human has orcid
            # TODO::generate eln_data.yaml
            with open(fpath, "rb", 0) as fp:
                hash = get_sha256_of_file_content(fp)
            eln_fpath = f"{config['working_directory']}/{hash}.eln_data.yaml"
            logger.debug(f"eln_fpath {eln_fpath}")
            nsproj_to_eln[f"{fpath}"] = eln_fpath
            eln_data = {}
            alias = get_user_name_alias(fpath, "nion")
            # eln_data["orcid"] = get_orcid_from_alias(alias, identifier)
            with open(eln_fpath, "w") as fp:
                yaml.dump(eln_data, fp)
            del eln_data

            # TODO::process nsproj file
            # TODO::deactivate hashing and debugging
            input_files_tuple: tuple = (eln_fpath, fpath)
            output_fpath = f"{config['working_directory']}{os.sep}{hash}.output.nxs"
            logger.debug(f"{input_files_tuple}")
            logger.debug(f"{output_fpath}")
            _ = convert(
                input_file=input_files_tuple,
                reader="em",
                nxdl=nxdl,
                skip_verify=True,
                ignore_undocumented=True,
                output=output_fpath,
            )

        if collect_statistics:
            try:
                # TODO::identify current directory
                stat = os.stat(fpath)
                byte_size = stat.st_size

                statistics[f"{fpath}"] = int(byte_size)
                bytes_processed += byte_size
                # logger.info(f"{fpath}{SEPARATOR}{byte_size}")
            except Exception as e:
                logger.warning(f"{fpath}{SEPARATOR}{e}")
            if bytes_processed >= INCREMENTAL_REPORTING:
                total_bytes_processed += bytes_processed
                print(
                    f"Processed {np.around((total_bytes_processed / (1024**4)), decimals=3)} TiB"
                )
                # reset and store results so far collected
                bytes_processed = 0
                if generate_nexus_file:
                    export_to_yaml("nsproj_to_eln.yaml", nsproj_to_eln)

        if not fpath.endswith(".nsproj"):
            continue
        else:
            if not generate_nexus_file:
                nsproj_to_eln[f"{fpath}"] = get_user_name_alias(fpath, "nion")

# last reporting and cleaning up
total_bytes_processed += bytes_processed
print(f"Processed {np.around((total_bytes_processed / (1024**4)), decimals=3)} TiB")
# if generate_nexus_file:
export_to_yaml("nsproj_to_eln.yaml", nsproj_to_eln)
if collect_statistics:
    export_to_yaml("statistics.yaml", statistics)
# export_to_text("projects.txt", projects)
toc = datetime.datetime.now().timestamp()
logger.info(f"{toc}")
print(f"Batch queue processed successfully")
