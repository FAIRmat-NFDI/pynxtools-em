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

from operator import itemgetter
from typing import Dict

import numpy as np

from pynxtools_em.utils.custom_logging import logger


def sort_list_of_tuples_desc_order(tuples):
    """Sort the tuples by the second item using the itemgetter function."""
    return sorted(tuples, key=itemgetter(1), reverse=True)


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
                template[f"{trg}@default"] = f"{path[idx + 1][symbol_s + 1 : symbol_e]}"
                trg += f"{path[idx + 1]}/"
            else:
                template[f"{trg}@default"] = f"{path[idx + 1]}"
                trg += f"{path[idx + 1]}/"
        return template

    def priority_select(self, template: dict, entry_id: int = 1) -> dict:
        """Inspects all NXdata instances that could serve as default plots and picks one."""
        # find candidates for interesting default plots with some priority
        # priority ipf map > roi overview > spectra > complex image > real image
        # TODO: some of the here used idx_head, idx_tail string mangling could be
        # made likely better with using a regex
        candidates: Dict = {}
        priorities = [1, 2, 3, 4]
        for votes in priorities:
            candidates[votes] = []

        dtyp_vote = [
            ("imageID", "image", 1),
            ("imageID", "stack", 1),
            ("spectrumID", "spectrum", 2),
            ("spectrumID", "stack", 2),
        ]
        for key in template.keys():
            for tpl in dtyp_vote:
                for dimensionality in ["0d", "1d", "2d", "3d"]:
                    head = f"{tpl[0]}["
                    idx_head = key.find(head)
                    tail = f"]/{tpl[1]}_{dimensionality}"
                    idx_tail = key.find(tail)
                    if idx_head is not None and idx_tail is not None:
                        if 0 < idx_head < idx_tail:
                            keyword = f"{key[0 : idx_tail + len(tail)]}"
                            if keyword not in candidates[tpl[2]]:
                                candidates[tpl[2]].append(keyword)
                            break

            # find ebsd ipf map
            idx_head = key.find("/roiID[roi1]")
            idx_tail = key.find("/ebsd/indexing")
            if idx_head is None or idx_tail is None:
                continue
            if 0 < idx_head < idx_tail:
                n_scan_points_total = 1.0
                if (
                    f"{key[0 : idx_tail + len('/ebsd/indexing')]}/number_of_scan_points"
                    in template
                ):
                    n_scan_points_total = template[
                        f"{key[0 : idx_tail + len('/ebsd/indexing')]}/number_of_scan_points"
                    ]
                    # in case of ebsd map with phase2, phase3, ... find than phase with the
                    vote_ipf_map = []
                    for phase_id in np.arange(1, 20 + 1):
                        idx_tail = key.find(f"/ebsd/indexing/phaseID[phase{phase_id}]")
                        if idx_tail is None or idx_tail == -1:
                            continue
                        prfx = f"{key[0 : idx_tail + len(f'''/ebsd/indexing/phaseID[phase{phase_id}]''')]}"
                        # logger.debug(f"{key}\t{idx_head}\t{idx_tail}\t{prfx}")
                        if 0 < idx_head < idx_tail and (
                            f"{prfx}/ipfID[ipf1]/map/data" in template
                            or f"{prfx}/ipfID[ipf1]/map/DATA[data]" in template
                        ):
                            n_scan_points = 1.0
                            if f"{prfx}/number_of_scan_points" in template:
                                # n_scan_points = template[
                                #     f"{key[0:idx_tail + len(f'''/ebsd/indexing/phaseID[phase{phase_id}]''')]}/number_of_scan_points"
                                # ]
                                n_scan_points = template[
                                    f"{prfx}/number_of_scan_points"
                                ]
                            vote_ipf_map.append(
                                (
                                    f"{prfx}/ipfID[ipf1]/map",
                                    np.float64(n_scan_points)
                                    / np.float64(n_scan_points_total),
                                )
                            )
                    vote_ipf_map = sort_list_of_tuples_desc_order(vote_ipf_map)
                    if len(vote_ipf_map) > 0:
                        if vote_ipf_map[0][0] not in candidates[4]:
                            candidates[4].append(vote_ipf_map[0][0])

            # find ebsd roi map
            idx_tail = key.find("/ebsd/indexing/roi")
            if idx_head is not None and idx_tail is not None:
                if 0 < idx_head < idx_tail:
                    keyword = key[0 : idx_tail + len("/ebsd/indexing/roi")]
                    if keyword not in candidates[3]:
                        candidates[3].append(keyword)

        # TODO:one could think about more fine-grained priority voting, e.g. based on
        # image descriptors or shape of the data behind a key in template
        # but this will likely escalate into a discussion about personal preferences
        # and particularity details

        for votes in priorities:
            logger.info(
                f"{len(candidates[votes])} NXdata instances with priority {votes}"
            )

        has_default_plot = False
        for votes in priorities[::-1]:
            if len(candidates[votes]) > 0:
                self.decorate_path_to_default_plot(template, candidates[votes][0])
                logger.info(
                    f"Decorating {candidates[votes][0]} as the default plot for H5Web ..."
                )
                has_default_plot = True
                break

        if not has_default_plot:
            logger.warning("WARNING::No default plot!")
        return template
