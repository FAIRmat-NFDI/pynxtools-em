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

import logging
import os
import shutil
import sys

import pandas as pd
import yaml
from pycountry import countries

from pynxtools_em import get_pynxtools_em_version
from pynxtools_em.examples.get_file_from_archive_formats import (
    get_file_from_rar,
    get_file_from_sevenzip,
    get_file_from_tar,
    get_file_from_zip,
)


def get_project_id(project_name: str, typ: str = "D") -> str:
    """Convert integer project_name ids like 1, 2, 3, ..., to three-digit format with prefix D for dataset or A for article."""
    if 1 <= len(project_name) <= 3:  # typ == "D" or typ == "A" and
        return f"{'0' * (3 - len(project_name))}{project_name}"  # {typ}
    return ""


# print(get_project_id("1"))


def snake_case_to_camel_case(snake_case: str) -> str:
    camel_case = ""
    for token in snake_case.split("_"):
        camel_case += token.capitalize()
    return camel_case


# print(snake_case_to_camel_case("usa_portland_wang"))
# print(snake_case_to_camel_case("usa_idaho_boise01"))


def export_to_yaml(fpath: str, lookup_dict: dict):
    """Write content of lookup_dict to yaml file."""
    with open(fpath, "w") as fp:
        yaml.dump(lookup_dict, fp, default_flow_style=False, width=float("inf"))


def export_to_text(fpath: str, the_set: set[str]):
    """Write sorted list of all entries of the_set."""
    with open(fpath, "w") as fp:
        for item in sorted(the_set):
            fp.write(f"{item}\n")


def alpha2_to_alpha3(alpha2: str) -> str:
    country = countries.get(alpha_2=alpha2)
    return country.alpha_3 if country else ""


# print(alpha2_to_alpha3("US").lower())


def is_valid_alpha3(code: str) -> bool:
    try:
        return countries.get(alpha_3=code.upper()) is not None
    except KeyError:
        return False


EM_EBSD_MTEX_MIME_TYPES_SIDECAR: list[tuple[str, str]] = [
    # common file formats for EBSD we preprocess with MTex and then pynxtools-em
    # first value of each pair is always the master, the second that of the sidecar
    (".crc", ".cpr"),  # Oxford Instruments
]

EM_EBSD_MTEX_MIME_TYPES_SOLITARY: list[str] = [
    # common file formats for EBSD we preprocess with MTex and then pynxtools-em
    ".ang",  # TSL/EDAX OIM
    ".osc",  # Oxford Instruments
    ".ctf",  # Channel text file
]


# EM_EBSD_KPY_MIME_TYPES = [
#     # common file formats for EBSD we process straight with pynxtools-em using kikuchipy
# ]


CSV_HEADER_FOR_HASH_FILE = "file_path:archive_path;byte_size;unix_mtime;sha256sum"


