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

import gc
import glob
import json
import logging
import os
import re
import sys

import bibtexparser
import flatdict as fd
import h5py
from pandas import read_excel
from pynxtools.dataconverter.convert import convert
from pynxtools.dataconverter.helpers import (
    get_nxdl_root_and_path,
    get_pynxtools_version,
)

from pynxtools_em import get_pynxtools_em_version
from pynxtools_em.examples.oasisb.oasisb_eln import generate_oasis_specific_yaml
from pynxtools_em.utils.custom_logging import ISO8601Formatter


def process_project(
    project_name: str,
    bib_file: str,
    hash_file: str,
    source_directory: str,
    target_directory: str,
    mime_type: str,
    alias_prefix_secret: str = "",
    openalex_file: str = "",
    logger_file_path_suffix: str = "",
    nomad_project_name: str = "",
    # generate_eln_file: bool = True,
    # generate_nexus_file: bool = True,
    # time_zone_info: ZoneInfo = ZoneInfo("Europe/Berlin"),
) -> None:
    """Run pynxtools-em to generate a NeXus/HDF5 file for each *.mtex.h5 EBSD file in the project named project_name.

    project_name : name of the legacy EM/MTex project for which this function processes all entries,
        e.g. "D001" is a project-specific such name
    # other than in pynxtools-apm no config file
    # code rather searches through all project-specific mtex.h5 files in source_directory and converts
    # e.g. if project_name = "001" a file 001.*.mtex.h5 will be converted, a file 002.*.mtex.h5 will be not
    bib_file : bibtex bibliography file that resolves project-name-specific CitationKeys like
        D001 or A001 to populate NXcitation instances
    hash_file : csv file which stores the hash and original file name of each file from a project
    source_directory : location of EM/MTex files that the parser should convert
    target_directory : location where generated NeXus/HDF5 and log files should be stored
    mime_type : file format suffix to identify EM domain files (e.g. "dm3", "emd"), no leading "."
    alias_prefix_secret : prefix for the local location where to store mappings for aliasing file names
    openalex_file : (optional) project-name-specific JSON file, retrieved from OpenAlex
        to provide additional metadata context to a project, e.g. D001.son
    logger_file_path_suffix : suffix to add to the name of the log file, e.g. run01
    nomad_project_name : human-readable name used to display in the NOMAD UI overview
    """

    pattern = os.path.join(source_directory, f"{project_name}.*.{mime_type}")
    domain_specifically_formatted_files: list[str] = glob.glob(pattern)
    if len(domain_specifically_formatted_files) == 0:
        return

    config: dict[str, str] = {
        "python_version": f"{sys.version}",
        "working_directory": f"{os.getcwd()}",
        "project_name": project_name,
        "bib_file": bib_file,
        "hash_file": hash_file,
        "source_directory": source_directory,
        "target_directory": target_directory,
        "alias_prefix_secret": alias_prefix_secret,
        "openalex_file": openalex_file,
        "logger_file_path_suffix": logger_file_path_suffix,
        "nomad_project_name": nomad_project_name,
        "pynxtools_version": f"{get_pynxtools_version()}",
        "pynxtools_em_version": f"{get_pynxtools_em_version()}",
    }

    # buffer = io.StringIO()
    custom_formatter = ISO8601Formatter(
        "%(asctime)s;%(name)s;%(levelname)s;%(message)s"
    )
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(custom_formatter)
    file = logging.FileHandler(
        f"{target_directory}{os.sep}{project_name}.{logger_file_path_suffix}.csv",
        mode="w",
    )
    file.setFormatter(custom_formatter)
    logging.basicConfig(
        level=logging.INFO,
        handlers=[console, file],
        force=True,  # to display also for jupyter notebooks
    )

    logger = logging.getLogger(project_name)
    for key, value in config.items():
        logger.info(f"{key};{value}")

    nxdl = "NXem"
    nxdl_root, nxdl_file = get_nxdl_root_and_path(nxdl)
    if not os.path.exists(nxdl_file):
        logger.error(f"Unable to load {nxdl_file}")
        return

    # local configuration files would go here
    try:
        with open(bib_file) as fp:
            bib = bibtexparser.load(fp).entries_dict
    except (FileNotFoundError, OSError):
        logger.error(f"Unable to load {bib_file}")
        return

    # compute hashes for each file when processing legacy data instead of using the original
    # file names i) assures as best as possible disjoint file names, ii) enables as best as
    # possible to filter out duplicates
    # using file names with hashes in the UI of an RDM can be perceived though as cryptic
    # here we explore a mechanism of defining an alias for a file name
    # the files that get parsed follow the convention that replaces the content in the NeXus
    # HDF5 files with the original file name, i.e. given a file name made unique e.g.
    # f"{project_name}.{hash_ctf_file}.ctf"
    # we define a mapping which assigns this file again its original file name
    # "some_archive.zip:some_ebsd.ctf"
    # the keys in file_to_hash end on the alias name
    # the values in file_to_hash end on the file with the hash, respectively
    # note that legacy data is often archived, colon is used to separate archive
    # relative path (some_archive.zip)
    # from absolute path of the file in the archive (some_ebsd.ctf)
    # file path aliasing
    alias_to_original: dict[str, str] = {}
    try:
        with open(hash_file, encoding="utf-8") as fp:
            for _ in range(3):
                next(fp)
            for line in fp:
                # logger lines formatted
                # old decompression log files are formatted like this "INFO 2026-05-19T21:40:49.+0200 /mnt/Map_1.crc > /mnt/e.crc"
                # match = re.match(r"^INFO\s+(\S+)\s+(.+?)\s+>\s+(.+)$", line.rstrip())
                # parts: list[str] = list(match.groups()) if match else []
                # new decompression log files are formatted like this "INFO;2026-06-09T12:34:41.+0200;a.zip:b.emd;;b.emd"
                parts: list[str] = line.split(";") if line.startswith("INFO;") else []
                # old decompression logs
                # if len(parts) == 3:
                #     alias: str = parts[1].replace(alias_prefix_secret, "")
                #     original: str = parts[2]
                # new decompression logs
                if len(parts) == 5:
                    alias: str = parts[2].replace(alias_prefix_secret, "")
                    # the file passed to MTex to obtain an .mtex.h5
                    original: str = parts[4]
                    # the file we pass to pynxtools-em for parsing to NeXus
                    alias_to_original[original] = alias
                    del alias, original
    except (FileNotFoundError, OSError):
        logger.warning(f"Unable to load {hash_file}")
        # return
    logger.info(f"File name aliasing has {len(alias_to_original)} entries")

    # we inject already queried content from the OpenAlex literature reference database
    # to inject additional metadata, this would also allow to add orcid provided the
    # original authors have individually added these upon publishing
    # given that this is often though not the case and given that combining
    # orcid and author name is legally an issue in Germany, we currently do not
    # autorecover the authors' orcid
    openalex = fd.FlatDict({}, "/")
    if openalex_file != "":
        try:
            with open(openalex_file, encoding="utf-8") as fp:
                openalex = fd.FlatDict(json.load(fp), "/")
                # for key, value in openalex.items():
                #     logger.info(f"openalex, {key}, {value}")
        except (FileNotFoundError, json.JSONDecodeError, OSError, TypeError):
            logger.error(f"Unable to load {openalex_file}")

    # one NeXus file per incoming domain-specific file
    if mime_type not in ["msa", "emd", "dm3", "dm4"]:
        logger.error(
            f"EM domain-specific mime_type is not included in the list of supported ones"
        )
        return

    # pattern = os.path.join(source_directory, f"{project_name}.*.{mime_type}")
    # domain_specifically_formatted_files: list[str] = glob.glob(pattern)

    for domain_file in domain_specifically_formatted_files:
        file_name = domain_file.rsplit(os.sep, 1)[1]

        # TODO deal with sidecar files

        # define the name of the NeXus file
        output_file_path = f"{target_directory}{os.sep}{file_name}.nxs"
        if os.path.isfile(output_file_path):
            logger.warning(f"Deleting older version of {output_file_path}")
            os.remove(output_file_path)

        logger.info(f"Compositing {output_file_path}")

        # okay, there is at least some content that we wish to parse for the row
        # collect all external metadata that is not stored in any atom probe specific file
        eln_file_path = generate_oasis_specific_yaml(
            target_directory,
            project_name,
            file_name,
            bib,  # type: ignore
            alias_to_original,
            openalex,
            nomad_project_name,
            write_yaml_file=True,
        )
        if not os.path.isfile(eln_file_path):
            logger.error(
                f"Unable to generate {eln_file_path} whereby to get references to original authors' work"
            )
            continue

        pynx_open_input_files: list[str] = [domain_file, eln_file_path]
        logger.info(f"pynxtools-em {pynx_open_input_files}")

        try:
            convert(
                input_file=tuple(pynx_open_input_files),
                reader="em",
                nxdl=nxdl,
                append=False,
                skip_verify=True,
                ignore_undocumented=True,
                output=output_file_path,
            )
            logger.info(f"pynxtools-em {output_file_path} success")
        except Exception:
            logger.exception(f"pynxtools-em {output_file_path} failed", exc_info=True)

        gc.collect()

    # with open(
    #     f"{target_directory}{os.sep}{project_name}.{logger_file_path_suffix}.csv", "w"
    # ) as fp:
    #     fp.write(buffer.getvalue())

    logger.info(f"Batch queue for project {project_name} processed successfully")
    logger.info(f"Listing all instantiated loggers")
    for name, object in logging.root.manager.loggerDict.items():
        if isinstance(object, logging.Logger) and name.startswith("pynxtools"):
            logger.info(
                f"{name}, level {logging.getLevelName(object.level)}, effective level {logging.getLevelName(logger.getEffectiveLevel())}, handlers {object.handlers}, propagate {object.propagate}"
            )


