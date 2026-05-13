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

"""Script to batch-convert to NeXus/HDF5 using pynxtools-apm."""

# python3 pynxtools-apm/examples/oasisb/04_convert_archived_legacy_data_using_pynxtools.py ... /harvest_examples/data ... /scidat_nomad_apt aus_sydney_bilal
import gc
import importlib.metadata
import logging
import os
import sys
from datetime import datetime

import bibtexparser
import pandas as pd
from ifes_apt_tc_data_modeling.utils.versioning import (
    get_ifes_apt_tc_data_modeling_version,
)
from pynxtools.dataconverter.convert import convert
from pynxtools.dataconverter.helpers import (
    get_nxdl_root_and_path,
    get_pynxtools_version,
)

from pynxtools_apm import get_pynxtools_apm_version
from pynxtools_apm.examples.oasisb_eln import generate_oasis_specific_yaml
from pynxtools_apm.examples.oasisb_utils import generate_file_to_hash

config: dict[str, str] = {
    "python_version": f"{sys.version}",
    "working_directory": f"{os.getcwd()}",
    "pynxtools_name": f"pynxtools",
    "pynxtools_version": f"{get_pynxtools_version()}",
    "pynxtools_apm_name": f"pynxtools_apm/{__name__}",
    "pynxtools_apm_version": f"{get_pynxtools_apm_version()}",
    "ifes_apt_tc_data_modeling_name": f"ifes_apt_tc_data_modeling",
    "ifes_apt_tc_data_modeling_version": f"{get_ifes_apt_tc_data_modeling_version()}",
    "source_directory": sys.argv[1],  # e.g., endswith {os.sep}data
    "target_directory": sys.argv[2],
    # therein, {os.sep}decompressed for the input_files and {os.sep}nexus_hfive for the output NeXus/HDF5 files
    # the actual legacy atom probe project to process all entries of
    "project_name": sys.argv[3],
}


DEFAULT_LOGGER_NAME = "scidat_nomad_apt_process"
logger = logging.getLogger(DEFAULT_LOGGER_NAME)
line_formatting = "%(levelname)s %(asctime)s %(message)s"
time_formatting = "%Y-%m-%dT%H:%M:%S.%z"  # .%f%z"
formatter = logging.Formatter(line_formatting, time_formatting)


def switch_root_logfile(filename, log_level=logging.DEBUG):
    """Replace the root logger's handler with a new FileHandler."""
    root = logging.getLogger()
    root.setLevel(log_level)
    # remove and close old handlers
    for h in root.handlers[:]:
        root.removeHandler(h)
        try:
            h.close()
        except Exception:
            pass
    # install new one
    new_handler = logging.FileHandler(filename, mode="a", encoding="utf-8")
    new_handler.setFormatter(formatter)
    root.addHandler(new_handler)
    return new_handler


tic = datetime.now().timestamp()

script_log_file_path = f"{config['working_directory']}{os.sep}{DEFAULT_LOGGER_NAME}.log"
if os.path.exists(script_log_file_path):
    os.remove(script_log_file_path)
switch_root_logfile(script_log_file_path)

logger.info(f"{tic}")
for key, value in config.items():
    logger.info(f"{key} {value}")

nxdl = "NXapm"
nxdl_root, nxdl_file = get_nxdl_root_and_path(nxdl)
if not os.path.exists(nxdl_file):
    logger.warning(f"NXDL file {nxdl_file} for nxdl {nxdl} not found")

# load configuration sheet for the project from the source_directory
spread_sheet_of_project = pd.read_excel(
    f"{config['source_directory']}{os.sep}{config['project_name']}.ods",
    sheet_name=f"{config['project_name']}",
    engine="odf",
).fillna("")

# load bibliography to identify the data and eventually paper publication for the project
with open(f"{config['source_directory']}{os.sep}aaa_legacy_data.bib") as fp:
    bib = bibtexparser.load(fp).entries_dict

file_to_hash = generate_file_to_hash(
    f"{config['source_directory']}{os.sep}{config['project_name']}.sha256.results.csv"
)  # TODO

# full path to file as key, byte size as value
statistics: dict[str, int] = {}
generate_eln_file: bool = True
generate_nexus_file: bool = True
parse: int = 1
project_name = config["project_name"]
input_file_path_prefix = f"{config['target_directory']}{os.sep}decompressed"
output_file_path_prefix = (
    f"{config['target_directory']}{os.sep}apm_prepare_nomad_v142"  # nexus_hfive"
)

