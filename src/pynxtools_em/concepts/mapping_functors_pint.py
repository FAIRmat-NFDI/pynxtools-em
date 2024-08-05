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

import flatdict as fd
import numpy as np
import pytz
import pint
from pint import UnitRegistry
from typing import Any

from pynxtools_em.utils.get_file_checksum import get_sha256_of_file_content
from pynxtools_em.utils.interpret_boolean import try_interpret_as_boolean
from pynxtools_em.utils.string_conversions import rchop, string_to_number

UREG = UnitRegistry()
UREG.define('nx_unitless = 1')
UREG.define('nx_dimensionless = 1')
UREG.define('nx_any = 1')
NX_UNITLESS = pint.Quantity(1, UREG.nx_unitless)
NX_DIMENSIONLESS = pint.Quantity(1, UREG.nx_dimensionless)
NX_ANY = pint.Quantity(1, UREG.nx_any)


# best practice is use np.ndarray or np.generic as magnitude within that pint.Quantity!
MAP_TO_DTYPES = {
    "u1": np.uint8,
    "i1": np.int8,
    "u2": np.uint16,
    "i2": np.int16,
    "f2": np.float16,
    "u4": np.uint32,
    "i4": np.int32,
    "f4": np.float32,
    "u8": np.uint64,
    "i8": np.int64,
    "f8": np.float64,
    "bool": bool}

# general conversion workflow
# 1. Normalize src data to str, bool, or pint.Quantity
#    These pint.Quantities should use numpy scalar or array for the dtype of the magnitude.
#    Use special NeXus unit categories unitless, dimensionless, and any.
# 2. Map on specific trg path, pint.Unit, eventually with conversions, and dtype conversion
#    Later this could include endianness
# 3. Store pint.Quantity magnitude and if non-special also correctly converted @units
#    attribute


def var_path_to_spcfc_path(path: str, instance_identifier: list):
    """Transforms a variadic path to an actual path with instances."""
    if (path is not None) and (path != ""):
        nvariadic_parts = path.count("*")
        if nvariadic_parts == 0:  # path is not variadic
            return path
        if len(instance_identifier) >= nvariadic_parts:
            variadic_part = path.split("*")
            if len(variadic_part) == nvariadic_parts + 1:
                nx_specific_path = ""
                for idx in range(0, nvariadic_parts):
                    nx_specific_path += (
                        f"{variadic_part[idx]}{instance_identifier[idx]}"
                    )
                    idx += 1
                nx_specific_path += f"{variadic_part[-1]}"
                return nx_specific_path


def is_not_special_unit(units: pint.Unit) -> bool:
    """True if not a special NeXus unit category."""
    for special_units in [NX_UNITLESS.units, NX_DIMENSIONLESS.units, NX_ANY.units]:
        if units == special_units:
            return False
    return True


def get_case(arg):
    if isinstance(arg, str):  # str
        return "case_one"
    elif isinstance(arg, tuple):
        if len(arg) == 2:  # str, str | list
            if isinstance(arg[0], str):
                if isinstance(arg[1], str):
                    return "case_two_str"
                elif isinstance(arg[1], list):
                    return "case_two_list"
        elif len(arg) == 3:  # str, str | list, pint.Unit or str, pint.Unit, str | list
            if isinstance(arg[0], str):
                if isinstance(arg[1], pint.Unit):
                    if isinstance(arg[2], str):
                        return "case_three_str"
                    elif isinstance(arg[2], list):
                        return "case_three_list"
                elif (arg[2], pint.Unit):
                    if isinstance(arg[1], str):
                        return "case_four_str"
                    elif isinstance(arg[1], list):
                        return "case_four_list"
        elif len(arg) == 4:  # str, pint.Unit, str | list, pint.Unit
            if isinstance(arg[0], str) and isinstance(arg[1], pint.Unit) and isinstance(arg[3], pint.Unit):
                if isinstance(arg[2], str):
                    return "case_five_str"
                elif isinstance(arg[2], list):
                    return "case_five_list"


