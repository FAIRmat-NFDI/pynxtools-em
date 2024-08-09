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
from typing import Any

import flatdict as fd
import numpy as np
import pytz
from pynxtools_em.utils.get_file_checksum import get_sha256_of_file_content
from pynxtools_em.utils.interpret_boolean import try_interpret_as_boolean
from pynxtools_em.utils.pint_custom_unit_registry import is_not_special_unit, ureg
from pynxtools_em.utils.string_conversions import rchop

# best practice is use np.ndarray or np.generic as magnitude within that ureg.Quantity!
MAP_TO_DTYPES = {
    "u1": np.uint8,
    "i1": np.int8,
    "u2": np.uint16,
    "i2": np.int16,
    # "f2": np.float16, not supported yet with all HDF5 h5py versions
    "u4": np.uint32,
    "i4": np.int32,
    "f4": np.float32,
    "u8": np.uint64,
    "i8": np.int64,
    "f8": np.float64,
    "bool": bool,
}

# general conversion workflow
# 1. Normalize src data to str, bool, or ureg.Quantity
#    These ureg.Quantities should use numpy scalar or array for the dtype of the magnitude.
#    Use special NeXus unit categories unitless, dimensionless, and any.
# 2. Map on specific trg path, ureg.Unit, eventually with conversions, and dtype conversion
#    Later this could include endianness
# 3. Store ureg.Quantity magnitude and if non-special also correctly converted @units
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
        elif len(arg) == 3:  # str, str | list, ureg.Unit or str, ureg.Unit, str | list
            if isinstance(arg[0], str):
                if isinstance(arg[1], ureg.Unit):
                    if isinstance(arg[2], str):
                        return "case_three_str"
                    elif isinstance(arg[2], list):
                        return "case_three_list"
                elif (arg[2], ureg.Unit):
                    if isinstance(arg[1], str):
                        return "case_four_str"
                    elif isinstance(arg[1], list):
                        return "case_four_list"
        elif len(arg) == 4:
            # str, ureg.Unit, str | list, ureg.Unit
            # str, ureg.Unit, str, str
            # last string points to unit string for situations where e.g. tech partner
            # report HV/value, HV/Unit and these two pieces of information should be
            # fused into a ureg.Quantity with target ureg.Unit given as second argument
            if (
                isinstance(arg[0], str)
                and isinstance(arg[1], ureg.Unit)
                and isinstance(arg[3], ureg.Unit)
            ):
                if isinstance(arg[2], str):
                    return "case_five_str"
                elif isinstance(arg[2], list):
                    return "case_five_list"
            elif (
                isinstance(arg[0], str)
                and isinstance(arg[1], ureg.Unit)
                and isinstance(arg[2], str)
                and isinstance(arg[3], str)
            ):
                return "case_six"


def map_to_dtype(trg_dtype: str, value: Any) -> Any:
    # can this be done more elegantly, i.e. written more compact?
    # yes I already tried MAP_TO_DTYPE[trg_dtype](value) but mypy does not like it
    # error: Argument 1 has incompatible type "generic | bool | int | float | complex |
    #      str | bytes | memoryview"; expected "str | bytes | SupportsIndex"  [arg-type]
    if np.shape(value) != ():
        if trg_dtype == "u1":
            return np.asarray(value, np.uint8)
        elif trg_dtype == "i1":
            return np.asarray(value, np.int8)
        elif trg_dtype == "u2":
            return np.asarray(value, np.uint16)
        elif trg_dtype == "i2":
            return np.asarray(value, np.int16)
        # elif trg_dtype == "f2":
        #     return np.asarray(value, np.float16)
        elif trg_dtype == "u4":
            return np.asarray(value, np.uint32)
        elif trg_dtype == "i4":
            return np.asarray(value, np.int32)
        elif trg_dtype == "f4":
            return np.asarray(value, np.float32)
        elif trg_dtype == "u8":
            return np.asarray(value, np.uint64)
        elif trg_dtype == "i8":
            return np.asarray(value, np.int64)
        elif trg_dtype == "f8":
            return np.asarray(value, np.float64)
        elif trg_dtype == "bool":
            if hasattr(value, "dtype"):
                if value.dtype is bool:
                    return np.asarray(value, bool)
        else:
            raise ValueError(f"map_to_dtype, hitting unexpected case for array !")
    else:
        if trg_dtype == "u1":
            return np.uint8(value)
        elif trg_dtype == "i1":
            return np.int8(value)
        elif trg_dtype == "u2":
            return np.uint16(value)
        elif trg_dtype == "i2":
            return np.int16(value)
        # elif trg_dtype == "f2":
        #     return np.float16(value)
        elif trg_dtype == "u4":
            return np.uint32(value)
        elif trg_dtype == "i4":
            return np.int32(value)
        elif trg_dtype == "f4":
            return np.float32(value)
        elif trg_dtype == "u8":
            return np.uint64(value)
        elif trg_dtype == "i8":
            return np.int64(value)
        elif trg_dtype == "f8":
            return np.float64(value)
        elif trg_dtype == "bool":
            return try_interpret_as_boolean(value)
        else:
            raise ValueError(f"map_to_dtype, hitting unexpected case for scalar !")


