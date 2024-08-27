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
"""Standardized functionalities and visualization used within the EDS community using normalized data."""

import numpy as np
from pynxtools_em.concepts.nxs_image_set import NxImageRealSpaceSet

# process_roi_eds_spectra(inp, template)
# process_roi_eds_maps(inp, template)
# if ckey.startswith("eds_roi") and inp[ckey] != {}:
# self.process_roi_overview_eds_based(inp[ckey], template)


def process_roi_overview_eds_based(self, inp, template: dict) -> dict:
    trg = (
        f"/ENTRY[entry{self.entry_id}]/measurement/event_data_em_set/"
        f"EVENT_DATA_EM[event_data_em{self.id_mgn['event']}]/"
        f"IMAGE_SET[image_set{self.id_mgn['event_img']}]/image_2d"
    )
    template[f"{trg}/description"] = inp.tmp["source"]
    template[f"{trg}/title"] = f"Region-of-interest overview image"
    template[f"{trg}/@signal"] = "real"
    dims = [("i", 0), ("j", 1)]
    template[f"{trg}/@axes"] = []
    for dim in dims[::-1]:
        template[f"{trg}/@axes"].append(f"axis_{dim[0]}")
    template[f"{trg}/real"] = {
        "compress": inp.tmp["image_2d/real"].value,
        "strength": 1,
    }
    template[f"{trg}/real/@long_name"] = f"Signal"
    for dim in dims:
        template[f"{trg}/@AXISNAME_indices[axis_{dim[0]}_indices]"] = np.uint32(dim[1])
        template[f"{trg}/AXISNAME[axis_{dim[0]}]"] = {
            "compress": inp.tmp[f"image_2d/axis_{dim[0]}"].value,
            "strength": 1,
        }
        template[f"{trg}/AXISNAME[axis_{dim[0]}]/@long_name"] = inp.tmp[
            f"image_2d/axis_{dim[0]}@long_name"
        ].value
    self.id_mgn["event_img"] += 1
    self.id_mgn["event"] += 1
    return template


def process_roi_eds_spectra(self, inp: dict, template: dict) -> dict:
    for ckey in inp.keys():
        if ckey.startswith("eds_spc") and inp[ckey] != {}:
            trg = (
                f"/ENTRY[entry{self.entry_id}]/measurement/event_data_em_set/"
                f"EVENT_DATA_EM[event_data_em{self.id_mgn['event']}]/SPECTRUM_SET"
                f"[spectrum_set{self.id_mgn['event_spc']}]/spectrum_0d"
            )
            template[f"{trg}/description"] = inp[ckey].tmp["source"]
            template[f"{trg}/title"] = f"Region-of-interest overview image"
            template[f"{trg}/@signal"] = "real"
            template[f"{trg}/@axes"] = ["axis_energy"]
            template[f"{trg}/real"] = {
                "compress": inp[ckey].tmp["spectrum_0d/real"].value,
                "strength": 1,
            }
            template[f"{trg}/real/@long_name"] = (
                inp[ckey].tmp["spectrum_0d/real@long_name"].value
            )
            template[f"{trg}/@AXISNAME_indices[axis_energy_indices]"] = np.uint32(0)
            template[f"{trg}/AXISNAME[axis_energy]"] = {
                "compress": inp[ckey].tmp[f"spectrum_0d/axis_energy"].value,
                "strength": 1,
            }
            template[f"{trg}/AXISNAME[axis_energy]/@long_name"] = (
                inp[ckey].tmp[f"spectrum_0d/axis_energy@long_name"].value
            )
            self.id_mgn["event_spc"] += 1
            self.id_mgn["event"] += 1
    return template


def process_roi_eds_maps(self, inp: dict, template: dict) -> dict:
    for ckey in inp.keys():
        if ckey.startswith("eds_map") and inp[ckey] != {}:
            trg = (
                f"/ENTRY[entry{self.entry_id}]/ROI[roi{self.id_mgn['roi']}]/"
                f"eds/indexing"
            )
            template[f"{trg}/source"] = inp[ckey].tmp["source"]
            for img in inp[ckey].tmp["IMAGE_SET"]:
                if not isinstance(img, NxImageRealSpaceSet):
                    continue
                trg = (
                    f"/ENTRY[entry{self.entry_id}]/ROI[roi{self.id_mgn['roi']}]/eds/"
                    f"indexing/IMAGE_SET[image_set{self.id_mgn['eds_img']}]"
                )
                template[f"{trg}/source"] = img.tmp["source"]
                template[f"{trg}/description"] = img.tmp["description"]
                template[f"{trg}/energy_range"] = img.tmp["energy_range"].value
                template[f"{trg}/energy_range/@units"] = img.tmp["energy_range"].unit
                template[f"{trg}/iupac_line_candidates"] = img.tmp[
                    "iupac_line_candidates"
                ]
                template[f"{trg}/image_2d/@signal"] = "real"
                template[f"{trg}/image_2d/@axes"] = ["axis_j", "axis_i"]
                template[f"{trg}/image_2d/title"] = f"EDS map {img.tmp['description']}"
                template[f"{trg}/image_2d/real"] = {
                    "compress": img.tmp["image_2d/real"].value,
                    "strength": 1,
                }
                template[f"{trg}/image_2d/real/@long_name"] = f"Signal"
                dims = [("i", 0), ("j", 1)]
                for dim in dims:
                    template[
                        f"{trg}/image_2d/@AXISNAME_indices[axis_{dim[0]}_indices]"
                    ] = np.uint32(dim[1])
                    template[f"{trg}/image_2d/AXISNAME[axis_{dim[0]}]"] = {
                        "compress": img.tmp[f"image_2d/axis_{dim[0]}"].value,
                        "strength": 1,
                    }
                    template[f"{trg}/image_2d/AXISNAME[axis_{dim[0]}]/@long_name"] = (
                        img.tmp[f"image_2d/axis_{dim[0]}@long_name"].value
                    )
                self.id_mgn["eds_img"] += 1
            self.id_mgn["roi"] += 1
    return template