def prepare_em_ebsd_mtex(
    config_file_path: str,
    src_directory: str,
    project_id: str,
    trg_directory: str,
    report: bool = True,
    write: bool = True,
) -> dict[str, dict[str, int]]:
    """
    Load EBSD files from a configuration file, identify MTex-processable files,
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

    Returns
    -------
    dict[str, Any]
        Dictionary containing metadata about the loaded files, including:
        - which files are processable
        - any errors encountered
    """

    log_path = f"{trg_directory}{os.sep}{project_id}.decompressed.log"
    logger = logging.getLogger(f"{project_id}")
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(log_path, mode="w")
    line_formatting = "%(levelname)s %(asctime)s %(message)s"
    time_formatting = "%Y-%m-%dT%H:%M:%S.%z"
    formatter = logging.Formatter(line_formatting, time_formatting)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    if report:
        logger.info(f"python_version: {sys.version.replace(' ', '_')}")
        logger.info(f"working_directory: {os.getcwd()}")
        logger.info(f"pynxtools_em version: {get_pynxtools_em_version()}")
        # logger.info(f"target_directory: {trg_directory}")
        # logger.info(f"config_file: {config_file_path}")
        # logger.info(f"project_id: {project_id}")

    status: dict[str, dict[str, int]] = {}
    for sidecar in EM_EBSD_MTEX_MIME_TYPES_SIDECAR:
        if len(sidecar) == 2:
            status["_".join([typ[1:] for typ in sidecar])] = {"n": 0, "size": 0}
    for typ in EM_EBSD_MTEX_MIME_TYPES_SOLITARY:
        status[typ[1:]] = {"n": 0, "size": 0}

    with open(config_file_path) as fp:
        start = next(
            idx for idx, line in enumerate(fp) if CSV_HEADER_FOR_HASH_FILE in line
        )

    df_hash = pd.read_csv(config_file_path, sep=";", skiprows=start)
    df_hash.columns = ["path", "size", "mtime", "sha256"]

    # build dictionary of hashes to replace original file names with short and clean unique ones
    file_to_hash: dict[str, str] = {}
    for line in df_hash.itertuples(index=True):
        if line.path.count("/") >= 1:
            file_name = line.path.rsplit("/", 1)[1]
        else:
            file_name = line.path

        # filter out files that we do not wish to support
        if any(
            ignore in file_name for ignore in ["__MACOS", ".DS_Store"]
        ) or file_name.startswith("._"):
            continue
        # select files of likely target mime_type (likely cuz here only inspect ending, which is no guarantee though)
        if line.path.lower().endswith(tuple(EM_EBSD_MTEX_MIME_TYPES_SOLITARY)) or any(
            line.path.lower().endswith(sidecar)
            for sidecar in EM_EBSD_MTEX_MIME_TYPES_SIDECAR
        ):
            file_to_hash[line.path] = line.sha256  # type: ignore
            # no duplicates possible inside any individual (sub)directory, irrespective if compressed or not, for each project

    # ignore duplicates for NOMAD as for the example we do not wish to store copies
    # duplicates can be sitting in different subdirectories across a project
    hash_to_file: dict[str, str] = {}
    for (
        name,
        hash,
    ) in file_to_hash.items():  # TODO sorting lexicographically automatically?
        if hash not in hash_to_file:
            hash_to_file[hash] = name

    # generate a list of files to finally consider, compose target filenames with hashes
    decompressed: dict[str, str] = {}  # src file as key, trg file name as value
    for hash, name in hash_to_file.items():
        typ = name.rsplit(".", 1)[1].lower()
        if f".{typ}" in EM_EBSD_MTEX_MIME_TYPES_SOLITARY:
            decompressed[name] = f"{trg_directory}{os.sep}{project_id}.{hash}.{typ}"
            status[typ]["n"] += 1
            continue
        for sidecar in EM_EBSD_MTEX_MIME_TYPES_SIDECAR:
            if (
                f".{typ}" == sidecar[0]
            ):  # first value is typ of the master file, avoid registering twice
                if name.count(os.sep) > 0:
                    tokenize: list[str] = name.rsplit(os.sep, 1)
                    # check if a sidecar file with the same filename in the same directory exists but mind that
                    # Windows, Linux, and MacOS used across legacy datasets so mime type ending can be upper or lower case!
                    prefix = f"{tokenize[0]}{os.sep}{tokenize[1].rsplit('.')[0]}"
                elif name.count(":") == 1:
                    prefix = name.rsplit(":", 1)[1]
                else:
                    prefix = name

                for case in [
                    f"{prefix}{sidecar[1].lower()}",
                    f"{prefix}{sidecar[1].upper()}",
                ]:
                    if case in file_to_hash:
                        # register master and its sidecar, will not register twice
                        # cuz of above conditional filtering on sidecar[0]
                        decompressed[
                            f"{src_directory}{os.sep}{project_id}{os.sep}{name}"
                        ] = f"{trg_directory}{os.sep}{project_id}.{hash}.{file_to_hash[case]}{sidecar[0]}"
                        decompressed[
                            f"{src_directory}{os.sep}{project_id}{os.sep}{case}"
                        ] = f"{trg_directory}{os.sep}{project_id}.{hash}.{file_to_hash[case]}{sidecar[1]}"
                        status["_".join([val[1:] for val in sidecar])]["n"] += 1
                        break
                break

    archive_handlers = {
        get_file_from_zip: (".zip", ".eln"),
        get_file_from_tar: (".tar", ".tar.gz", ".tar.bz2", ".tar.xz"),
        get_file_from_rar: (".rar"),
        get_file_from_sevenzip: (".7z"),
    }

    if not write:
        if report:
            for src, trg in decompressed.items():
                logger.info(f"{src} > {trg}")
    else:
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
                                logger.info(f"{src} > {trg}")
                            else:
                                logger.error(f"{src} > {trg}")
                        break  # stop checking other handlers once matched
            else:
                try:
                    return_value: str = shutil.copy2(src, trg)
                    if report:
                        if return_value == trg:
                            logger.info(f"{src} > {trg}")
                        else:
                            logger.error(f"{src} > {trg}")
                except OSError:
                    logger.error(f"{src} > {trg}")

    return status


