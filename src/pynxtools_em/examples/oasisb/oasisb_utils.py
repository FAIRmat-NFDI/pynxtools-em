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

import io
import logging
import os
import shutil
import sys

import pandas as pd
from pycountry import countries

from pynxtools_em import get_pynxtools_em_version
from pynxtools_em.utils.get_file_from_archive_formats import (
    get_file_from_rar,
    get_file_from_sevenzip,
    get_file_from_tar,
    get_file_from_zip,
)


def get_project_id(project_name: str) -> str:
    """Convert integer project_name ids like 1, 2, 3, ..., to three-digit format with prefix D for dataset or A for article."""
    if 1 <= len(project_name) <= 3:
        return f"{'0' * (3 - len(project_name))}{project_name}"
    return ""


def is_valid_alpha3(code: str) -> bool:
    try:
        return countries.get(alpha_3=code.upper()) is not None
    except KeyError:
        return False


"""
APM_MIME_TYPES_SIDECAR: list[tuple[str, str]] = []

APM_MIME_TYPES_SOLITARY: list[str] = [
    # common file formats for acquisition, reconstruction, and ranging
    ".apt",  # Cameca/AP Suite APT file format currently most used
    ".pos",  # Cameca/IVAS position and mass-to-charge minimal result of reconstruction and mass-to-charge calibration
    ".epos",  # Cameca/IVAS extended POS file, additional data classically designed to assist open-source software development of data analysis algorithms
    ".ato",  # Rouen, GPM
    # will almost always find ".csv",  # sometimes used serialization of reconstructions
    # ranging definitions
    ".env",  # Rouen, GPM
    ".rrng",  # classical Miller-style ranging definitions
    ".rng",  # classical Miller-style ranging definitions
    # ".fig.txt",  # serialized ranging definitions from Erlangen Matlab Atom Probe Toolbox fig file
    # mixed mode, open-source, exotic stuff, and legacy
    # will almost always find # ".h5",  # Erlangen OXCART raw, ranging, and reconstruction, pyccapt
    # will almost always find # ".hdf",
    # will almost always find # ".hdf5",  # Cameca HDF5 from Materials Data Facility
    ".analysis",  # XML-based Imago legacy IVAS state file
    ".analysisset",  # eventually modern? XML-based Cameca/IVAS state file
    # ".nxs",  # NeXus/HDF5
    # will almost always find # ".raw",  # Stuttgart TAP-style instruments
    # "_trimmed.txt",  # Stuttgart APyT complete mass spectrum analysis results file
    # "_xyz.txt",  # Stuttgart APyT reconstruction analysis results file
    # "db.yaml",  # Stuttgart APyT database file
    ".ops",  # legacy 3DAP acquisition, Oxford Position-Sensitive Atom Probe (PoSAP)
    # CAMECA_ROOT_MIME_TYPES
    ".str",  # raw files, acquisition, unprocessed hits
    ".rraw",  # raw files, acquisition, unprocessed hits
    ".rhit",  # classical, IVAS results and parameter of hit finding and analysis steps up to reconstruction and ranging
    ".hits",  # newer, AP Suite results and parameter of hit finding and analysis steps up to reconstruction and ranging
    ".root",  # parameterization of reconstruction and ranging
]
"""


EM_MTEX_MIME_TYPES_SIDECAR: list[tuple[str, str]] = [
    # common file formats for EBSD we preprocess with MTex and then pynxtools-em
    # first value of each pair is always the master, the second that of the sidecar
    (".crc", ".cpr"),  # Oxford Instruments
]

EM_MTEX_MIME_TYPES_SOLITARY: list[str] = [
    # common file formats for EBSD we preprocess with MTex and then pynxtools-em
    ".ang",  # TSL/EDAX OIM
    ".osc",  # Oxford Instruments
    ".ctf",  # Channel text file
]

EM_HFIVE_MIME_TYPES_SIDECAR: list[tuple[str, str]] = []

EM_HFIVE_MIME_TYPES_SOLITARY: list[str] = [
    ".h5oina",
    ".h5",
    ".oh5",
    ".hdf",
    ".hdf5",
    ".edaxh5",
]

EM_EDAX_MIME_TYPES_SIDECAR: list[tuple[str, str]] = []

EM_EDAX_MIME_TYPES_SOLITARY: list[str] = [
    ".spd",
    ".spc",
]


EM_KPY_MIME_TYPES_SIDECAR: list[tuple[str, str]] = []

EM_KPY_MIME_TYPES_SOLITARY: list[str] = [
    ".up1",
    ".up2",
    ".oip",
]

