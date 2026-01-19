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
"""Derived image class to derive every tech-partner-specific TIFF parser from."""

import mmap

from PIL import Image
from PIL.TiffTags import TAGS

from pynxtools_em.utils.config import DEFAULT_VERBOSITY
from pynxtools_em.utils.custom_logging import logger


class TiffParser:
    """Read Tagged Image File Format TIF/TIFF."""

    def __init__(self, file_path: str = "", verbose: bool = DEFAULT_VERBOSITY):
        if file_path:
            self.file_path = file_path
        self.verbose = verbose
        self.version: dict = {}  # trg target versions supported, src actual
        self.tags: dict = {}
        self.supported = False
        self.check_if_tiff()

    def check_if_tiff(self):
        """Check if resource behind self.file_path is a TaggedImageFormat file."""
        self.supported = False
        # different tech partners may all generate tiff files but internally
        # report completely different pieces of information the situation is the same
        # as for HDF5 files. Therefore, specific parsers for specific tech partner content
        # is required, checking just on the file ending is in most cases never sufficient !
        # Checking the magic number is useful as it can help with narrowing down that one
        # has a specific type of container format. However, like it is the case with a
        # container you can pack almost whatever into it. Unfortunately, this is how tiff
        # is currently being used and the research field of electron microscopy makes
        # no exception here. Indeed, it is a common practice to export single images
        # from a microscope session using common image formats like png, jpg, tiff
        # often with a scale bar hard-coded into the image.
        # Although this is usual practice, we argue this is not best practice at all.
        # Instead, use and develop tech-partner file formats and at conferences and meetings
        # speak up to convince the tech partners to offer documentation of the
        # content of their file formats (ideally using semantic web technology).
        # The more this happens and the more users articulate this need, one can
        # write software to support scientists with reading directly and more completely
        # from these tech partner files. In effect, there is then less and less of a reason
        # to manually export files and share them ad hoc like single tiff images.
        # Rather try to think about a mindset change and ask yourself:
        # Can I not just show this content to my colleagues in the research
        # data management system directly instead of copying over files that in the
        # process of manually exporting them get cut off from their contextualization
        # and unless I am then super careful and spent time with writing rich metadata?
        # Most tech partners by now have file formats with indeed very rich metadata.
        # Our conviction is that these should be used and explored more frequently.
        # Exactly for this reason we provided an example for the differences
        # in the current state of and documentation of EBSD data stored in HDF5
        try:
            with open(self.file_path, "rb", 0) as file:
                s = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)
                magic = s.read(4)
                if magic != b"II*\x00":  # https://en.wikipedia.org/wiki/TIFF
                    return
                self.supported = True
        except (OSError, FileNotFoundError):
            logger.warning(f"{self.file_path} either FileNotFound or IOError !")
            return

    def get_tags(self):
        """Extract tags if present."""
        logger.debug("Reporting the tags found in this TIFF file...")
        # for an overview of tags
        # https://www.loc.gov/preservation/digital/formats/content/tiff_tags.shtml
        with Image.open(self.file_path, mode="r") as fp:
            self.tags = {}
            for key in fp.tag_v2:
                if key in TAGS:
                    self.tags[TAGS[key]] = fp.tag_v2[key]
            if self.verbose:
                for key, val in self.tags.items():
                    logger.info(f"{key}, {val}")