def set_value(template: dict, trg: str, src_val: Any, trg_dtype: str = "") -> dict:
    """Set value in the template using trg.

    src_val can be a single value, an array, or a ureg.Quantity (scalar or array)
    """
    # np.issubdtype(np.uint32, np.signedinteger)
    if src_val:  # covering not None, not "", ...
        if not trg_dtype:  # go with existent dtype
            if isinstance(src_val, str):
                # TODO this is not rigorous need to check for null-term also and str arrays
                template[f"{trg}"] = src_val
                # assumes I/O to HDF5 will write specific encoding, typically variable, null-term, utf8
            elif isinstance(src_val, ureg.Quantity):
                if isinstance(
                    src_val.magnitude, (np.ndarray, np.generic)
                ) or np.isscalar(
                    src_val.magnitude
                ):  # bool case typically not expected!
                    template[f"{trg}"] = src_val.magnitude
                    if is_not_special_unit(src_val.units):
                        template[f"{trg}/@units"] = f"{src_val.units}"
                    print(
                        f"WARNING::Assuming writing to HDF5 will auto-convert Python types to numpy type, trg {trg} !"
                    )
                else:
                    raise TypeError(
                        f"ureg.Quantity magnitude should use in-build, bool, or np !"
                    )
            elif (
                isinstance(src_val, (np.ndarray, np.generic))
                or np.isscalar(src_val)
                or isinstance(src_val, bool)
            ):
                template[f"{trg}"] = src_val
                # units may be required, need to be set explicitly elsewhere in the source code!
                print(
                    f"WARNING::Assuming writing to HDF5 will auto-convert Python types to numpy type, trg: {trg} !"
                )
            else:
                raise TypeError(
                    f"Unexpected type {type(src_val)} found for not trg_dtype case !"
                )
        else:  # do an explicit type conversion
            # e.g. in cases when tech partner writes float32 but e.g. NeXus assumes float64
            if isinstance(src_val, str):
                raise TypeError(
                    f"Unexpected type str found when calling set_value, trg {trg} !"
                )
            elif isinstance(src_val, ureg.Quantity):
                if isinstance(src_val.magnitude, (np.ndarray, np.generic)):
                    template[f"{trg}"] = map_to_dtype(trg_dtype, src_val.magnitude)
                    if is_not_special_unit(src_val.units):
                        template[f"{trg}/@units"] = f"{src_val.units}"
                elif np.isscalar(src_val.magnitude):  # bool typically not expected
                    template[f"{trg}"] = map_to_dtype(trg_dtype, src_val.magnitude)
                    if is_not_special_unit(src_val.units):
                        template[f"{trg}/@units"] = f"{src_val.units}"
                else:
                    raise TypeError(
                        f"Unexpected type for explicit src_val.magnitude, set_value, trg {trg} !"
                    )
            elif isinstance(src_val, (np.ndarray, np.generic)):
                template[f"{trg}"] = map_to_dtype(trg_dtype, src_val)
                # units may be required, need to be set explicitly elsewhere in the source code!
                print(
                    f"WARNING::Assuming I/O to HDF5 will auto-convert to numpy type, trg: {trg} !"
                )
            elif np.isscalar(src_val):
                template[f"{trg}"] = map_to_dtype(trg_dtype, src_val)
                print(
                    f"WARNING::Assuming I/O to HDF5 will auto-convert to numpy type, trg: {trg} !"
                )
            else:
                raise TypeError(
                    f"Unexpected type for explicit type conversion, set_value, trg {trg} !"
                )
    return template


def use_functor(
    cmds: list, mdata: fd.FlatDict, prfx_trg: str, ids: list, template: dict
) -> dict:
    """Process the use functor."""
    for cmd in cmds:
        if isinstance(cmd, tuple):
            if len(cmd) == 2:
                if isinstance(cmd[0], str):
                    if isinstance(cmd[1], str):  # str, str
                        trg = var_path_to_spcfc_path(f"{prfx_trg}/{cmd[0]}", ids)
                        set_value(template, trg, cmd[1])
                    elif isinstance(cmd[1], ureg.Quantity):  # str, ureg.Quantity
                        trg = var_path_to_spcfc_path(f"{prfx_trg}/{cmd[0]}", ids)
                        set_value(template, trg, cmd[1])
    return template