EM_IMAGE_MIME_TYPES_SIDECAR: list[tuple[str, str]] = [
    # common file formats for images we process straight with pynxtools-em
    (".tif", "-tif.hdr"),  # TESCAN
    (".tif", ".txt"),  # JEOL, Hitachi
    (".tiff", ".txt"),  #  JEOL, Hitachi
    (".bmp", ".txt"),
]

EM_IMAGE_MIME_TYPES_SOLITARY: list[str] = [
    # common file formats for images we process straight with pynxtools-em
    ".tif",  # JEOL, Hitachi, Zeiss, ThermoFisher
    ".tiff",
]

EM_MIXED_MIME_TYPES_SIDECAR: list[tuple[str, str]] = [
    # common file formats for mixed content we process straight with pynxtools-em
    (".emi", ".ser"),
]

EM_MIXED_MIME_TYPES_SOLITARY: list[str] = [
    # common file formats for spectra we process straight with pynxtools-em
    ".ipj",  # Oxford Instruments INCA
    ".msa",  # EMSA/MSA
    ".bcf",
    ".dm2",
    ".dm3",
    ".dm4",
    ".dm5",
    ".emd",
]

EM_HDR_MIME_TYPES_SIDECAR: list[tuple[str, str]] = []

EM_HDR_MIME_TYPES_SOLITARY: list[str] = [".hdr"]


CSV_HEADER_FOR_HASH_FILE = "file_path:archive_path;byte_size;unix_mtime;sha256sum"


