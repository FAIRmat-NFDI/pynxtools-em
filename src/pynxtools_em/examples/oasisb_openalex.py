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

import json
import os

import requests
from requests.exceptions import HTTPError

from pynxtools_em.examples.oasisb_bibliography import is_valid_doi


def get_data_for_doi_from_openalex(bib: dict, bib_keys: str) -> int:
    """Query OpenAlex for a data source and article (if the latter is available) expect data source to exist always."""
    n_queries: int = 0
    print(bib_keys)
    for idx, typ in enumerate([("D", "data"), ("A", "paper")]):
        prefix, cls = typ
        if bib_keys[idx] in bib:
            if "doi" in bib[bib_keys[idx]]:
                if is_valid_doi(bib[bib_keys[idx]]["doi"]):
                    os.makedirs("openalex", exist_ok=True)

                    file_path = f"openalex{os.sep}{bib_keys[idx]}.json"
                    if not os.path.isfile(file_path):
                        url = f"https://api.openalex.org/works/https://doi.org/{bib[bib_keys[idx]]['doi']}"

                        try:
                            response = requests.get(url, timeout=30)
                            response.raise_for_status()
                            n_queries += 1
                        except HTTPError as http_err:
                            print(f"ERROR::HTTP error occurred: {http_err}")
                            continue

                        data = response.json()

                        with open(file_path, "w", encoding="utf-8") as fp:
                            json.dump(data, fp, indent=4, ensure_ascii=False)
                        print(f"{file_path} written")
                    # else:
                    #     print(f"INFO::{file_path} already exists")
                else:
                    print(f"WARNING::{bib_keys[idx]} has an invalid DOI")
            else:
                print(f"WARNING::{bib_keys[idx]} has no DOI")
        # else:
        #     print(f"INFO::{bib_keys[idx]} not in the bibliography")
    return n_queries


# get_data_for_doi_from_openalex(bib, get_bibliographical_metadata(bib, get_project_id("1")))
