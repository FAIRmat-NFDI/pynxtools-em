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
"""Parser mapping content of specific image files on NeXus."""

from pynxtools_em.parsers.image_png_protochips import ProtochipsPngSetParser
from pynxtools_em.parsers.image_tiff_point_electronic import PointElectronicTiffParser
from pynxtools_em.parsers.image_tiff_tfs import TfsTiffParser
from pynxtools_em.parsers.image_tiff_zeiss import ZeissTiffParser


class NxEmImagesParser:
    """Map content from different type of image files on an instance of NXem."""

    def __init__(self, entry_id: int = 1, file_path: str = "", verbose: bool = False):
        """Overwrite constructor of the generic reader."""
        if entry_id > 0:
            self.entry_id = entry_id
        else:
            self.entry_id = 1
        self.file_path = file_path
        self.cache = {"is_filled": False}
        self.verbose = verbose

    def identify_image_type(self):
        """Identify if image matches known mime type and has content for which parser exists."""
        # tech partner formats used for measurement
        img = TfsTiffParser(self.file_path)
        if img.supported:
            return "tiff_tfs"
        img = ZeissTiffParser(self.file_path)
        if img.supported:
            return "tiff_zeiss"
        img = PointElectronicTiffParser(self.file_path)
        if img.supported:
            return "tiff_point_electronic"
        img = ProtochipsPngSetParser(self.file_path)
        if img.supported:
            return "set_of_zipped_png_protochips"
        return None

    def parse(self, template: dict) -> dict:
        image_parser_type = self.identify_image_type()
        if image_parser_type is None:
            print(
                f"Parser {self.__class__.__name__} finds no content in {self.file_path} that it supports"
            )
            return template
        print(f"{self.__class__.__name__} identified content as {image_parser_type}")
        # see also comments for respective nxs_pyxem parser
        # and its interaction with tech-partner-specific hfive_* parsers
        if image_parser_type == "tiff_tfs":
            tfs = TfsTiffParser(self.file_path, self.entry_id)
            tfs.parse_and_normalize()
            tfs.process_into_template(template)
        elif image_parser_type == "tiff_zeiss":
            zss = ZeissTiffParser(self.file_path, self.entry_id)
            zss.parse(template)
        elif image_parser_type == "tiff_point_electronic":
            pe = PointElectronicTiffParser(self.file_path, self.entry_id)
            pe.parse_and_normalize()
            pe.process_into_template(template)
        elif image_parser_type == "set_of_zipped_png_protochips":
            axon = ProtochipsPngSetParser(self.file_path, self.entry_id)
            axon.parse_and_normalize()
            axon.process_into_template(template)
        # add here further specific content (sub-)parsers for formats from other
        # tech partner or other custom parsing of images
        return template
