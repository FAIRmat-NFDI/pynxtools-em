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

import re


def is_valid_doi(token: str) -> bool:
    pattern = r"^10\.\d{4,9}/[-._;()/:A-Z0-9]+$"
    return bool(re.match(pattern, token, re.IGNORECASE))


# print(is_valid_doi("10.5281/zenodo.11128117"))


def get_bibliographical_metadata(bib: dict, project_id: str) -> list[str]:
    """Get dataset and article citation_key for given project."""
    matching: dict[str, list[str]] = {
        "data": [],
        "paper": [],
    }
    for key in bib:
        for prefix, cls in [("D", "data"), ("A", "paper")]:
            if key.startswith(f"{prefix}{project_id}"):
                matching[cls].append(key)
    data_article: list[str] = ["", ""]
    # print(matching)
    for idx, cls, entry_type in [
        (0, "data", "an original dataset"),
        (1, "paper", "an original research article"),
    ]:
        if len(matching[cls]) == 0:
            print(
                f"{'ERROR' if cls == 'data' else 'WARNING'}, {project_id} has no reference for {entry_type}"
            )
            # print(f"@Misc{{D_{camel_case_project_name}}},\n  author={{}},\n note = {{personal communication}},\n year = {{2024}},\n}},")
        elif len(matching[cls]) > 1:
            print(f"WARNING, {project_id} has more than one reference for {entry_type}")
        else:
            data_article[idx] = matching[cls][0]
    return data_article
