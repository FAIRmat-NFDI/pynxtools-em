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
"""Utilities for working with NeXus concepts encoded as Python dicts in the concepts dir."""

from datetime import datetime
import pytz
import flatdict as fd
import numpy as np

from pynxtools_em.utils.string_conversions import string_to_number


def load_from_modifier(terms, fd_dct):
    """Implement modifier which reads values of different type from fd_dct."""
    if isinstance(terms, str):
        if terms in fd_dct.keys():
            return fd_dct[terms]
    if all(isinstance(entry, str) for entry in terms) is True:
        if isinstance(terms, list):
            lst = []
            for entry in terms:
                lst.append(fd_dct[entry])
            return lst
    return None


def convert_iso8601_modifier(terms, dct: dict):
    """Implement modifier which transforms nionswift time stamps to proper UTC ISO8601."""
    if terms is not None:
        if isinstance(terms, str):
            if terms in dct.keys():
                return None
        elif (
            (isinstance(terms, list))
            and (len(terms) == 2)
            and (all(isinstance(entry, str) for entry in terms) is True)
        ):
            # assume the first argument is a local time
            # assume the second argument is a timezone string
            if terms[0] in dct.keys() and terms[1] in dct.keys():
                # handle the case that these times can be arbitrarily formatted
                # for now we let ourselves be guided
                # by how time stamps are returned in Christoph Koch's
                # nionswift instances also formatting-wise
                date_time_str = dct[terms[0]].replace("T", " ")
                time_zone_str = dct[terms[1]]
                if time_zone_str in pytz.all_timezones:
                    date_time_obj = datetime.strptime(
                        date_time_str, "%Y-%m-%d %H:%M:%S.%f"
                    )
                    utc_time_zone_aware = pytz.timezone(time_zone_str).localize(
                        date_time_obj
                    )
                    return utc_time_zone_aware
                else:
                    raise ValueError("Invalid timezone string!")
                return None
        else:
            return None
    return None


def apply_modifier(modifier, dct: dict):
    """Interpret a functional mapping using data from dct via calling modifiers."""
    if isinstance(modifier, dict):
        # different commands are available
        if set(["fun", "terms"]) == set(modifier.keys()):
            if modifier["fun"] == "load_from":
                return load_from_modifier(modifier["terms"], dct)
            if modifier["fun"] == "convert_iso8601":
                return convert_iso8601_modifier(modifier["terms"], dct)
        else:
            print(f"WARNING::Modifier {modifier} is currently not implemented !")
            # elif set(["link"]) == set(modifier.keys())
            # with the jsonmap reader Sherjeel conceptualized "link"
            return None
    if isinstance(modifier, str):
        return modifier
    return None


def variadic_path_to_specific_path(path: str, instance_identifier: list):
    """Transforms a variadic path to an actual path with instances."""
    if (path is not None) and (path != ""):
        narguments = path.count("*")
        if narguments == 0:  # path is not variadic
            return path
        if len(instance_identifier) >= narguments:
            tmp = path.split("*")
            if len(tmp) == narguments + 1:
                nx_specific_path = ""
                for idx in range(0, narguments):
                    nx_specific_path += f"{tmp[idx]}{instance_identifier[idx]}"
                    idx += 1
                nx_specific_path += f"{tmp[-1]}"
                return nx_specific_path
    return None


