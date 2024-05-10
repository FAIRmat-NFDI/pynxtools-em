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
"""Logics and functionality to identify and annotate a default plot NXem."""

from typing import Dict

import numpy as np


class NxEmDefaultPlotResolver:
    """Annotate the default plot in an instance of NXem."""

    def __init__(self):
        pass

    def decorate_path_to_default_plot(self, template: dict, nxpath: str) -> dict:
        """Write @default attribute to point to the default plot."""
        # an example for nxpath
        # "/ENTRY[entry1]/atom_probe/ranging/mass_to_charge_distribution/mass_spectrum"
        if nxpath.count("/") == 0:
            return template
        path = nxpath.split("/")
        trg = "/"
        for idx in np.arange(0, len(path) - 1):
            symbol_s = path[idx + 1].find("[")
            symbol_e = path[idx + 1].find("]")
            if 0 <= symbol_s < symbol_e:
                template[f"{trg}@default"] = f"{path[idx + 1][symbol_s + 1:symbol_e]}"
                trg += f"{path[idx + 1][symbol_s + 1:symbol_e]}/"
            else:
                template[f"{trg}@default"] = f"{path[idx + 1]}"
                trg += f"{path[idx + 1]}/"
        return template

    def priority_select(self, template: dict, entry_id: int = 1) -> dict:
        """Inspects all NXdata instances that could serve as default plots and picks one."""
        # find candidates for interesting default plots with some priority
        # priority ipf map > roi overview > spectra > complex image > real image
        candidates: Dict = {}
        for votes in [1, 2, 3, 4, 5]:
            candidates[votes] = []

        dtyp_vote = [
            ("IMAGE_R_SET", "image", 1),
            ("IMAGE_C_SET", "image", 2),
            ("SPECTRUM_SET", "spectrum", 3),
        ]
        for key in template.keys():
            for tpl in dtyp_vote:
                for dimensionality in ["zerod", "oned", "twod", "threed"]:
                    head = f"{tpl[0]}["
                    idx_head = key.find(head)
                    tail = f"]/{tpl[1]}_{dimensionality}"
                    idx_tail = key.find(tail)
                    # TODO: better use a regex
                    if idx_head is not None and idx_tail is not None:
                        if 0 < idx_head < idx_tail:
                            keyword = f"{key[0:idx_tail + len(tail)]}"
                            if keyword not in candidates[tpl[2]]:
                                candidates[tpl[2]].append(keyword)
                            break

            # find ebsd ipf map
            idx_head = key.find("/ROI[")
            tail = "/ebsd/indexing/phaseID[phase1]/ipfID[ipf1]/map"
            idx_tail = key.find(tail)
            if idx_head is not None and idx_tail is not None:
                if 0 < idx_head < idx_tail:
                    keyword = key[0 : idx_tail + len(tail)]
                    if keyword not in candidates[5]:
                        candidates[5].append(keyword)
                    continue
            # find ebsd roi map
            tail = "/ebsd/indexing/roi"
            idx_tail = key.find(tail)
            if idx_head is not None and idx_tail is not None:
                if 0 < idx_head < idx_tail:
                    keyword = key[0 : idx_tail + len(tail)]
                    if keyword not in candidates[4]:
                        candidates[4].append(keyword)

        # one could think about more fine-grained priority voting, e.g. based on
        # image descriptors or shape of the data behind a key in template

        for votes in [1, 2, 3, 4, 5]:
            print(f"NXdata instances with priority {votes}:")
            for entry in candidates[votes]:
                print(entry)

        has_default_plot = False
        for votes in [5, 4, 3, 2, 1]:
            if len(candidates[votes]) > 0:
                self.decorate_path_to_default_plot(template, candidates[votes][0])
                print(
                    f"Decorating {candidates[votes][0]} as the default plot for H5Web ..."
                )
                has_default_plot = True
                break

        if not has_default_plot:
            print("WARNING::No default plot!")
        return template