"""
        trg_file_name = f"{row.project_name}.{row_idx}.{col_idx}.{file_to_hash[value]}.{value[value.rfind('.') + 1 :].lower()}"

del spread_sheet_for_project

unpack_instructions = {}
stats = {}
store = {}
for mime_type in mime_type_list:
    unpack_instructions[mime_type] = [
        "use;atomtypes_hint;main_file_data_original_path;main_file_data_hashed;main_file_meta_original_path;main_file_meta_hashed;main_file_data_byte_size;main_file_meta_byte_size"
    ]
    stats[mime_type] = 0
    store[mime_type] = 0

for hsh, fnm in hash_to_file_name.items():
    pid = re.match(r"^\\/[0-9]{3}", fnm)
    # if not fnm.startswith("/340"):
    #    continue
    if pid:
        project_id = pid.group()[1:4]
        lower_case = fnm.lower()
        if lower_case.endswith(".ctf"):
            unpack_instructions["ctf"].append(
                f"1;;{fnm};{target_directory}/mtex/{project_id}.{hsh}.ctf;;;{hash_to_byte_size[hsh]};"
            )
            stats["ctf"] += 1
            store["ctf"] += hash_to_byte_size[hsh]
        elif lower_case.endswith(".ang"):
            unpack_instructions["ang"].append(
                f"1;;{fnm};{target_directory}/mtex/{project_id}.{hsh}.ang;;;{hash_to_byte_size[hsh]};"
            )
            stats["ang"] += 1
            store["ang"] += hash_to_byte_size[hsh]
        elif lower_case.endswith(".osc"):
            unpack_instructions["osc"].append(
                f"1;;{fnm};{target_directory}/mtex/{project_id}.{hsh}.osc;;;{hash_to_byte_size[hsh]};"
            )
            stats["osc"] += 1
            store["osc"] += hash_to_byte_size[hsh]
        elif lower_case.endswith(".crc"):
            # cpr and crc needs to come as a pair in the same directory with the same filename splitting metadata and data
            path_prefix = fnm[0 : fnm.rfind(".")]
            path_for_crc = fnm
            path_for_cpr = ""
            if fnm.endswith(".crc"):  # require consistent capitalization of cpr sidecar
                path_for_cpr = f"{path_prefix}.cpr"
            elif fnm.endswith(".CPR"):
                path_for_cpr = f"{path_prefix}.CPR"
            if (path_for_crc in file_name_to_hash) and (
                path_for_cpr in file_name_to_hash
            ):
                hsh_crc = file_name_to_hash[path_for_crc]
                hsh_cpr = file_name_to_hash[path_for_cpr]
                instruction = (
                    f"1;;{path_for_crc};{target_directory}/mtex/{project_id}.{hsh_crc}.{hsh_cpr}.crc;"
                    f"{path_for_cpr};{target_directory}/mtex/{project_id}.{hsh_crc}.{hsh_cpr}.cpr;"
                    f"{hash_to_byte_size[hsh_crc]};{hash_to_byte_size[hsh_cpr]}"
                )
                unpack_instructions["crc"].append(instruction)
                stats["crc"] += 1
                store["crc"] += hash_to_byte_size[hsh_crc] + hash_to_byte_size[hsh_cpr]
                del (
                    path_prefix,
                    path_for_cpr,
                    path_for_crc,
                    hsh_cpr,
                    hsh_crc,
                    instruction,
                )
        elif lower_case.endswith((".tif", ".tiff")):
            path_prefix = fnm[0 : fnm.rfind(".")]
            instruction = ""
            path_for_tif = fnm
            path_for_meta = ""
            mime_for_meta = ""
            if f"{path_prefix}.txt" in file_name_to_hash:  # JEOL and Hitachi sidecar
                path_for_meta = f"{path_prefix}.txt"
                mime_for_meta = "txt"
            elif f"{path_prefix}.TXT" in file_name_to_hash:
                path_for_meta = f"{path_prefix}.TXT"
                mime_for_meta = "TXT"
            elif f"{path_prefix}-tif.hdr" in file_name_to_hash:  # TESCAN sidecar
                path_for_meta = f"{path_prefix}-tif.hdr"
                mime_for_meta = "hdr"
            elif f"{path_prefix}-tif.HDR" in file_name_to_hash:
                path_for_meta = f"{path_prefix}-tif.hdr"
                mime_for_meta = "HDR"
            # print(f"{path_prefix}\n\t{path_for_tif}\n\t{path_for_meta}\n\t{mime_for_meta}")
            if path_for_tif in file_name_to_hash:
                storage = 0
                instruction = f"0;;{path_for_tif};{target_directory}/tiff/{project_id}.{file_name_to_hash[path_for_tif]}.tiff;;;{hash_to_byte_size[file_name_to_hash[path_for_tif]]};"
                storage += hash_to_byte_size[file_name_to_hash[path_for_tif]]
                if (path_for_meta != "") and (path_for_meta in file_name_to_hash):
                    # print(f"{path_for_tif}\n\t{path_for_meta}")
                    instruction = (
                        f"0;;{path_for_tif};{target_directory}/tiff/{project_id}.{file_name_to_hash[path_for_tif]}.{file_name_to_hash[path_for_meta]}.tiff;"
                        f"{path_for_meta};{target_directory}/tiff/{project_id}.{file_name_to_hash[path_for_tif]}.{file_name_to_hash[path_for_meta]}.{mime_for_meta};"
                        f"{hash_to_byte_size[file_name_to_hash[path_for_tif]]};{hash_to_byte_size[file_name_to_hash[path_for_meta]]}"
                    )
                    storage += hash_to_byte_size[file_name_to_hash[path_for_meta]]
            if instruction != "":
                unpack_instructions["tif"].append(instruction)
                stats["tif"] += 1
                store["tif"] += storage
            del (
                path_prefix,
                path_for_tif,
                path_for_meta,
                mime_for_meta,
                instruction,
                storage,
            )
        elif lower_case.endswith(".h5oina"):
            unpack_instructions["oina"].append(
                f"1;;{fnm};{target_directory}/hspy/{project_id}.{hsh}.h5oina;;;{hash_to_byte_size[hsh]};"
            )
            stats["oina"] += 1
            store["oina"] += hash_to_byte_size[hsh]
        elif lower_case.endswith(".edaxh5"):
            unpack_instructions["edax"].append(
                f"1;;{fnm};{target_directory}/hspy/{project_id}.{hsh}.edaxh5;;;{hash_to_byte_size[hsh]};"
            )
            stats["edax"] += 1
            store["edax"] += hash_to_byte_size[hsh]
        elif lower_case.endswith(".oh5"):
            unpack_instructions["edax"].append(
                f"1;;{fnm};{target_directory}/hspy/{project_id}.{hsh}.oh5;;;{hash_to_byte_size[hsh]};"
            )
            stats["edax"] += 1
            store["edax"] += hash_to_byte_size[hsh]
        elif lower_case.endswith((".h5", ".hdf5", ".hdf")):
            unpack_instructions["hdf"].append(
                f"0;;{fnm};{target_directory}/hspy/{project_id}.{hsh}.h5;;;{hash_to_byte_size[hsh]};"
            )
            stats["hdf"] += 1
            store["hdf"] += hash_to_byte_size[hsh]
        elif lower_case.endswith(".emd"):
            unpack_instructions["emd"].append(
                f"1;;{fnm};{target_directory}/hspy/{project_id}.{hsh}.emd;;;{hash_to_byte_size[hsh]};"
            )
            stats["emd"] += 1
            store["emd"] += hash_to_byte_size[hsh]
        elif lower_case.endswith(".dm3"):
            unpack_instructions["gatan"].append(
                f"1;;{fnm};{target_directory}/hspy/{project_id}.{hsh}.dm3;;;{hash_to_byte_size[hsh]};"
            )
            stats["gatan"] += 1
            store["gatan"] += hash_to_byte_size[hsh]
        elif lower_case.endswith(".dm4"):
            unpack_instructions["gatan"].append(
                f"1;;{fnm};{target_directory}/hspy/{project_id}.{hsh}.dm4;;;{hash_to_byte_size[hsh]};"
            )
            stats["gatan"] += 1
            store["gatan"] += hash_to_byte_size[hsh]
        elif lower_case.endswith(".dm5"):
            unpack_instructions["gatan"].append(
                f"1;;{fnm};{target_directory}/hspy/{project_id}.{hsh}.dm5;;;{hash_to_byte_size[hsh]};"
            )
            stats["gatan"] += 1
            store["gatan"] += hash_to_byte_size[hsh]
        elif lower_case.endswith(".bcf"):
            # proprietary file with possibly unclear content wont be handled
            stats["bcf"] += 1
        del project_id, lower_case
    del pid
print(stats)
blacklist = ["ctf", "ang", "osc", "crc", "oina", "tif", "hdf", "emd", "gatan", "bcf"]
for mime_type in mime_type_list:
    if mime_type not in blacklist:
        if len(unpack_instructions[mime_type]) > 0:
            print(f"Writing unpack_instructions for {mime_type}...")
            with open(f"harvest.examples.10.em.{mime_type}.unpack.csv", "w") as fp:
                fp.write("\n".join(unpack_instructions[mime_type]))
for key, val in store.items():
    print(f"{key}: {float(val) / float(1024**3)} GiB")
"""
