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
"""Parser mapping content of specific image files on NeXus."""


class NxEmImagesParser:
    """Map content from different type of image files on an instance of NXem."""

    def __init__(self, file_path: str = "", entry_id: int = 1, verbose: bool = False):
        """Overwrite constructor of the generic reader."""
        self.file_path = file_path
        if entry_id > 0:
            self.entry_id = entry_id
        else:
            self.entry_id = 1
        self.verbose = verbose
        self.cache = {"is_filled": False}
