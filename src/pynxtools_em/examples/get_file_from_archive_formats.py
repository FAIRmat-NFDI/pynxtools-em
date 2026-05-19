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

"""Extract specific content from common compressed file formats."""

import os
import shutil
import tarfile
import zipfile
from pathlib import Path

import py7zr
import rarfile

BUFFER_SIZE = 1024 * 1024


def get_file_from_zip(
    zip_file_path: str,
    file_in_zip_path: str,
    target_directory: str,
    target_file_name: str,
) -> bool:
    try:
        target_dir = Path(target_directory)
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / target_file_name
        with zipfile.ZipFile(zip_file_path, "r") as zf:
            # target_file.write_bytes(zf.read(file_in_zip_path))
            with (
                zf.open(file_in_zip_path) as src,
                open(target_file, "wb", buffering=BUFFER_SIZE) as dst,
            ):
                shutil.copyfileobj(src, dst)
        return os.path.isfile(target_file)
    except (FileNotFoundError, KeyError, zipfile.BadZipFile) as exception:
        print(f"Error extracting file from zip: {exception}")
    return False


def get_file_from_tar(
    tar_file_path: str,
    file_in_tar_path: str,
    target_directory: str,
    target_file_name: str,
) -> bool:
    try:
        target_dir = Path(target_directory)
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / target_file_name
        with tarfile.open(tar_file_path, mode="r:*") as tf:
            member = tf.getmember(file_in_tar_path)
            if not member.isfile():
                raise ValueError(f"{file_in_tar_path} is not a regular file")
            with (
                tf.extractfile(member) as src,
                open(target_file, "wb", buffering=BUFFER_SIZE) as dst,
            ):
                shutil.copyfileobj(src, dst)
        return os.path.isfile(target_file)
    except (
        FileNotFoundError,  # tar file missing or target path invalid
        KeyError,  # member not found in archive
        tarfile.TarError,  # corrupt / unsupported tar
        ValueError,  # not a regular file
    ) as exception:
        print(f"Error extracting file from tar: {exception}")
    return False


def get_file_from_rar(
    rar_file_path: str,
    file_in_rar_path: str,
    target_directory: str,
    target_file_name: str,
) -> bool:
    try:
        target_dir = Path(target_directory)
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / target_file_name
        with rarfile.RarFile(rar_file_path) as rf:
            info = rf.getinfo(file_in_rar_path)
            if info.isdir():
                raise ValueError(f"{file_in_rar_path} is a directory")
            with (
                rf.open(info) as src,
                open(target_file, "wb", buffering=BUFFER_SIZE) as dst,
            ):
                shutil.copyfileobj(src, dst)
        return os.path.isfile(target_file)
    except (
        FileNotFoundError,
        KeyError,
        rarfile.Error,
        ValueError,
    ) as exception:
        print(f"Error extracting file from rar: {exception}")
    return False


def get_file_from_sevenzip(
    sevenz_file_path: str,
    file_in_sevenz_path: str,
    target_directory: str,
    target_file_name: str,
) -> bool:
    try:
        target_dir = Path(target_directory)
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / target_file_name
        with py7zr.SevenZipFile(sevenz_file_path, mode="r") as z:
            # get a file-like object for streaming
            with (
                z.open(file_in_sevenz_path) as src,
                open(target_file, "wb", buffering=BUFFER_SIZE) as dst,
            ):
                shutil.copyfileobj(src, dst)
        return os.path.isfile(target_file)
    except (
        FileNotFoundError,
        KeyError,
        py7zr.exceptions.Bad7zFile,
        py7zr.exceptions.PasswordRequired,
        py7zr.exceptions.UnsupportedCompressionMethodError,
        ValueError,
    ) as exception:
        print(f"Error extracting file from 7z: {exception}")
    return False