def add_specific_metadata(
    concept_mapping: dict, orgmeta: fd.FlatDict, identifier: list, template: dict
) -> dict:
    """Map specific concept src on specific NeXus concept trg.

    concept_mapping: translation dict how trg and src are to be mapped
    orgmeta: instance data of src concepts
    identifier: list of identifier to resolve variadic paths
    template: instance data resulting from a resolved src to trg concept mapping
    """
    if "prefix_trg" in concept_mapping:
        variadic_prefix_trg = concept_mapping["prefix_trg"]
    elif "prefix" in concept_mapping:
        variadic_prefix_trg = concept_mapping["prefix"]
    else:
        raise KeyError(f"Neither prefix nor prefix_trg found in concept_mapping!")

    if "prefix_src" in concept_mapping:
        prefix_src = concept_mapping["prefix_src"]
    else:
        prefix_src = ""

    # process all mapping functors
    # (in graphical programming these are also referred to as filters or nodes), i.e.
    # an agent that gets some input does some (maybe abstract mapping) and returns an output
    # as the mapping can be abstract we call it functor
    if "use" in concept_mapping:
        for entry in concept_mapping["use"]:
            if isinstance(entry, tuple):
                trg = variadic_path_to_specific_path(
                    f"{variadic_prefix_trg}/{entry[0]}", identifier
                )
                template[f"{trg}"] = entry[1]
    if "load" in concept_mapping:
        for entry in concept_mapping["load"]:
            if isinstance(entry, tuple):
                if f"{prefix_src}{entry[1]}" not in orgmeta:
                    continue
                trg = variadic_path_to_specific_path(
                    f"{variadic_prefix_trg}/{entry[0]}", identifier
                )
                template[f"{trg}"] = orgmeta[f"{prefix_src}{entry[1]}"]
    if "load_and_multiply" in concept_mapping:
        for entry in concept_mapping["load_and_multiply"]:
            if isinstance(entry, tuple) and len(entry) == 3:
                if isinstance(entry[1], str) and isinstance(entry[2], float):
                    if f"{prefix_src}{entry[1]}" not in orgmeta:
                        continue
                    trg = variadic_path_to_specific_path(
                        f"{variadic_prefix_trg}/{entry[0]}", identifier
                    )
                    # Velox stores BeamConvergence but is this the full angle or the half i.e. semi angle?
                    # if entry[2] == 1. we assume BeamConvergence is the semi_convergence_angle
                    template[f"{trg}"] = entry[2] * orgmeta[f"{prefix_src}{entry[1]}"]
    if "map_to_real" in concept_mapping:
        for entry in concept_mapping["map_to_real"]:
            if isinstance(entry, tuple):
                if isinstance(entry[1], str):
                    if f"{prefix_src}{entry[1]}" not in orgmeta:
                        continue
                    trg = variadic_path_to_specific_path(
                        f"{variadic_prefix_trg}/{entry[0]}", identifier
                    )
                    # rosettasciio stores most Velox original metadata as string
                    # but this is incorrect for numerical values if stored as string
                    # here that would at the latest throw in the dataconverter
                    # validation
                    template[f"{trg}"] = string_to_number(
                        orgmeta[f"{prefix_src}{entry[1]}"]
                    )
                elif isinstance(entry[1], list):
                    if not all(
                        (isinstance(value, str) and f"{prefix_src}{value}" in orgmeta)
                        for value in entry[1]
                    ):
                        continue
                    trg = variadic_path_to_specific_path(
                        f"{variadic_prefix_trg}/{entry[0]}", identifier
                    )
                    res = []
                    for value in entry[1]:
                        res.append(string_to_number(orgmeta[f"{prefix_src}{value}"]))
                    template[f"{trg}"] = np.asarray(res, np.float64)
    if "map_to_real_and_multiply" in concept_mapping:
        for entry in concept_mapping["map_to_real_and_multiply"]:
            if isinstance(entry, tuple) and len(entry) == 3:
                if isinstance(entry[1], str) and isinstance(entry[2], float):
                    if f"{prefix_src}{entry[1]}" not in orgmeta:
                        continue
                    trg = variadic_path_to_specific_path(
                        f"{variadic_prefix_trg}/{entry[0]}", identifier
                    )
                    # Velox stores BeamConvergence but is this the full angle or the half i.e. semi angle?
                    # if entry[2] == 1. we assume BeamConvergence is the semi_convergence_angle
                    template[f"{trg}"] = entry[2] * string_to_number(
                        orgmeta[f"{prefix_src}{entry[1]}"]
                    )
    if "map_to_real_and_join" in concept_mapping:
        for entry in concept_mapping["map_to_real_and_join"]:
            trg = variadic_path_to_specific_path(
                f"{variadic_prefix_trg}/{entry[0]}", identifier
            )
            if isinstance(entry[1], list):
                if not all(
                    (isinstance(value, str) and f"{prefix_src}{value}" in orgmeta)
                    for value in entry[1]
                ):
                    continue
                res = []
                for value in entry[1]:
                    res.append(string_to_number(orgmeta[f"{prefix_src}{value}"]))
                template[f"{trg}"] = np.asarray(res)
            # we may need to be more specific with the return datatype here
    if "unix_to_iso8601" in concept_mapping:
        for entry in concept_mapping["unix_to_iso8601"]:
            trg = variadic_path_to_specific_path(
                f"{variadic_prefix_trg}/{entry[0]}", identifier
            )
            if isinstance(entry[1], str):
                if f"{prefix_src}{entry[1]}" not in orgmeta:
                    continue
                template[f"{trg}"] = datetime.fromtimestamp(
                    int(orgmeta[f"{prefix_src}{entry[1]}"]), tz=pytz.timezone("UTC")
                ).isoformat()
                # TODO::is this really a UNIX timestamp, what about the timezone?
                # no E. Spiecker's example shows clearly these remain tz-naive timestamps
                # e.g. 1340_Camera_Ceta_440_kx.emd was collect 2024/04/05 in Erlangen
                # but shows GMT time zone which is incorrect, problem only unix timestamp
                # reported by Velox
                # but for the hyperspy relevant metadata rosettasciio identifies
                # General/date: 2024-04-05, General/time: 13:40:20, General/time_zone: CEST
                # needs clarification from scientists !
    if "join_str" in concept_mapping:
        for entry in concept_mapping["join_str"]:
            trg = variadic_path_to_specific_path(
                f"{variadic_prefix_trg}/{entry[0]}", identifier
            )
            if isinstance(entry[1], list):
                if not all(
                    (isinstance(value, str) and f"{prefix_src}{value}" in orgmeta)
                    for value in entry[1]
                ):
                    continue
                res = []
                for value in entry[1]:
                    res.append(orgmeta[f"{prefix_src}{value}"])
                template[f"{trg}"] = " ".join(res)
    return template