# NeXus file is composed eventually from multiple files and sources
# ELN, proprietary AMETEK/Cameca metadata, and open-source files (pos, apt, rrng, etc.)
for row_idx in range(spread_sheet_of_project.shape[0]):
    ### DO WE HAVE INPUT AT ALL ?
    has_input: bool = False
    for col_idx in range(1, 6):  # ignore str_rraw and comment columns i.e. >=6
        # col_idx int will resolve to
        # 0, str_rraw
        # 1, rhit_hits
        # 2, root
        # 3, pos_epos_apt_ato_csv
        # 4, rng_rrng_fig_env
        # 5, hdf_xml_nxs_raw_ops
        value = spread_sheet_of_project.iat[row_idx, col_idx]  # type: ignore
        if value == "":
            continue
        has_input = True
        break
    if not has_input:
        continue
    del col_idx

    ### GENERATE OASIS-SPECIFIC ELN content (remaining metadata not stored in files)
    eln_file_path = generate_oasis_specific_yaml(
        project_name,
        row_idx,  # type: ignore
        output_file_path_prefix,
        bib,  # type: ignore
    )
    print(eln_file_path)

    if eln_file_path == "":
        continue

    # eln_file_path = f"{output_file_path_prefix}/{project_name}.{row_idx}.oasis.specific.yaml"  # eln_data.yaml"
    if not os.path.isfile(eln_file_path):
        continue

    ### DEFINE OUTPUT NAME OF THE NEXUS FILE
    output_file_path = f"{eln_file_path.replace('.oasis.specific.yaml', '')}.output.nxs"
    # if not os.path.isfile(output_file_path):
    #     continue

    # split log one log file for each pair of root and open parsing
    log_file_path = f"{output_file_path}.log"
    if os.path.exists(log_file_path):
        os.remove(log_file_path)
    switch_root_logfile(log_file_path, logging.INFO)
    # separating the log messages from the individual parser call
    # to get one log file per generated NeXus/HDF5 file == per NOMAD entry
    for key, value in config.items():
        logger.info(f"{key} {value}")
    del key, value

    ### DO WE HAVE PROPRIETARY INPUT ?
    try:
        # pynxtools-camecaroot is not in the public domain!
        pynxtools_camecaroot_version = (
            f"{importlib.metadata.version('pynxtools-camecaroot')}"
        )
    except importlib.metadata.PackageNotFoundError:
        pynxtools_camecaroot_version = "unknown_version"

    root_parser_used: bool = False  # relevant to distinguish if we need to run
    # pynxtools-apm in append mode (if root_parser_used == True) or not (if False)
    if pynxtools_camecaroot_version != "unknown_version" and root_parser_used:
        pynx_root_input_files: list[str] = []
        for col_idx in range(1, 6):  # ignore str_rraw
            # col_idx int will be 0, str_rraw, 1, rhit_hits, 2, root,
            # 3, pos_epos_apt_ato_csv, 4, rng_rrng_fig_env, 5, hdf_xml_nxs_raw_ops
            value = spread_sheet_of_project.iat[row_idx, col_idx]  # type: ignore
            if value == "":
                continue
            pynx_root_input_files.append(
                f"{input_file_path_prefix}{os.sep}"
                f"{project_name}.{row_idx}.{col_idx}."
                f"{file_to_hash[value]}."  # type: ignore
                f"{value.rsplit('.', 1)[-1].lower()}"  # type: ignore
            )
        del col_idx

        if len(pynx_root_input_files) > 0:
            # RUN DATACONVERTER USING PYNXTOOLS-CAMECAROOT
            input_files_tuple = tuple(pynx_root_input_files)
            logger.debug(f"{input_files_tuple}")
            logger.debug(f"{output_file_path}")

            _ = convert(
                input_file=input_files_tuple,
                reader="camecaroot",
                nxdl=nxdl,
                append=False,
                skip_verify=True,
                ignore_undocumented=True,
                output=output_file_path,
            )
            root_parser_used = True

            # release memory and resources associated with previous processing
            del _, pynx_root_input_files, input_files_tuple

    ### DO WE HAVE OPEN-SOURCE INPUT ?
    pynx_open_input_files: list[str] = []
    for col_idx in range(3, 6):
        # col_idx int will be 0, str_rraw, 1, rhit_hits, 2, root,
        # 3, pos_epos_apt_ato_csv, 4, rng_rrng_fig_env, 5, hdf_xml_nxs_raw_ops
        value = spread_sheet_of_project.iat[row_idx, col_idx]  # type: ignore
        if value == "":
            continue
        pynx_open_input_files.append(
            f"{input_file_path_prefix}{os.sep}"
            f"{project_name}.{row_idx}.{col_idx}."
            f"{file_to_hash[value]}."  # type: ignore
            f"{value.rsplit('.', 1)[-1].lower()}"  # type: ignore
        )
    del col_idx

    # in every case ELN content is added by pynxtools-apm
    pynx_open_input_files.append(eln_file_path)

    # RUN DATACONVERTER USING PYNXTOOLS-APM
    input_files_tuple = tuple(pynx_open_input_files)
    logger.debug(f"{input_files_tuple}")
    logger.debug(f"{output_file_path}")

    if root_parser_used:
        _ = convert(
            input_file=input_files_tuple,
            reader="apm",
            nxdl=nxdl,
            append=True,
            skip_verify=True,  # obsolete as append switches validation off anyway
            ignore_undocumented=True,
            output=output_file_path,
        )
    else:
        _ = convert(
            input_file=input_files_tuple,
            reader="apm",
            nxdl=nxdl,
            append=False,
            skip_verify=True,
            ignore_undocumented=True,
            output=output_file_path,
        )

    # release memory and resources associated with previous processing
    del _, pynx_open_input_files, input_files_tuple
    # TODO::there is evidence of that the switch_root_logfile causes a memory
    # leak as the more its called the more memory does not get freed despite
    # running the garbage collection, ok for now but should be fixed
    # for better machine utilization at some point.

    execute: bool = False
    if execute:
        input_files_tuple = tuple([eln_file_path])
        logger.debug(f"{input_files_tuple}")
        logger.debug(f"{output_file_path}")

        _ = convert(
            input_file=input_files_tuple,
            reader="apm",
            nxdl=nxdl,
            append=True,
            skip_verify=True,  # obsolete as append switches validation off anyway
            ignore_undocumented=True,
            output=output_file_path,
        )
        del _, input_files_tuple

    gc.collect()

    switch_root_logfile(script_log_file_path)

# use case analyze content

# lastly, final report and clean up
switch_root_logfile(script_log_file_path)

toc = datetime.now().timestamp()
logger.info(f"{toc}")
print(f"Batch queue for project {config['project_name']} processed successfully")