def map_functor(
    cmds: list,
    mdata: fd.FlatDict,
    prfx_src: str,
    prfx_trg: str,
    ids: list,
    template: dict,
    trg_dtype_key: str = "",
) -> dict:
    for cmd in cmds:
        case = get_case(cmd)
        if case == "case_one":  # str
            if f"{prfx_src}{cmd}" not in mdata:
                continue
            src_val = mdata[f"{prfx_src}{cmd}"]
            trg = var_path_to_spcfc_path(f"{prfx_trg}/{cmd}", ids)
            set_value(template, trg, src_val, trg_dtype_key)
        elif case == "case_two_str":  # str, str
            if f"{prfx_src}{cmd[1]}" not in mdata:
                continue
            src_val = mdata[f"{prfx_src}{cmd[1]}"]
            trg = var_path_to_spcfc_path(f"{prfx_trg}/{cmd[0]}", ids)
            set_value(template, trg, src_val, trg_dtype_key)
        elif case == "case_two_list":
            # ignore empty list, all src paths str, all src_val have to exist of same type
            if len(cmd[1]) == 0:
                continue
            if not all(isinstance(val, str) for val in cmd[1]):
                continue
            if not all(f"{prfx_src}{val}" in mdata for val in cmd[1]):
                continue
            src_values = [mdata[f"{prfx_src}{val}"] for val in cmd[1]]
            if len(src_values) == 0:
                continue
            if not all(type(val) is type(src_values[0]) for val in src_values):
                continue
            trg = var_path_to_spcfc_path(f"{prfx_trg}/{cmd[0]}", ids)
            set_value(template, trg, np.asarray(src_values), trg_dtype_key)
        elif case == "case_three_str":  # str, ureg.Unit, str
            if f"{prfx_src}{cmd[2]}" not in mdata:
                continue
            src_val = mdata[f"{prfx_src}{cmd[2]}"]
            trg = var_path_to_spcfc_path(f"{prfx_trg}/{cmd[0]}", ids)
            if isinstance(src_val, ureg.Quantity):
                set_value(template, trg, src_val.to(cmd[1]), trg_dtype_key)
            else:
                set_value(
                    template, trg, ureg.Quantity(src_val, cmd[1].units), trg_dtype_key
                )
        elif case == "case_three_list":  # str, ureg.Unit, list
            if len(cmd[2]) == 0:
                continue
            if not all(isinstance(val, str) for val in cmd[2]):
                continue
            if not all(f"{prfx_src}{val}" in mdata for val in cmd[2]):
                continue
            src_values = [mdata[f"{prfx_src}{val}"] for val in cmd[2]]
            if not all(type(val) is type(src_values[0]) for val in src_values):
                # need to check whether content are scalars also
                continue
            trg = var_path_to_spcfc_path(f"{prfx_trg}/{cmd[0]}", ids)
            if isinstance(src_values, ureg.Quantity):
                set_value(template, trg, src_values, trg_dtype_key)
            else:
                set_value(
                    template,
                    trg,
                    ureg.Quantity(src_values, cmd[1].units),
                    trg_dtype_key,
                )
        elif case.startswith("case_four"):
            # both of these cases can be avoided in an implementation when the
            # src quantity is already a pint quantity instead of some
            # pure python or numpy value or array respectively
            print(
                f"WARNING::Ignoring case_four, instead refactor implementation such"
                f"that values on the src side are pint.Quantities already!"
            )
        elif case == "case_five_str":
            if f"{prfx_src}{cmd[2]}" not in mdata:
                continue
            src_val = mdata[f"{prfx_src}{cmd[2]}"]
            trg = var_path_to_spcfc_path(f"{prfx_trg}/{cmd[0]}", ids)
            if isinstance(src_val, ureg.Quantity):
                set_value(template, trg, src_val.to(cmd[1]), trg_dtype_key)
            else:
                pint_src = ureg.Quantity(src_val, cmd[3])
                set_value(template, trg, pint_src.to(cmd[1]), trg_dtype_key)
        elif case == "case_five_list":
            if len(cmd[2]) == 0:
                continue
            if not all(isinstance(val, str) for val in cmd[2]):
                continue
            if not all(f"{prfx_src}{val}" in mdata for val in cmd[2]):
                continue
            src_values = [mdata[f"{prfx_src}{val}"] for val in cmd[2]]
            if isinstance(src_values[0], ureg.Quantity):
                raise ValueError(
                    f"Hit unimplemented case that src_val is ureg.Quantity"
                )
            if not all(type(val) is type(src_values[0]) for val in src_values):
                continue
            trg = var_path_to_spcfc_path(f"{prfx_trg}/{cmd[0]}", ids)
            if isinstance(src_values, ureg.Quantity):
                set_value(template, trg, src_values.to(cmd[1]), trg_dtype_key)
            else:
                pint_src = ureg.Quantity(src_values, cmd[3])
                set_value(template, trg, pint_src.to(cmd[1]), trg_dtype_key)
        elif case == "case_six":
            if f"{prfx_src}{cmd[2]}" not in mdata or f"{prfx_src}{cmd[3]}" not in mdata:
                continue
            src_val = mdata[f"{prfx_src}{cmd[2]}"]
            src_unit = mdata[f"{prfx_src}{cmd[3]}"]
            trg = var_path_to_spcfc_path(f"{prfx_trg}/{cmd[0]}", ids)
            if isinstance(src_val, ureg.Quantity):
                set_value(template, trg, src_val.units.to(cmd[1]), trg_dtype_key)
            else:
                pint_src = ureg.Quantity(src_val, ureg.Unit(src_unit))
                set_value(template, trg, pint_src.to(cmd[1]), trg_dtype_key)
    return template