def prepare_parsing(
    config_file_path: str,
    src_directory: str,
    project_id: str,
    trg_directory: str,
    report: bool,
    write: bool,
    mime_type: str,
    mime_type_solitary: list[str],
    mime_type_sidecar: list[tuple[str, str]],
) -> dict[str, dict[str, int]]:
    """
    Load files from a configuration file, identify MTex-processable files,
    and decompress these to a target directory.

    Parameters
    ----------
    config_file_path : str
        Configuration file (ODS spreadsheet) that lists all files of project with alias project_id.
    src_directory : str
        Directory prefix where to find archive or files that should be processed.
    project_id : str
        Three-digit integer string 001, 002, ..., 999 alias of the project.
    trg_directory : str
        Directory where processable files will be decompressed.
    report : bool
        If True will write a csv file to trg_directory named {project_id}.decompressed.log
    write : bool
        If True will decompress files to disk.
    mime_type : str
        Identifier used in log files to distinguish artifacts of different use cases
    mime_type_solitary : list[str]
        File name ending (e.g. .tif) to use for filtering relevant content when these file formats do not carry metadata sidecar files.
    mime_type_sidecar : list[tuple[str, str]]
        Pair of master file and metadata sidecar file name ending to use for filtering relevant content when these file formats carry metadata sidecar files

    Returns
    -------
    dict[str, Any]
        Dictionary containing metadata about the loaded files, including:
        - which files are processable
        - any errors encountered
    """

    if report:
        log_buffer = io.StringIO()
        log_path = f"{trg_directory}{os.sep}{project_id}.{mime_type}.decompressed.csv"
        logger = logging.getLogger(f"{project_id}")
        logger.setLevel(logging.DEBUG)
        log_handler = logging.StreamHandler(log_buffer)
        # log_handler = logging.FileHandler(log_path, mode="w")
        line_formatting = "%(levelname)s;%(asctime)s;%(message)s"
        time_formatting = "%Y-%m-%dT%H:%M:%S.%z"
        formatter = logging.Formatter(line_formatting, time_formatting)
        log_handler.setFormatter(formatter)
        logger.addHandler(log_handler)

        logger.info(f"python_version: {sys.version.replace(' ', '_')}")
        logger.info(f"working_directory: {os.getcwd()}")
        logger.info(f"pynxtools_em version: {get_pynxtools_em_version()}")
        # logger.info(f"target_directory: {trg_directory}")
        # logger.info(f"config_file: {config_file_path}")
        # logger.info(f"project_id: {project_id}")

    status: dict[str, dict[str, int]] = {}
    for sidecar in mime_type_sidecar:
        if len(sidecar) == 2 and all(
            isinstance(typ, str) and len(typ) > 0 for typ in sidecar
        ):
            key = "_".join([typ for typ in sidecar])
            if key not in status:
                status[key] = {"n": 0, "bytes": 0}
            else:
                logger.error(f"Key {key} already exists in status dict")
    for typ in mime_type_solitary:
        if isinstance(typ, str) and len(typ) > 0:
            status[typ] = {"n": 0, "bytes": 0}

    with open(config_file_path) as fp:
        start = next(
            idx for idx, line in enumerate(fp) if CSV_HEADER_FOR_HASH_FILE in line
        )

    df_hash = pd.read_csv(config_file_path, sep=";", skiprows=start)
    df_hash.columns = ["path", "size", "mtime", "sha256"]

    # build dictionary of hashes to replace original file names with short and clean unique ones
    path_to_hash: dict[str, str] = {}
    path_to_size: dict[str, int] = {}
    for line in df_hash.itertuples(index=True):
        if line.path.count("/") >= 1:
            path = line.path.rsplit("/", 1)[1]
        else:
            path = line.path

        # filter out files that we do not wish to support, e.g. Mac and WSL artifacts
        if any(
            ignore in path for ignore in ["__MACOS", ".DS_Store", ".identifier"]
        ) or path.startswith("._"):
            continue
        # inspecting only the file name ending is not a guarantee that the file is of
        # the expected format, checking for these details is the duty of the pynx plugin
        if line.path.lower().endswith(tuple(mime_type_solitary)) or any(
            line.path.lower().endswith(sidecar) for sidecar in mime_type_sidecar
        ):
            path_to_hash[line.path] = line.sha256  # type: ignore
            # no duplicates possible inside an individual (sub)directory,
            # irrespective if that content is compressed or not cuz for each project
            # line.path encodes file paths
            path_to_size[line.path] = line.size

    # ignore duplicates for NOMAD, cuz we do not wish to store copies
    # of duplicated files across different subdirectories/projects
    hash_to_path: dict[str, str] = {}
    for path, hash in path_to_hash.items():
        # TODO does this process automatically lexicographically sorted?
        if hash not in hash_to_path:
            hash_to_path[hash] = path

    # generate a list of files to finally consider, compose target filenames with hashes
    decompressed: dict[str, str] = {}  # src file as key, trg file name as value
    for hash, path in hash_to_path.items():
        found: bool = False
        for sidecar in mime_type_sidecar:
            if not found:
                if path.lower().endswith(sidecar[0]):
                    # sidecar[0] encodes file ending of the master file
                    # sidecar[1] encodes file ending of the sidecar file
                    path_without_ending = path[0 : len(path) - len(sidecar[0])]
                    for variant in [
                        f"{path_without_ending}{sidecar[1]}",
                        f"{path_without_ending}{sidecar[1].lower()}",
                        f"{path_without_ending}{sidecar[1].upper()}",
                    ]:
                        if variant in path_to_hash:
                            # register master and its sidecar path together
                            # do not register the master or sidecar path twice
                            src = f"{src_directory}{os.sep}{project_id}{os.sep}"
                            trg = f"{trg_directory}{os.sep}"
                            main = f"{src}{path}"
                            side = f"{src}{variant}"
                            if main not in decompressed and side not in decompressed:
                                hsh = f"{hash}.{path_to_hash[variant]}"
                                decompressed[main] = (
                                    f"{trg}{project_id}.{hsh}{sidecar[0]}"
                                )
                                decompressed[side] = (
                                    f"{trg}{project_id}.{hsh}{sidecar[1]}"
                                )
                                status["_".join([typ for typ in sidecar])]["n"] += 1
                                status["_".join([typ for typ in sidecar])]["bytes"] += (
                                    path_to_size[path] + path_to_size[variant]
                                )
                                found = True
                                break  # do not inspect other variants
        if not found:
            for typ in mime_type_solitary:
                if path.lower().endswith(typ):
                    src = f"{src_directory}{os.sep}{project_id}{os.sep}"
                    trg = f"{trg_directory}{os.sep}"
                    main = f"{src}{path}"
                    if main not in decompressed:
                        decompressed[main] = f"{trg}{project_id}.{hash}{typ}"
                        status[typ]["n"] += 1
                        status[typ]["bytes"] += path_to_size[path]
                        found = True
                        break  # do not inspect other endings

    if write:
        archive_handlers = {
            get_file_from_zip: (".zip", ".eln"),
            get_file_from_tar: (".tar", ".tar.gz", ".tar.bz2", ".tar.xz"),
            get_file_from_rar: (".rar"),
            get_file_from_sevenzip: (".7z"),
        }

        for src, trg in decompressed.items():
            if src.count(":") == 1:
                archive_file_path, file_path = src.split(":")
                trg_directory, trg_file_name = trg.rsplit(os.sep, 1)

                for handler, extensions in archive_handlers.items():
                    if archive_file_path.lower().endswith(extensions):  # type: ignore
                        success = handler(
                            archive_file_path, file_path, trg_directory, trg_file_name
                        )
                        if report:
                            if success:
                                logger.info(f"{src};;{trg}")
                            else:
                                logger.error(f"{src};;{trg}")
                        break  # stop checking other handlers once matched
            else:
                try:
                    return_value: str = shutil.copy2(src, trg)
                    if report:
                        if return_value == trg:
                            logger.info(f"{src};;{trg}")
                        else:
                            logger.error(f"{src};;{trg}")
                except OSError:
                    logger.error(f"{src};;{trg}")
    else:
        if report:
            for src, trg in decompressed.items():
                logger.info(f"{src};;{trg}")

    if report:
        # pro: allows writing log files only when these have content
        # con: requires main memory for caching
        if len(decompressed.keys()) > 0:
            with open(log_path, "w") as fp:
                fp.write(log_buffer.getvalue())

    return status


