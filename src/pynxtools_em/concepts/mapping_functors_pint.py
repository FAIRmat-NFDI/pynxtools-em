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
from typing import Any, Dict

import flatdict as fd
import numpy as np
import pytz

from pynxtools_em.utils.get_file_checksum import (
    DEFAULT_CHECKSUM_ALGORITHM,
    get_sha256_of_file_content,
)
from pynxtools_em.utils.interpret_boolean import try_interpret_as_boolean
from pynxtools_em.utils.pint_custom_unit_registry import is_not_special_unit, ureg
from pynxtools_em.utils.string_conversions import rchop

# best practice is use np.ndarray or np.generic as magnitude within that ureg.Quantity!
MAP_TO_DTYPES: Dict[str, type] = {
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
    "str": str,
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
    """Identify which case an instruction from the configuration belongs to.
    Each case comes with specific instructions to resolve that are detailed
    in the README.md in this source code directory."""
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
        if trg_dtype in MAP_TO_DTYPES:
            if trg_dtype != "bool":
                return np.asarray(value, MAP_TO_DTYPES[trg_dtype])
            else:
                if hasattr(value, "dtype"):
                    if value.dtype is bool:
                        return np.asarray(value, bool)
                else:
                    raise TypeError(
                        f"map_to_dtype, hitting unexpected case for array bool !"
                    )
        else:
            raise ValueError(f"map_to_dtype, hitting unexpected case for array !")
    else:
        if trg_dtype in MAP_TO_DTYPES:
            if trg_dtype != "bool":
                that_type = MAP_TO_DTYPES[trg_dtype]
                return that_type(value)
            else:
                return try_interpret_as_boolean(value)
        else:
            raise ValueError(f"map_to_dtype, hitting unexpected case for scalar !")


def set_value(template: dict, trg: str, src_val: Any, trg_dtype: str = "") -> dict:
    """Set value in the template using trg.

    src_val can be a single value, an array, or a ureg.Quantity (scalar or array)
    """
    # np.issubdtype(np.uint32, np.signedinteger)
    if not trg_dtype:  # go with existent dtype
        if isinstance(src_val, str):
            # TODO this is not rigorous need to check for null-term also and str arrays
            template[f"{trg}"] = src_val
            # assumes I/O to HDF5 will write specific encoding, typically variable, null-term, utf8
        elif isinstance(src_val, bool):
            template[f"{trg}"] = try_interpret_as_boolean(src_val)
        elif isinstance(src_val, ureg.Quantity):
            if isinstance(src_val.magnitude, (np.ndarray, np.generic)) or np.isscalar(
                src_val.magnitude
            ):  # bool case typically not expected!
                template[f"{trg}"] = src_val.magnitude
                if is_not_special_unit(src_val):
                    template[f"{trg}/@units"] = f"{src_val.units}"
                print(
                    f"WARNING::Assuming writing to HDF5 will auto-convert Python types to numpy type, trg {trg} !"
                )
            else:
                raise TypeError(
                    f"ureg.Quantity magnitude should use in-build, bool, or np !"
                )
        elif isinstance(src_val, list):
            if all(isinstance(val, str) for val in src_val):
                template[f"{trg}"] = ", ".join(src_val)
            else:
                raise TypeError(
                    f"Not List[str] {type(src_val)} found for not trg_dtype case !"
                )
        elif (
            isinstance(src_val, (np.ndarray, np.generic))
            or np.isscalar(src_val)
            or isinstance(src_val, bool)
        ):
            template[f"{trg}"] = np.asarray(src_val)
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
            if trg_dtype != "bool":
                template[f"{trg}"] = f"{src_val}"
            else:
                template[f"{trg}"] = try_interpret_as_boolean(src_val)
        elif isinstance(src_val, bool):
            template[f"{trg}"] = try_interpret_as_boolean(src_val)
        elif isinstance(src_val, ureg.Quantity):
            if isinstance(src_val.magnitude, (np.ndarray, np.generic)):
                template[f"{trg}"] = map_to_dtype(trg_dtype, src_val.magnitude)
                if is_not_special_unit(src_val):
                    template[f"{trg}/@units"] = f"{src_val.units}"
            elif np.isscalar(src_val.magnitude):  # bool typically not expected
                template[f"{trg}"] = map_to_dtype(trg_dtype, src_val.magnitude)
                if is_not_special_unit(src_val):
                    template[f"{trg}/@units"] = f"{src_val.units}"
            else:
                raise TypeError(
                    f"Unexpected type for explicit src_val.magnitude, set_value, trg {trg} !"
                )
        elif isinstance(src_val, list):
            if trg_dtype == "str":
                if all(isinstance(val, str) for val in src_val):
                    template[f"{trg}"] = ", ".join(src_val)
                else:
                    template[f"{trg}"] = ", ".join([f"{val}" for val in src_val])
                print(
                    f"WARNING::Assuming I/O to HDF5 will serializing to concatenated string !"
                )
            else:
                template[f"{trg}"] = map_to_dtype(trg_dtype, np.asarray(src_val))
                # units may be required, need to be set explicitly elsewhere in the source code!
                print(
                    f"WARNING::Assuming I/O to HDF5 will auto-convert to numpy type, trg: {trg} !"
                )
        elif isinstance(src_val, (np.ndarray, np.generic)):
            template[f"{trg}"] = map_to_dtype(trg_dtype, np.asarray(src_val))
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
    """Process concept mapping for simple predefined strings and pint quantities."""
    for cmd in cmds:
        if isinstance(cmd, tuple):
            if len(cmd) == 2:
                if isinstance(cmd[0], str):
                    if isinstance(cmd[1], (str, ureg.Quantity, bool)):
                        # str, str or str, ureg or str, bool
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
    """Process concept mapping, datatype and unit conversion for quantities."""
    # for debugging set configurable breakpoints like such
    # prfx_trg == "/ENTRY[entry*]/measurement/events/EVENT_DATA_EM[event_data_em*]/instrument"
    # either here or on a resolved variadic name in the trg variable
    # in the set_value function or specific parameterized concept names like
    # cmd[0] == "optics/operation_mode" (see rsciio_gatan_cfg, GATAN_DYNAMIC_VARIOUS_NX)
    for cmd in cmds:
        case = get_case(cmd)
        if case == "case_one":  # str
            src_val = mdata.get(f"{prfx_src}{cmd}")
            if src_val is not None and src_val != "":
                trg = var_path_to_spcfc_path(f"{prfx_trg}/{cmd}", ids)
                set_value(template, trg, src_val, trg_dtype_key)
        elif case == "case_two_str":  # str, str
            src_val = mdata.get(f"{prfx_src}{cmd[1]}")
            if src_val is not None and src_val != "":
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
            if not all(src_val is not None and src_val != "" for src_val in src_values):
                continue
            if trg_dtype_key != "str":
                if not all(type(val) is type(src_values[0]) for val in src_values):
                    continue
            trg = var_path_to_spcfc_path(f"{prfx_trg}/{cmd[0]}", ids)
            set_value(template, trg, src_values, trg_dtype_key)
        elif case == "case_three_str":  # str, ureg.Unit, str
            src_val = mdata.get(f"{prfx_src}{cmd[2]}")
            if not src_val:
                continue
            trg = var_path_to_spcfc_path(f"{prfx_trg}/{cmd[0]}", ids)
            if isinstance(src_val, ureg.Quantity):
                set_value(template, trg, src_val.to(cmd[1]), trg_dtype_key)
            else:
                set_value(template, trg, ureg.Quantity(src_val, cmd[1]), trg_dtype_key)
        elif case == "case_three_list":  # str, ureg.Unit, list
            if len(cmd[2]) == 0:
                continue
            if not all(isinstance(val, str) for val in cmd[2]):
                continue
            if not all(f"{prfx_src}{val}" in mdata for val in cmd[2]):
                continue
            src_values = [mdata[f"{prfx_src}{val}"] for val in cmd[2]]
            if not all(src_val is not None and src_val != "" for src_val in src_values):
                continue
            if not all(type(val) is type(src_values[0]) for val in src_values):
                # need to check whether content are scalars also
                continue
            trg = var_path_to_spcfc_path(f"{prfx_trg}/{cmd[0]}", ids)
            if isinstance(src_values, ureg.Quantity):
                set_value(template, trg, src_values, trg_dtype_key)
            else:
                # potentially a list of ureg.Quantities with different scaling
                normalize = []
                for val in src_values:
                    if isinstance(val, ureg.Quantity):
                        normalize.append(val.to(cmd[1]).magnitude)
                    else:
                        raise TypeError(
                            "Unimplemented case for {val} in case_three_list !"
                        )
                set_value(
                    template,
                    trg,
                    ureg.Quantity(normalize, cmd[1]),
                    trg_dtype_key,
                )
        elif case.startswith("case_four"):
            # both of these cases can be avoided in an implementation when the
            # src quantity is already a pint quantity instead of some
            # pure python or numpy value or array respectively
            raise NotImplementedError(
                f"Hitting unimplemented case_four, instead refactor implementation such"
                f"that values on the src side are pint.Quantities already!"
            )
        elif case == "case_five_str":
            src_val = mdata.get(f"{prfx_src}{cmd[2]}")
            if not src_val:
                continue
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
            if not all(src_val is not None and src_val != "" for src_val in src_values):
                continue
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
            raise NotImplementedError("Check handling of units!")
            if f"{prfx_src}{cmd[2]}" not in mdata or f"{prfx_src}{cmd[3]}" not in mdata:
                continue
            src_val = mdata[f"{prfx_src}{cmd[2]}"]
            src_unit = mdata[f"{prfx_src}{cmd[3]}"]
            if not src_val or not src_unit:
                continue
            trg = var_path_to_spcfc_path(f"{prfx_trg}/{cmd[0]}", ids)
            if isinstance(src_val, ureg.Quantity):
                set_value(template, trg, src_val.to(cmd[1]), trg_dtype_key)
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
    """Process concept mapping and time format conversion."""
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
    """Process concept mapping and checksums to add context from which file NeXus content was processed."""
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
                try:
                    with open(mdata[f"{prfx_src}{cmd[1]}"], "rb") as fp:
                        fragment = rchop(trg, "checksum")
                        template[f"{fragment}checksum"] = get_sha256_of_file_content(fp)
                        template[f"{fragment}type"] = "file"
                        template[f"{fragment}file_name"] = mdata[f"{prfx_src}{cmd[1]}"]
                        template[f"{fragment}algorithm"] = DEFAULT_CHECKSUM_ALGORITHM
                except (FileNotFoundError, IOError):
                    print(f"File {mdata[f'''{prfx_src}{cmd[1]}''']} not found !")
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
        prefix_trg = cfg["prefix_trg"]
    else:
        raise KeyError(f"prefix_trg not found in cfg!")
    if "prefix_src" in cfg:
        if isinstance(cfg["prefix_src"], str):
            prfx_src = [cfg["prefix_src"]]
        elif isinstance(cfg["prefix_src"], list) and all(
            isinstance(val, str) for val in cfg["prefix_src"]
        ):
            prfx_src = cfg["prefix_src"]
        else:
            raise ValueError(f"prefix_src needs to be a str or a list[str] !")
    else:
        raise KeyError(f"prefix_src not found in cfg!")

    # process all mapping functors
    # (in graphical programming these are also referred to as filters or nodes),
    # i.e. an agent that gets some input does something (e.g. abstract mapping) and
    # returns an output, given the mapping can be abstract, we call it a functor

    # https://numpy.org/doc/stable/reference/arrays.dtypes.html
    for prefix_src in prfx_src:
        for functor_key, functor in cfg.items():
            if functor_key in ["prefix_trg", "prefix_src"]:
                continue
            elif functor_key == "use":
                use_functor(cfg["use"], mdata, prefix_trg, ids, template)
            elif functor_key == "map":
                map_functor(functor, mdata, prefix_src, prefix_trg, ids, template)
            elif functor_key.startswith("map_to_"):
                dtype_key = functor_key.replace("map_to_", "")
                if dtype_key in MAP_TO_DTYPES:
                    map_functor(
                        functor,
                        mdata,
                        prefix_src,
                        prefix_trg,
                        ids,
                        template,
                        dtype_key,
                    )
                else:
                    raise KeyError(f"Unexpected dtype_key {dtype_key} !")
            elif functor_key == "unix_to_iso8601":
                timestamp_functor(
                    cfg["unix_to_iso8601"], mdata, prefix_src, prefix_trg, ids, template
                )
            elif functor_key == DEFAULT_CHECKSUM_ALGORITHM:
                filehash_functor(
                    cfg[DEFAULT_CHECKSUM_ALGORITHM],
                    mdata,
                    prefix_src,
                    prefix_trg,
                    ids,
                    template,
                )
            else:
                raise KeyError(f"Unexpected functor_key {functor_key} !")
    return template
