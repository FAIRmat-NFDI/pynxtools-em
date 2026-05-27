import os
import sys

import py7zr
import rarfile

from pynxtools_em import get_pynxtools_em_version
from pynxtools_em.examples.get_sha256_of_directories import (
    SEPARATOR,
    analyze_file,
    analyze_rar_file,
    analyze_sevenzip_file,
    analyze_tar_file,
    analyze_zip_file,
)
from pynxtools_em.examples.oasisb_utils import CSV_HEADER_FOR_HASH_FILE


def hash_directory(root_path: str, prefix: str) -> None:
    """Recursively compute SHA256 checksum for all files in root_path."""

    config: dict[str, str] = {
        "python_version": f"{sys.version.replace(' ', '_')}",
        "working_directory": f"{os.getcwd()}",
        "pynxtools_em version": f"{get_pynxtools_em_version()}",
        "rarfile version": f"{rarfile.__version__}",
        "sevenzip version": f"{py7zr.__version__}",
        "root_path": f"{root_path}",
        "prefix": f"{prefix}",
    }

    progress: int = 0

    results: list[str] = []
    issues: list[str] = []
    for key, value in config.items():
        results.append(f"{key}{SEPARATOR}{value}")
        issues.append(f"{key}{SEPARATOR}{value}")

    results.append(CSV_HEADER_FOR_HASH_FILE)
    for root, dirs, files in os.walk(root_path):
        for file in files:
            fpath = f"{root}/{file}".replace(os.sep * 2, os.sep)

            if fpath.lower().endswith((".zip", ".eln")):
                analyze_zip_file(fpath, results, issues)
            elif fpath.lower().endswith((".tar", ".tar.gz", ".tar.bz2", ".tar.xz")):
                analyze_tar_file(fpath, results, issues)
            elif fpath.lower().endswith(".rar"):
                analyze_rar_file(fpath, results, issues)
            elif fpath.lower().endswith(".7z"):
                analyze_sevenzip_file(fpath, results, issues)
            else:
                analyze_file(fpath, results, issues)

            progress += 1
            if progress % 100 == 0:
                print(f"Processed {progress} files and archives")

    with open(
        f"{prefix}.sha256.results.csv",
        "w",
        encoding="utf-8",
        errors="surrogateescape",
    ) as fp:
        fp.write("\n".join(results))
    del results
    with open(
        f"{prefix}.sha256.issues.csv",
        "w",
        encoding="utf-8",
        errors="surrogateescape",
    ) as fp:
        fp.write("\n".join(issues))
    if len(issues) > len(config.keys()):
        print(issues)
    else:
        print(f"Batch queue completed")
        print(f"SHA256 computed for {progress} files or archives")
        print(f"{len(issues) - len(config.keys())} issues found")


def main():
    # e.g. call via
    # `python3 hash_microscope_database.py /microscope_data microscope_data`
    if len(sys.argv) > 1:
        root_path = sys.argv[1]
    else:
        root_path = "."

    if len(sys.argv) > 2:
        prefix = sys.argv[2]
    else:
        prefix = "hash_microscope_database"

    hash_directory(root_path, prefix)


if __name__ == "__main__":
    main()
