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
"""Get XMP metadata from an image."""

import xml.etree.ElementTree as ET

from PIL import Image


def extract_full_xmp(path):
    with Image.open(path) as img:
        xmp = img.info.get("XML:com.adobe.xmp")
        if xmp:
            print("Extracting XMP metadata via pillow")
            return ET.fromstring(xmp)
    with open(path, "rb") as fp:
        data = fp.read()
        start = data.find(b"<x:xmpmeta")
        end = data.find(b"</x:xmpmeta")
        if start != -1 and end != -1:
            end += len(b"</x:xmpmeta>")
            xmp = data[start:end].decode("utf-8", errors="replace")
            if xmp:
                print("Extracting XMP metadata via explicit xmpmeta content")
                return ET.fromstring(xmp)