def prepare_parsing_via_config_file(
    config_file_path: str,
    src_directory: str,
    project_id: str,
    trg_directory: str,
    report: bool,
    write: bool,
    mime_type: str,
) -> None:
    """
    Decompress files based on a config file that pecifies all files
    to consider and decompress these to a target directory.

    Parameters
    ----------
    config_file_path :
        Configuration file (ODS spreadsheet) that lists files to consider.
    src_directory :
        Directory prefix where to find archive or files that should be processed.
    project_id :
        Three-digit integer string 001, 002, ..., 999 alias of the project.
    trg_directory :
        Directory where processable files will be decompressed.
    report :
        If True will write a csv file to trg_directory named {project_id}.decompressed.log
    write :
        If True will decompress files to disk.
    mime_type :
        Identifier used in log files to distinguish artifacts of different use cases
    """

    if report:
        log_buffer = io.StringIO()
        log_path = f"{trg_directory}{os.sep}{project_id}.{mime_type}.decompressed.csv"
        print(log_path)
        logger = logging.getLogger(f"{project_id}")
        logger.setLevel(logging.DEBUG)
        log_handler = logging.StreamHandler(log_buffer)
        # log_handler = logging.FileHandler(log_path, mode="w")
        line_formatting = "%(levelname)s;%(asctime)s;%(message)s"
        time_formatting = "%Y-%m-%dT%H:%M:%S.%z"
        formatter = logging.Formatter(line_formatting, time_formatting)
        log_handler.setFormatter(formatter)
        logger.addHandler(log_handler)

        logger.info(f"python_version: {sys.version.replace(' ', '_')}")
        logger.info(f"working_directory: {os.getcwd()}")
        logger.info(f"pynxtools_em version: {get_pynxtools_em_version()}")
        logger.info(f"src_directory: {src_directory}")
        logger.info(f"project_id: {project_id}")
        logger.info(f"trg_directory: {trg_directory}")
        logger.info(f"report: {report}")
        logger.info(f"write: {write}")
        logger.info(f"mime_type: {mime_type}")

    config_file = pd.read_excel(
        config_file_path,
        sheet_name=project_id,
        engine="odf",
        dtype=str,
    ).fillna("")

    decompressed: dict[str, str] = {}  # src file as key, trg file name as value
    for row in config_file.itertuples(index=True):
        print(row)
        if row.src != "" and row.trg != "":
            decompressed[row.src] = row.trg
    logger.info(f"len(decompressed): {len(decompressed)}")

    if write:
        archive_handlers = {
            get_file_from_zip: (".zip", ".eln"),
            get_file_from_tar: (".tar", ".tar.gz", ".tar.bz2", ".tar.xz"),
            get_file_from_rar: (".rar"),
            get_file_from_sevenzip: (".7z"),
        }

        for src, trg in decompressed.items():
            if src.count(":") == 1:
                archive_file_path, file_path = src.split(":")
                trg_directory, trg_file_name = trg.rsplit(os.sep, 1)

                for handler, extensions in archive_handlers.items():
                    if archive_file_path.lower().endswith(extensions):  # type: ignore
                        success = handler(
                            archive_file_path, file_path, trg_directory, trg_file_name
                        )
                        if report:
                            if success:
                                logger.info(f"{src};;{trg}")
                            else:
                                logger.error(f"{src};;{trg}")
                        break  # stop checking other handlers once matched
            else:
                try:
                    return_value: str = shutil.copy2(src, trg)
                    if report:
                        if return_value == trg:
                            logger.info(f"{src};;{trg}")
                        else:
                            logger.error(f"{src};;{trg}")
                except OSError:
                    logger.error(f"{src};;{trg}")
    else:
        if report:
            for src, trg in decompressed.items():
                logger.info(f"{src};;{trg}")

    if report:
        # pro: allows writing log files only when these have content
        # con: requires main memory for caching
        if len(decompressed.keys()) > 0:
            with open(log_path, "w") as fp:
                fp.write(log_buffer.getvalue())