def set_value(template: dict, trg: str, src_val: Any, trg_dtype=None) -> dict:
    """Set value in the template using trg.

    src_val can be a single value, an array, or a pint.Quantity (scalar or array)
    """
    # np.issubdtype(np.uint32, np.signedinteger)
    if src_val:  # covering not None, not "", ...
        if not trg_dtype:  # go with existent dtype
            if isinstance(src_val, str):
                # TODO this is not rigorous need to check for null-term also and str arrays
                template[f"{trg}"] = src_val
                # assumes I/O to HDF5 will write specific encoding, typically variable, null-term, utf8
            elif isinstance(src_val, pint.Quantity):
                if isinstance(src_val.magnitude, (np.ndarray, np.generic)) or np.isscalar(src_val.magnitude):  # bool case typically not expected!
                    template[f"{trg}"] = src_val.magnitude
                    if is_not_special_unit(src_val.units):
                        template[f"{trg}/@units"] = src_val.units
                    print(f"WARNING::Assuming writing to HDF5 will auto-convert Python types to numpy type, trg {trg} !")
                else:
                    raise TypeError(f"pint.Quantity magnitude should use in-build, bool, or np !")
            elif isinstance(src_val, (np.ndarray, np.generic)) or np.isscalar(src_val) or isinstance(src_val, bool):
                template[f"{trg}"] = src_val
                # units may be required, need to be set explicitly elsewhere in the source code!
                print(f"WARNING::Assuming writing to HDF5 will auto-convert Python types to numpy type, trg: {trg} !")
            else:
                raise TypeError(f"Unexpected type {type(src_val)} found for not trg_dtype case !")
        else:  # do an explicit type conversion
            # e.g. in cases when tech partner writes float32 but e.g. NeXus assumes float64
            if isinstance(src_val, str):
                raise TypeError(f"Unexpected type str found when calling set_value, trg {trg} !")
            elif isinstance(src_val, pint.Quantity):
                if isinstance(src_val.magnitude, (np.ndarray, np.generic)):
                    template[f"{trg}"] = np.asarray(src_val.magnitude, MAP_TO_DTYPES[trg_dtype])
                    if is_not_special_unit(src_val.units):
                        template[f"{trg}/@units"] = src_val.units
                elif np.isscalar(src_val.magnitude):  # bool typically not expected
                    template[f"{trg}"] = MAP_TO_DTYPES[trg_dtype](src_val.magnitude)
                    if is_not_special_unit(src_val.units):
                        template[f"{trg}/@units"] = src_val.units
                else:
                    raise TypeError(f"Unexpected type for explicit src_val.magnitude, set_value, trg {trg} !")
            elif isinstance(src_val, (np.ndarray, np.generic)):
                template[f"{trg}"] = np.asarray(src_val, MAP_TO_DTYPES[trg_dtype])
                # units may be required, need to be set explicitly elsewhere in the source code!
                print(f"WARNING::Assuming I/O to HDF5 will auto-convert to numpy type, trg: {trg} !")
            elif np.isscalar(src_val):
                template[f"{trg}"] = MAP_TO_DTYPES[trg_dtype](src_val)
                print(f"WARNING::Assuming I/O to HDF5 will auto-convert to numpy type, trg: {trg} !")
            else:
                raise TypeError(f"Unexpected type for explicit type conversion, set_value, trg {trg} !")
    return template


def use_functor(cmds: list, mdata: fd.FlatDict, ids: list, template: dict) -> dict:
    """Process the use functor."""
    for cmd in cmds:
        if isinstance(cmd, tuple):
            if len(cmd) == 2:
                if isinstance(cmd[0], str):
                    if isinstance(cmd[1], str):  # str, str
                        trg = var_path_to_spcfc_path(f"{var_prefix_trg}/{cmd[0]}", ids)
                        set_value(template, trg, cmd[1])
                    elif isinstance(cmd[1], pint.Quantity):  # str, pint.Quantity
                        trg = var_path_to_spcfc_path(f"{var_prefix_trg}/{cmd[0]}", ids)
                        set_value(template, trg, cmd[1])
    return template


