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
"""Simple profiling"""

import platform

import numpy as np

# try:
#     from cpuinfo import get_cpu_info
#
#     HAS_CPU_INFO: bool = True
# except ImportError:
#     HAS_CPU_INFO: bool = False


def simple_profiling(template: dict, tic: int, toc: int, entry_id: int = 1) -> dict:
    """Get simple profiling and system analytics."""
    trg = f"/ENTRY[entry{entry_id}]/profiling"
    # if HAS_CPU_INFO:
    #     info = get_cpu_info()
    #     aggregate = []
    #     for key in ["processor_type", "model", "family", "stepping", "flags"]:
    #         if key in info.keys():
    #             aggregate.append(info[key])
    #     if len(aggregate) > 0:
    #         template[f"{trg}/model"] = ", ".join([f"{value}" for value in aggregate])
    # else:
    #     template[f"{trg}/model"] = "unknown"
    template[f"{trg}/architecture"] = f"{platform.machine()}"
    template[f"{trg}/operating_system"] = (
        f"{platform.uname().system}, {platform.uname().release}, {platform.uname().version}"
    )
    template[f"{trg}/max_processes"] = np.uint32(1)
    template[f"{trg}/max_threads"] = np.uint32(1)
    template[f"{trg}/max_gpus"] = np.uint32(0)
    template[f"{trg}/template_filling_elapsed_time"] = np.float64((toc - tic) / 1.0e9)
    template[f"{trg}/template_filling_elapsed_time/@units"] = "s"
    return template
