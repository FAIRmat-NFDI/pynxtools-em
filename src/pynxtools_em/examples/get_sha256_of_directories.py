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

"""Compute checksums of each file in a directory recurse common compressed files."""

import hashlib
import os
import tarfile
import zipfile
from datetime import datetime

import py7zr
import rarfile

# import blake3
from pynxtools_apm.utils.default_config import SEPARATOR

HASHING = True

from collections.abc import Mapping


def to_int(value: str | int | bytes | Mapping[str, str]) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, bytes):
        return int(value.decode())
    if isinstance(value, str):
        return int(value)
    raise TypeError(f"Cannot convert {value!r} to int")


def analyze_zip_file(
    fpath: str,
    results: list[str],
    issues: list[str],
    right_stripped: str = "",
    hashing: bool = HASHING,
):
    """Get metadata about zipfile and recursively compute SHA256 hash for each of its files."""
    byte_size = 0
    if fpath.lower().endswith((".zip", ".eln")):  # .eln, e.g., RO-Crate
        try:
            fpath_stripped = fpath.replace(right_stripped, "")
            with zipfile.ZipFile(fpath, "r") as zip_file_hdl:
                for member in zip_file_hdl.infolist():
                    line = f"{fpath_stripped}:{member.filename};{member.file_size};{datetime(*member.date_time).timestamp()}"
                    byte_size += int(member.file_size)
                    if hashing:
                        zh = hashlib.sha256()
                        with zip_file_hdl.open(member, "r") as zfp:
                            while True:
                                chunk = zfp.read(zh.block_size)
                                if not chunk:
                                    break
                                zh.update(chunk)
                            line += f";{zh.hexdigest()}"
                    results.append(line)
        except Exception as exception:
            issues.append(f"{fpath_stripped}{SEPARATOR}{exception}")


def analyze_tar_file(
    fpath: str,
    results: list[str],
    issues: list[str],
    right_stripped: str = "",
    hashing: bool = HASHING,
):
    """Get metadata about tarfile and recursively compute SHA256 hash for each of its files."""
    byte_size = 0
    if fpath.lower().endswith((".tar", ".tar.gz", ".tar.bz2", ".tar.xz")):
        try:
            fpath_stripped = fpath.replace(right_stripped, "")
            with tarfile.open(fpath, "r:*") as tar:
                for member in tar:
                    if member.isreg():
                        tfp = tar.extractfile(member.name)
                        info = member.get_info()
                        line = f"{fpath_stripped}:{member.name};{to_int(info['size'])};{to_int(info['mtime'])}"
                        byte_size += to_int(info["size"])
                        if hashing:
                            th = hashlib.sha256()
                            while True:
                                chunk = tfp.read(th.block_size)
                                if not chunk:
                                    tfp.close()
                                    break
                                th.update(chunk)
                            line += f";{th.hexdigest()}"
                        results.append(line)
        except Exception as exception:
            issues += f"{fpath_stripped}{SEPARATOR}{exception}\n"


def analyze_file(
    fpath: str,
    results: list[str],
    issues: list[str],
    right_stripped: str = "",
    hashing: bool = HASHING,
):
    """Get metadata about file and compute its SHA256 hash."""
    byte_size = 0
    if os.path.isfile(fpath):
        fpath_stripped = fpath.replace(right_stripped, "")
        try:
            stat = os.stat(fpath)
            byte_size += int(stat.st_size)
            line = f"{fpath_stripped};{stat.st_size};{stat.st_mtime}"
            if hashing:
                fh = hashlib.sha256()
                with open(fpath, "rb") as ffp:
                    while True:
                        chunk = ffp.read(fh.block_size)
                        if not chunk:
                            break
                        fh.update(chunk)
                line += f";{fh.hexdigest()}"
            results.append(line)
        except Exception as exception:
            issues.append(f"{fpath_stripped}{SEPARATOR}{exception}")


def analyze_rar_file(
    fpath: str,
    results: list[str],
    issues: list[str],
    right_stripped: str = "",
    hashing: bool = HASHING,
):
    """Get metadata about rarfile and recursively compute SHA256 hash for each of its files."""
    byte_size = 0
    if fpath.lower().endswith(".rar"):
        try:
            fpath_stripped = fpath.replace(right_stripped, "")
            with rarfile.RarFile(fpath, "r") as rar_file_hdl:
                for member in rar_file_hdl.infolist():
                    line = f"{fpath_stripped}:{member.filename};{member.file_size};{datetime(*member.date_time).timestamp()}"
                    byte_size += int(member.file_size)
                    if hashing:
                        rh = hashlib.sha256()
                        with rar_file_hdl.open(member, "r") as rfp:
                            while True:
                                chunk = rfp.read(rh.block_size)
                                if not chunk:
                                    break
                                rh.update(chunk)
                            line += f";{rh.hexdigest()}"
                    results.append(line)
        except Exception as exception:
            issues.append(f"{fpath_stripped}{SEPARATOR}{exception}")


def analyze_sevenzip_file(
    fpath: str,
    results: list[str],
    issues: list[str],
    right_stripped: str = "",
    hashing: bool = HASHING,
):
    """Get metadata about 7z file and recursively compute SHA256 hash for each of its files."""
    byte_size = 0
    if fpath.lower().endswith(".7z"):
        try:
            fpath_stripped = fpath.replace(right_stripped, "")
            with py7zr.SevenZipFile(fpath, "r") as seven_file_hdl:
                mdata: dict[str, dict[str, str | int]] = {}
                for obj in seven_file_hdl.list():
                    if obj.uncompressed > 0:  # no bookkeeping of directories in that 7z
                        key = obj.filename
                        if key not in mdata:
                            mdata[key] = {}
                            mdata[key]["mtime"] = f"{obj.creationtime}".replace(
                                " ", "T"
                            )
                            # = datetime.datetime(*obj.creationtime).timestamp()
                            mdata[key]["size"] = obj.uncompressed
                if hashing:
                    for key, bio in seven_file_hdl.readall().items():
                        if key in mdata:
                            sh = hashlib.sha256(bio.getbuffer())
                            # bio.getbuffer().nbytes is equivalent to obj.uncompressed
                            mdata[key]["sha256"] = sh.hexdigest()
                        else:
                            issues.append(
                                f"{fpath_stripped}{SEPARATOR}KeyError {key} not found"
                            )
                    for key in mdata:
                        results.append(
                            f"{fpath_stripped}:{key};{mdata[key]['size']};{mdata[key]['mtime']};{mdata[key]['sha256']}"
                        )
                        byte_size += int(mdata[key]["size"])
                else:
                    for key in mdata:
                        results.append(
                            f"{fpath_stripped}:{key};{mdata[key]['size']};{mdata[key]['mtime']}"
                        )
                        byte_size += int(mdata[key]["size"])
        except Exception as exception:
            issues.append(f"{fpath_stripped}{SEPARATOR}{exception}")
