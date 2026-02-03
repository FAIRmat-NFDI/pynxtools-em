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

import re
from operator import itemgetter

import numpy as np

from pynxtools_em.utils.custom_logging import logger
from pynxtools_em.utils.natural_sorting import natural_key


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
        # find keys_of_priority for interesting default plots with some priority
        # priority ipf map > roi overview > eds map > spectra > complex image > real image
        keys_of_priority: dict[int, list[str]] = {}
        priorities = [1, 2, 3, 4, 5]
        for priority in priorities:
            keys_of_priority[priority] = []

        # images, 1
        image_pattern = re.compile(
            r"("
            r"/ENTRY\[entry([1-9]\d*)\].*/"
            r"(?:"
            r"imageID\[image([1-9]\d*)\]/image_[0-3]d"
            r"|"
            r"imageID\[image([1-9]\d*)\]/stack_[0-3]d"
            r"))"
        )
        keys_of_priority[1] = list(
            sorted(
                {
                    match.group(1)
                    for key in template
                    for match in image_pattern.finditer(key)
                },
                key=natural_key,
            )
        )
        del image_pattern

        # spectra, 2
        spectrum_pattern = re.compile(
            r"("
            r"/ENTRY\[entry([1-9]\d*)\].*/"
            r"(?:"
            r"spectrumID\[spectrum([1-9]\d*)\]/spectrum_[0-3]d"
            r"|"
            r"spectrumID\[spectrum([1-9]\d*)\]/stack_[0-3]d"
            r"))"
        )
        keys_of_priority[2] = list(
            sorted(
                {
                    match.group(1)
                    for key in template
                    for match in spectrum_pattern.finditer(key)
                },
                key=natural_key,
            )
        )
        del spectrum_pattern

        # eds, 3
        eds_pattern = re.compile(
            r"("
            r"/ENTRY\[entry([1-9]\d*)\]/roiID\[roi([1-9]\d*)\].*/"
            r"eds/indexing/ELEMENT_SPECIFIC_MAP\[[A-Za-z]{1,2}\]/image_2d"
            r")"
        )
        keys_of_priority[3] = list(
            sorted(
                {
                    match.group(1)
                    for key in template
                    for match in eds_pattern.finditer(key)
                },
                key=natural_key,
            )
        )
        del eds_pattern

        ebsd_pattern = re.compile(
            r"("
            r"/ENTRY\[entry([1-9]\d*)\]/roiID\[roi([1-9]\d*)\].*/ebsd/indexing"
            r")"
        )
        ebsd_keys = list(
            sorted(
                {
                    match.group(1)
                    for key in template
                    for match in ebsd_pattern.finditer(key)
                },
                key=natural_key,
            )
        )
        for ebsd_key in ebsd_keys:
            # ebsd, roi, 4
            if (
                f"{ebsd_key}/roi" in template
                and f"{ebsd_key}/roi" not in keys_of_priority[4]
            ):
                keys_of_priority[4].append(f"{ebsd_key}/roi")

            # ebsd, ipf 5
            if f"{ebsd_key}/number_of_scan_points" in template:
                n_scan_points_total = template[f"{ebsd_key}/number_of_scan_points"]

                # for that specific roi get all phase maps, rank by coverage of ipf
                # TODO
                phase_pattern = re.compile(
                    rf"("
                    rf"{re.escape(ebsd_key)}/"
                    rf"phaseID\[phase([1-9]\d*)\]"
                    rf")"
                )
                phase_keys = list(
                    sorted(
                        {
                            match.group(1)
                            for key in template
                            for match in phase_pattern.finditer(key)
                        },
                        key=natural_key,
                    )
                )
                vote_ipf_map: list[tuple[str, float]] = []
                for phase_key in phase_keys:
                    if f"{phase_key}/number_of_scan_points" in template and any(
                        f"{phase_key}/ipfID[ipf1]/map/{s}" in template
                        for s in ("data", "DATA[data]")
                    ):
                        n_scan_points = template[f"{phase_key}/number_of_scan_points"]
                        vote_ipf_map.append(
                            (
                                f"{phase_key}/ipfID[ipf1]/map",
                                float(n_scan_points) / float(n_scan_points_total),
                            )
                        )
                vote_ipf_map = sort_list_of_tuples_desc_order(vote_ipf_map)
                if len(vote_ipf_map) > 0:
                    if vote_ipf_map[0][0] not in keys_of_priority[5]:
                        keys_of_priority[5].append(vote_ipf_map[0][0])
                del phase_pattern, phase_keys
        del ebsd_pattern, ebsd_keys

        # TODO:one could think about more fine-grained priority voting, e.g. based on
        # image descriptors or shape of the data behind a key in template
        # but this will likely escalate into a discussion about personal preferences
        # and particularity details

        for priority in priorities:
            logger.info(
                f"{len(keys_of_priority[priority])} NXdata instances with priority {priority}"
            )

        has_default_plot = False
        for priority in priorities[::-1]:
            if len(keys_of_priority[priority]) > 0:
                self.decorate_path_to_default_plot(
                    template, keys_of_priority[priority][0]
                )
                logger.info(
                    f"Decorating {keys_of_priority[priority][0]} as the default plot for H5Web ..."
                )
                has_default_plot = True
                break

        if not has_default_plot:
            logger.warning("No default plot!")
        return template