def get_parsing_tasks(project_id: str, config_file: str) -> dict[str, list[str]]:
    """Reorganize a table with original file names (src) and copies of
    these files named following the pattern f'''{project_id}.{hash}*'''
    (trg) such that (trg) files with different ending, representing main file
    and sidecar file are grouped together, as they should be fed to pynxtools-em
    to generate one NeXus file using task_name as the prefix to the NeXus file."""

    src_trg_table = read_excel(
        config_file,
        sheet_name=project_id,
        engine="odf",
        dtype=str,
    ).fillna("")

    hash_to_input: dict[str, list[str]] = {}
    for row in src_trg_table.itertuples(index=True):
        if row.src != "" and row.trg != "":
            suffix = row.trg.rsplit(os.sep, 1)[1]
            probe = re.search(r"^\d{3}.*", suffix)
            project = suffix[0:3] if probe else None
            del probe

            probe_side = re.search(
                r"^\d{3}\.[a-fA-F0-9]{64}\.[a-fA-F0-9]{64}.*$", suffix
            )
            if probe_side:
                hash = f"{suffix[0 : 3 + 1 + 64 + 1 + 64]}"
            else:
                probe_main = re.search(r"^\d{3}\.[a-fA-F0-9]{64}.*$", suffix)
                if probe_main:
                    hash = f"{suffix[0 : 3 + 1 + 64]}"
                del probe_main
            del probe_side

            if project and hash:
                if hash in hash_to_input:
                    hash_to_input[hash].append(row.trg)
                else:
                    hash_to_input[hash] = [row.trg]
            del project, hash

    tasks: dict[str, list[str]] = {}
    for hash, input in hash_to_input.items():
        tasks[f"{hash}"] = input
    return tasks


