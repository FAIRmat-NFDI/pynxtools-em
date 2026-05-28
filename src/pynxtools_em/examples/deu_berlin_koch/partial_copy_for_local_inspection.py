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

"""Copy content for a local inspection."""

import os
import shutil
import sys


def partial_copy(root_path: str, target_path: str, write: bool = True) -> None:
    """Either recursively list all directories and files in root_path or summarize used file types."""
    if write:
        for root, dirs, files in os.walk(root_path):
            for name in files:
                path = os.path.join(root, name)
                if path.lower().endswith(".txt"):
                    # check if there is a matching main file (i.e. tif or bmp image)
                    prefix = f"{path.rsplit('.', 1)[0]}"
                    if os.path.isfile(f"{prefix}.bmp") or os.path.isfile(
                        f"{prefix}.tif"
                    ):
                        print(
                            f"{path};{target_path}{os.sep}{path.rsplit(os.sep, 1)[1]}"
                        )
                        shutil.copy2(
                            path, f"{target_path}{os.sep}{path.rsplit(os.sep, 1)[1]}"
                        )
                        continue


def main():
    # e.g. call via
    # `python3 partial_copy_for_local_inspection.py /microscope_data /mytarget`
    if len(sys.argv) > 2:
        root_path = sys.argv[1]
        target_path = sys.argv[2]
    else:
        return

    partial_copy(root_path, target_path)


if __name__ == "__main__":
    main()
