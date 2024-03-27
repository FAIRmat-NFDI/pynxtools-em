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
# see pynxtools-apm

import datetime as dt


EM_OASIS_TO_NEXUS_CFG = [
    ("/ENTRY[entry*]/definition", "NXem"),
    (
        "/ENTRY[entry*]/start_time",
        f"{dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00', 'Z')}",
    ),
]