def process_task(
    project_name: str,
    input_file_paths: list[str],
    nexus_file_name_prefix: str,
    bib,
    source_directory: str,
    target_directory: str,
    mime_type: str,
    openalex_file: str = "",
    logger_file_path_suffix: str = "image",
    nomad_project_name: str = "",
) -> None:
    """TODO"""

    config: dict[str, str] = {
        "python_version": f"{sys.version}",
        "working_directory": f"{os.getcwd()}",
        "project_name": project_name,
        # input_file_paths
        "nexus_file_name_prefix": nexus_file_name_prefix,
        "source_directory": source_directory,
        "target_directory": target_directory,
        "openalex_file": openalex_file,
        "logger_file_path_suffix": logger_file_path_suffix,
        "nomad_project_name": nomad_project_name,
        "pynxtools_version": f"{get_pynxtools_version()}",
        "pynxtools_em_version": f"{get_pynxtools_em_version()}",
    }

    # buffer = io.StringIO()
    custom_formatter = ISO8601Formatter(
        "%(asctime)s;%(name)s;%(levelname)s;%(message)s"
    )
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(custom_formatter)
    file = logging.FileHandler(
        f"{target_directory}{os.sep}{nexus_file_name_prefix}.{logger_file_path_suffix}.csv",
        mode="w",
    )
    file.setFormatter(custom_formatter)
    logging.basicConfig(
        level=logging.INFO,
        handlers=[console, file],
        force=True,  # to display also for jupyter notebooks
    )

    logger = logging.getLogger(project_name)
    for key, value in config.items():
        logger.info(f"{key};{value}")

    nxdl = "NXem"
    nxdl_root, nxdl_file = get_nxdl_root_and_path(nxdl)
    if not os.path.exists(nxdl_file):
        logger.error(f"Unable to load {nxdl_file}")
        return

    # see notes on process
    alias_to_original: dict[str, str] = {}
    logger.info(f"File name aliasing has {len(alias_to_original)} entries")

    # we inject already queried content from the OpenAlex literature reference database
    # to inject additional metadata, this would also allow to add orcid provided the
    # original authors have individually added these upon publishing
    # given that this is often though not the case and given that combining
    # orcid and author name is legally an issue in Germany, we currently do not
    # autorecover the authors' orcid
    openalex = fd.FlatDict({}, "/")
    if openalex_file != "":
        try:
            with open(openalex_file, encoding="utf-8") as fp:
                openalex = fd.FlatDict(json.load(fp), "/")
                # for key, value in openalex.items():
                #     logger.info(f"openalex, {key}, {value}")
        except (FileNotFoundError, json.JSONDecodeError, OSError, TypeError):
            logger.error(f"Unable to load {openalex_file}")

    output_file_path = (
        f"{target_directory}{os.sep}{nexus_file_name_prefix}.{mime_type}.nxs"
    )
    if os.path.isfile(output_file_path):
        logger.warning(f"Deleting older version of {output_file_path}")
        os.remove(output_file_path)

    logger.info(f"Compositing {output_file_path}")

    # okay, there is at least some content that we wish to parse for the row
    # collect all external metadata that is not stored in any atom probe specific file
    eln_file_path = generate_oasis_specific_yaml(
        target_directory,
        project_name,
        nexus_file_name_prefix,
        bib,  # type: ignore
        alias_to_original,
        openalex,
        nomad_project_name,
        write_yaml_file=True,
    )
    if not os.path.isfile(eln_file_path):
        logger.error(
            f"Unable to generate {eln_file_path} whereby to get references to original authors' work"
        )

    pynx_open_input_files = input_file_paths
    logger.info(f"pynxtools-em {pynx_open_input_files}")

    try:
        convert(
            input_file=tuple(pynx_open_input_files),
            reader="em",
            nxdl=nxdl,
            append=False,
            skip_verify=True,
            ignore_undocumented=True,
            output=output_file_path,
        )
        logger.info(f"pynxtools-em {output_file_path} success")
    except Exception:
        logger.exception(f"pynxtools-em {output_file_path} failed", exc_info=True)

    # check if file exists and has default plot
    if os.path.isfile(output_file_path):
        has_default_plot = False
        with h5py.File(output_file_path, "r") as h5r:
            if "default" in h5r.attrs:
                has_default_plot = True
        if not has_default_plot:
            logger.warning(f"Deleting {output_file_path} as it has no default plot")
            os.remove(output_file_path)

    # gc.collect()

    # with open(
    #     f"{target_directory}{os.sep}{project_name}.{logger_file_path_suffix}.csv", "w"
    # ) as fp:
    #     fp.write(buffer.getvalue())

    logger.info(f"Batch queue for project {project_name} processed successfully")
    logger.info(f"Listing all instantiated loggers")
    # for name, object in logging.root.manager.loggerDict.items():
    #     if isinstance(object, logging.Logger) and name.startswith("pynxtools"):
    #         logger.info(
    #             f"{name}, level {logging.getLevelName(object.level)}, effective level {logging.getLevelName(logger.getEffectiveLevel())}, handlers {object.handlers}, propagate {object.propagate}"
    #         )
