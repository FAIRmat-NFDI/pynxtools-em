from typing import Any, Tuple

from pynxtools.dataconverter.readers.base.reader import BaseReader

class EMReader(BaseReader):
    """
    Reader for my method....
    PLEASE UPDATE
    """

    supported_nxdls = ["NXem"]

    def read(
        self,
        template: dict = None,
        file_paths: Tuple[str] = None,
        objects: Tuple[Any] = None,
    ):
        """
        General read menthod to prepare the template.
        """
        return template


READER = EMReader