def map_functor(cmds: list, mdata: fd.FlatDict, ids: list, template: dict, **kwargs) -> dict:
    if "trg_dtype_key" in kwargs:
        trg_dtype = kwargs["trg_dtype"]
        # this will force the conversion of all instance data from src to match trg_dtype
    for cmd in cmds:
        case = get_case(cmd)
        if case == "case_one":  # str
            if f"{prefix_src}{cmd}" not in mdata:
                continue
            src_val = mdata[f"{prefix_src}{cmd}"]
            trg = var_path_to_spcfc_path(f"{var_prefix_trg}/{cmd}", ids)
            set_value(template, trg, src_val, trg_dtype)
        elif case == "case_two_str":  # str, str
            if f"{prefix_src}{cmd[1]}" not in mdata:
                continue
            src_val = mdata[f"{prefix_src}{cmd[1]}"]
            trg = var_path_to_spcfc_path(f"{var_prefix_trg}/{cmd[0]}", ids)
            set_value(template, trg, src_val)
        elif case == "case_two_list":
            # ignore empty list, all src paths str, all src_val have to exist of same type
            if len(cmd[1]) == 0:
                continue
            if not all(isinstance(val, str) for val in cmd[1])
                continue
            if not all(f"{prefix_src}{val}" in mdata for val in cmd[1]):
                continue
            src_values = [mdata[f"{prefix_src}{val}"] for val in cmd[1]]
            if len(src_values) == 0:
                continue
            if not all(type(val) == type(src_values[0]) for val in src_values):
                continue
            trg = var_path_to_spcfc_path(f"{var_prefix_trg}/{cmd[0]}", ids)
            set_value(template, trg, np.asarray(src_values))
        elif case == "case_three_str":  # str, pint.Unit, str
            if f"{prefix_src}{cmd[2]}" not in mdata:
                continue
            src_val = mdata[f"{prefix_src}{cmd[2]}"]
            trg = var_path_to_spcfc_path(f"{var_prefix_trg}/{cmd[0]}", ids)
            if isinstance(src_val, pint.Quantity):
                set_value(template, trg, src_val)
            else:
                set_value(template, trg, pint.Quantity(src_val, cmd[1].units))
        elif case == "case_three_list":  # str, pint.Unit, list
            if len(cmd[2]) == 0:
                continue
            if not all(isinstance(val, str) for val in cmd[2])
                continue
            if not all(f"{prefix_src}{val}" in mdata for val in cmd[2]):
                continue
            src_values = [mdata[f"{prefix_src}{val}"] for val in cmd[2]]
            if not all(type(val) == type(src_values[0]) for val in src_values):
                # need to check whether content are scalars also
                continue
            trg = var_path_to_spcfc_path(f"{var_prefix_trg}/{cmd[0]}", ids)
            if isinstance(src_values, pint.Quantity):
                set_value(template, trg, src_values)
            else:
                set_values(template, trg, pint.Quantity(src_values, cmd[1].units))
        elif case.startswith("case_four"):
            # both of these cases can be avoided in an implementation when the
            # src quantity is already a pint quantity instead of some
            # pure python or numpy value or array respectively
            print(f"WARNING::Ignoring case_four, instead refactor implementation such"
                    f"that values on the src side are pint.Quantities already!")
        elif case == "case_five_str":
            if f"{prefix_src}{cmd[2]}" not in mdata:
                continue
            src_val = mdata[f"{prefix_src}{cmd[2]}"]
            trg = var_path_to_spcfc_path(f"{var_prefix_trg}/{cmd[0]}", ids)
            if isinstance(src_val, pint.Quantity):
                set_value(template, trg, src_val.units.to(cmd[1]))
            else:
                pint_src = pint.Quantity(src_val, cmd[3])
                # pint_trg = pint_src.units.to(cmd[1])
                set_value(template, trg, pint_src.units.to(cmd[1]))
        elif case == "case_five_list":
            if len(cmd[2]) == 0:
                continue
            if not all(isinstance(val, str) for val in cmd[2])
                continue
            if not all(f"{prefix_src}{val}" in mdata for val in cmd[2]):
                continue
            src_values = [mdata[f"{prefix_src}{val}"] for val in cmd[2]]
            if isinstance(src_values[0], pint.Quantity):
                raise ValueError(f"Hit unimplemented case that src_val is pint.Quantity")
            if not all(type(val) == type(src_values[0]) for val in src_values):
            trg = var_path_to_spcfc_path(f"{var_prefix_trg}/{cmd[0]}", ids)
            if isinstance(src_values, pint.Quantity):
                set_value(template, trg, src_values.units.to(cmd[1]))
            else:
                pint_src = pint.Quantity(src_values, cmd[3])
                set_values(template, trg, pint_src.units.to(cmd[1]))

    # try_interpret_as_boolean(mdata[f"{prefix_src}{entry[1]}"])
    # string_to_number(mdata[f"{prefix_src}{entry[1]}"])
    return template


def timestamp_functor(cmds: list, mdata: fd.FlatDict, ids: list, template: dict) -> dict:
    for cmd in cmds:
        if isinstance(cmd, tuple):
            if 2 <= len(cmd) <= 3:  # trg, src, timestamp or empty string (meaning utc)
                if all(isinstance(elem, str) for elem in cmd):
                    if f"{prefix_src}{cmd[1]}" not in mdata:
                        continue
                    if mdata[f"{prefix_src}{cmd[1]}"] == "":
                        continue
                    tzone = "UTC"
                    if len(cmd) == 3:
                        tzone = cmd[2]
                    if tzone not in pytz.all_timezones:
                        raise ValueError(
                            f"{tzone} is not a timezone in pytz.all_timezones!"
                        )
                    var_path_to_spcfc_path
                    trg = var_path_to_spcfc_path(f"{var_prefix_trg}/{cmd[0]}", ids)
                    template[f"{trg}"] = datetime.fromtimestamp(
                        int(mdata[f"{prefix_src}{cmd[1]}"]),
                        tz=pytz.timezone(tzone),
                    ).isoformat()
    return template