def timestamp_functor(
    cmds: list,
    mdata: fd.FlatDict,
    prfx_src: str,
    prfx_trg: str,
    ids: list,
    template: dict,
) -> dict:
    for cmd in cmds:
        if isinstance(cmd, tuple):
            if 2 <= len(cmd) <= 3:  # trg, src, timestamp or empty string (meaning utc)
                if all(isinstance(elem, str) for elem in cmd):
                    if f"{prfx_src}{cmd[1]}" not in mdata:
                        continue
                    if mdata[f"{prfx_src}{cmd[1]}"] == "":
                        continue
                    tzone = "UTC"
                    if len(cmd) == 3:
                        tzone = cmd[2]
                    if tzone not in pytz.all_timezones:
                        raise ValueError(
                            f"{tzone} is not a timezone in pytz.all_timezones!"
                        )
                    var_path_to_spcfc_path
                    trg = var_path_to_spcfc_path(f"{prfx_trg}/{cmd[0]}", ids)
                    template[f"{trg}"] = datetime.fromtimestamp(
                        int(mdata[f"{prfx_src}{cmd[1]}"]),
                        tz=pytz.timezone(tzone),
                    ).isoformat()
    return template


def filehash_functor(
    cmds: list,
    mdata: fd.FlatDict,
    prfx_src: str,
    prfx_trg: str,
    ids: list,
    template: dict,
) -> dict:
    for cmd in cmds:
        if isinstance(cmd, tuple):
            if len(cmd) == 2:
                if not all(isinstance(elem, str) for elem in cmd):
                    continue
                if f"{prfx_src}{cmd[1]}" not in mdata:
                    continue
                if mdata[f"{prfx_src}{cmd[1]}"] == "":
                    continue
                trg = var_path_to_spcfc_path(f"{prfx_trg}/{cmd[0]}", ids)
                with open(mdata[f"{prfx_src}{cmd[1]}"], "rb") as fp:
                    template[f"{rchop(trg, 'checksum')}checksum"] = (
                        get_sha256_of_file_content(fp)
                    )
                    template[f"{rchop(trg, 'checksum')}type"] = "file"
                    template[f"{rchop(trg, 'checksum')}path"] = mdata[
                        f"{prfx_src}{cmd[1]}"
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
        prfx_trg = cfg["prefix_trg"]
    else:
        raise KeyError(f"prefix_trg not found in cfg!")
    if "prefix_src" in cfg:
        prfx_src = cfg["prefix_src"]
    else:
        raise KeyError(f"prefix_src not found in cfg!")

    # process all mapping functors
    # (in graphical programming these are also referred to as filters or nodes),
    # i.e. an agent that gets some input does something (e.g. abstract mapping) and
    # returns an output, given the mapping can be abstract, we call it a functor

    # https://numpy.org/doc/stable/reference/arrays.dtypes.html

    for functor_key in cfg:
        if functor_key == "use":
            use_functor(cfg["use"], mdata, prfx_trg, ids, template)
        if functor_key == "map":
            map_functor(cfg[functor_key], mdata, prfx_src, prfx_trg, ids, template)
        if functor_key.startswith("map_to_"):
            dtype_key = functor_key.replace("map_to_", "")
            print(f"dtype_key >>>> {dtype_key}")
            if dtype_key in MAP_TO_DTYPES:
                map_functor(
                    cfg[functor_key],
                    mdata,
                    prfx_src,
                    prfx_trg,
                    ids,
                    template,
                    dtype_key,
                )
            else:
                raise KeyError(f"Unexpected dtype_key {dtype_key} !")
        if functor_key == "unix_to_iso8601":
            timestamp_functor(
                cfg["unix_to_iso8601"], mdata, prfx_src, prfx_trg, ids, template
            )
        if functor_key == "sha256":
            filehash_functor(cfg["sha256"], mdata, prfx_src, prfx_trg, ids, template)
    return template
