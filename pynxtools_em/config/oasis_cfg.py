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
"""Dict mapping values for a specifically configured NOMAD Oasis."""

# see specific comments about the design that should be moved to mkdocs

# import datetime as dt
# f"{dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00', 'Z')}",

EM_EXAMPLE_CSYS_TO_NEXUS = {
    "prefix": "/ENTRY[entry*]/coordinate_system_set/COORDINATE_SYSTEM[coordinate_system*]",
    "load": [
        "alias",
        "type",
        "handedness",
        ("x_direction", "xaxis_direction"),
        ("x_alias", "xaxis_alias"),
        ("y_direction", "yaxis_direction"),
        ("y_alias", "yaxis_alias"),
        ("z_direction", "zaxis_direction"),
        ("z_alias", "zaxis_alias"),
        "origin",
    ],
}
