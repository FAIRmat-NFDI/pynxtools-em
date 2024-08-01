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
"""Interpret different human-readable forms of a boolean statement to boolean."""

HUMAN_BOOLEAN_STATEMENT = {
    "0": False,
    "1": True,
    "n": False,
    "y": True,
    "no": False,
    "yes": True,
    "false": False,
    "true": True,
}


def try_interpret_as_boolean(arg: str) -> bool:
    """Try to interpret a human string statement if boolean be strict."""
    if arg.lower() in HUMAN_BOOLEAN_STATEMENT:
        return HUMAN_BOOLEAN_STATEMENT[arg.lower()]
    raise KeyError(
        f"try_to_interpret_as_boolean argument {arg} does not yield key even for {arg.lower()}!"
    )
