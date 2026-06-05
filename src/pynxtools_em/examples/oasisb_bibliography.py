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
import re

logger = logging.getLogger("pynxtools-em")


def is_valid_doi(token: str) -> bool:
    pattern = r"^10\.\d{4,9}/[-._;()/:A-Z0-9]+$"
    return bool(re.match(pattern, token, re.IGNORECASE))


def get_bibliographical_metadata(
    bib: dict, project_id: str, verbose: bool = False
) -> list[str]:
    """Get dataset and article citation_key for given project."""
    matching: dict[str, list[str]] = {
        "data": [],
        "paper": [],
    }
    for key in bib:
        for prefix, cls in [("D", "data"), ("A", "paper")]:
            if key.startswith(f"{prefix}{project_id}"):
                matching[cls].append(key)
    if verbose:
        for cls, matches in matching.items():
            logger.info(f"{cls}, {matches}")
    data_article: list[str] = ["", ""]
    for idx, cls, entry_type in [
        (0, "data", "an original dataset"),
        (1, "paper", "an original research article"),
    ]:
        if len(matching[cls]) == 0:
            if verbose:
                if cls == "data":
                    logger.error(f"{project_id} has no reference for {entry_type}")
                else:
                    logger.warning(f"{project_id} has no reference for {entry_type}")
        elif len(matching[cls]) > 1:
            logger.warning(f"{project_id} has more than one reference for {entry_type}")
        else:
            data_article[idx] = matching[cls][0]
    return data_article
