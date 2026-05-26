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


def inspect(root_path: str, output: str = f"in"):
    """Recursively list all directories and files in root_path."""
    csv = []
    for root, dirs, files in os.walk(root_path):
        for name in dirs + files:
            csv.append(name)
            # csv.append(os.path.join(root, name))

    with open(f"{output}.csv", "w") as fp:
        fp.write("\n".join(csv))


def main():
    if len(sys.argv) > 1:
        root = sys.argv[1]
    else:
        root = "."

    if len(sys.argv) > 2:
        name = sys.argv[2]
    else:
        name = "inspect_microscope_database"

    inspect(root, name)


if __name__ == "__main__":
    main()