def filehash_functor(cmds: list, mdata: fd.FlatDict, ids: list, template: dict) -> dict:
    for cmd in cmds:
        if isinstance(cmd, tuple):
            if len(cmd) == 2:
                if not all(isinstance(elem, str) for elem in cmd):
                    continue
                if f"{prefix_src}{cmd[1]}" not in mdata:
                    continue
                if mdata[f"{prefix_src}{cmd[1]}"] == "":
                    continue
                trg = var_path_to_spcfc_path(f"{var_prefix_trg}/{cmd[0]}", ids)
                with open(mdata[f"{prefix_src}{cmd[1]}"], "rb") as fp:
                    template[f"{rchop(trg, 'checksum')}checksum"] = (
                        get_sha256_of_file_content(fp)
                    )
                    template[f"{rchop(trg, 'checksum')}type"] = "file"
                    template[f"{rchop(trg, 'checksum')}path"] = mdata[
                        f"{prefix_src}{cmd[1]}"
                    ]
                    template[f"{rchop(trg, 'checksum')}algorithm"] = "sha256"
    return template


def add_specific_metadata_pint(
    cfg: dict, mdata: fd.FlatDict, ids: list, template: dict
) -> dict:
    """Map specific concept src on specific NeXus concept trg.

    cfg: a configuration dictionary from configurations/*.py mapping from src to trg
    mdata: instance data of src concepts
    ids: list of identifier to resolve variadic template paths to specific template paths
    template: dictionary where to store mapped instance data using template paths
    """
    if "prefix_trg" in cfg:
        var_prefix_trg = cfg["prefix_trg"]
    else:
        raise KeyError(f"prefix_trg not found in cfg!")
    if "prefix_src" in cfg:
        prefix_src = cfg["prefix_src"]
    else:
        raise KeyError(f"prefix_src not found in cfg!")

    # process all mapping functors
    # (in graphical programming these are also referred to as filters or nodes),
    # i.e. an agent that gets some input does something (e.g. abstract mapping) and
    # returns an output, given the mapping can be abstract, we call it a functor

    # https://numpy.org/doc/stable/reference/arrays.dtypes.html

    for functor_key in cfg:
        if functor_key == "use":
            use_functor(cfg["use"], mdata, ids, template)
        if functor_key == "map":
            map_functor(cfg[functor_key], mdata, ids, template)
        if functor_key.startswith("map_to_"):
            dtype_key = functor_key.replace("map_to_", "")
            print(f"dtype_key >>>> {dtype_key}")
            if dtype_key in MAP_TO_DTYPES:
                map_functor(cfg[functor_key],
                            mdata,
                            ids,
                            template,
                            trg_dtype_key=dtype_key)
            else:
                raise KeyError(f"Unexpected dtype_key {dtype_key} !")
        if functor_key == "unix_to_iso8601":
            timestamp_functor(cfg["unix_to_iso8601"], mdata, ids, template)
        if functor_key == "sha256":
            filehash_functor(cfg["sha256"], mdata, ids, template)
    return template


"use": [("str_str_01", ""),
        ("str_str_02", "one"),
        ("str_qnt_01", NX_UNITLESS),
        ("str_qnt_02", NX_DIMENSIONLESS),
        ("str_qnt_03", NX_ANY),
        ("str_qnt_04", pint.Quantity(1, ureg.meter)),
        ("str_qnt_05", pint.Quantity(1, ureg.nx_unitless)),
        ("str_qnt_06", pint.Quantity(1, ureg.nx_dimensionless)),
        ("str_qnt_07", pint.Quantity(1, ureg.nx_any)),
        ("str_qnt_08", pint.Quantity(np.uint32(1), ureg.meter)),
        ("str_qnt_09", pint.Quantity(np.uint32(1), ureg.nx_unitless)),
        ("str_qnt_10", pint.Quantity(np.uint32(1), ureg.nx_dimensionless)),
        ("str_qnt_11", pint.Quantity(np.uint32(1), ureg.nx_any)),
        ("str_qnt_12", pint.Quantity(np.asarray([1, 2, 3], np.uint32), ureg.meter))]