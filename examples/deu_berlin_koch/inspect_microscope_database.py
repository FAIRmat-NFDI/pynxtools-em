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

"""Inspect a directory for all its files and folders."""

import os
import sys


def inspect_directory(root_path: str, prefix: str, write: bool = False) -> None:
    """Either recursively list all directories and files in root_path or summarize used file types."""

    if write:
        csv_directories: list[str] = []
        csv_files: list[str] = []
        for root, dirs, files in os.walk(root_path):
            for name in dirs:
                csv_directories.append(os.path.join(root, name))
            for name in files:
                csv_files.append(os.path.join(root, name))

            with open(f"{prefix}.directories.csv", "w") as fp:
                fp.write("\n".join(csv_directories))
            with open(f"{prefix}.files.csv", "w") as fp:
                fp.write("\n".join(csv_files))
    else:
        mime_types: dict[str, int] = {}  # file type ending as key, counts as value
        for root, dirs, files in os.walk(root_path):
            for name in files:
                token = os.path.join(root, name).rsplit(".", 1)
                if len(token) == 2:
                    # no .lower() on endings to inspect typical variants (".TIF", ".tif")
                    if token[1] in mime_types:
                        mime_types[token[1]] += 1
                    else:
                        mime_types[token[1]] = 1

        for mime_type, count in sorted(
            mime_types.items(), key=lambda x: x[1], reverse=True
        ):
            print(f"{mime_type}, {count}")


def main():
    # e.g. call via
    # `python3 inspect_microscope_database.py /microscope_data microscope_data`
    if len(sys.argv) > 1:
        root_path = sys.argv[1]
    else:
        root_path = "."

    if len(sys.argv) > 2:
        prefix = sys.argv[2]
    else:
        prefix = "inspect_microscope_database"

    inspect_directory(root_path, prefix)


if __name__ == "__main__":
    main()
