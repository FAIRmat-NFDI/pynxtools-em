import argparse
import glob

#!/usr/bin/env python3
import logging
import os
import sys
from multiprocessing import Process

import bibtexparser
import click
import pandas as pd
import yaml

from pynxtools_em.examples.oasisb.batch_process import (
    get_parsing_tasks,
    process_project,
    process_task,
)
from pynxtools_em.examples.oasisb.oasisb_utils import get_project_id
from pynxtools_em.utils.custom_logging import logger


def run(project_id: str) -> int:

    logger.info(os.getcwd())
    with open(f"{os.getcwd()}{os.sep}source_directory.txt") as fp:
        src_directory: str = f"{fp.readline().strip().replace('/', os.sep)}"
    logger.info(src_directory)
    with open(f"{os.getcwd()}{os.sep}target_directory.txt") as fp:
        trg_directory: str = f"{fp.readline().strip().replace('/', os.sep)}"
    logger.info(trg_directory)
    """
    with open(f"{os.getcwd()}{os.sep}alias_prefix_secret.txt") as fp:
        alias_prefix_secret: str = f"{fp.readline().strip().replace('/', os.sep)}"
    logger.info(alias_prefix_secret)
    """

    # os.makedirs(
    #     f"{trg_directory.replace('/decompressed', '/pynxtools')}", exist_ok=True
    # )
    # os.listdir(f"{trg_directory.replace('/decompressed', '')}")

    spread_sheet_of_all_projects = pd.read_excel(
        f"{trg_directory.replace('/decompressed', '/config')}{os.sep}aaa_legacy_data.ods",
        sheet_name="aaa_legacy_data",
        engine="odf",
        dtype=str,
    ).fillna("")

    with open(
        f"{trg_directory.replace('/decompressed', '/config')}{os.sep}aaa_legacy_data.bib"
    ) as fp:
        bib = bibtexparser.load(fp).entries_dict

    project_range: tuple[int, int] = (1, 880)

    with open(
        f"{trg_directory.replace('/decompressed', '/config')}{os.sep}aaa_em_nomad_project_names.yaml"
    ) as fp:
        nomad_project_names: dict[str, str] = yaml.safe_load(fp)

    count: int = 0
    for row in spread_sheet_of_all_projects.itertuples(index=True):
        if row.legal == "1" and row.use == "1":
            if (
                project_id == get_project_id(row.project_name)
                and project_range[0] <= int(project_id) <= project_range[1]
                and project_id in nomad_project_names
            ):
                config_file = f"{trg_directory}{os.sep}{project_id}.image.decompressed.csv.subset.ods"
                if not os.path.isfile(config_file):
                    continue

                tasks: dict[str, list[str]] = get_parsing_tasks(project_id, config_file)
                # tasks has respectively either main or main and sidecar file puzzled together from a list
                # f"{project_id}.hash" is the key, used as output_file_prefix
                # list of main and sidecar file are the values, used as input_paths

                for nexus_file_name_prefix, input_paths in tasks.items():
                    print(f"{nexus_file_name_prefix}, {input_paths}")

                    def parse():
                        # now each task call for all files of one NeXus file
                        process_task(
                            project_id,
                            input_paths,
                            nexus_file_name_prefix,
                            bib,
                            trg_directory,
                            f"{trg_directory.replace('/decompressed', '/pynxtools')}",
                            "image",
                            openalex_file=f"{os.getcwd()}{os.sep}openalex/D{project_id}.json",
                            logger_file_path_suffix="image",
                            nomad_project_name=nomad_project_names[project_id],
                        )

                    p = Process(target=parse)
                    p.start()
                    p.join()

                    count += 1

                """
                for mime_type in ["msa", "dm3", "dm4", "emd"]:
                    def work_package():  # assure memory gets returned to the operating system
                        process_project(
                            project_id,
                            # f"{src_directory}{os.sep}{project_id}.ods",
                            f"{trg_directory.replace('/decompressed', '/config')}{os.sep}aaa_legacy_data.bib",
                            "",  # no file_path_aliasing f"{trg_directory}{os.sep}{project_id}.mixed.decompressed.csv",
                            trg_directory,
                            f"{trg_directory.replace('/decompressed', '/pynxtools')}",
                            mime_type,  # "msa",
                            alias_prefix_secret,
                            openalex_file=f"{os.getcwd()}{os.sep}openalex/D{project_id}.json",
                            logger_file_path_suffix=mime_type,  # "msa",
                            nomad_project_name=nomad_project_names[project_id],
                        )

                    p = Process(target=work_package)
                    p.start()
                    p.join()
                count += 1
                """

    logger.info(f"Batch queue completed {count}")
    return 0


@click.command()
@click.option(
    "--project",
    "project_id",
    required=True,
    type=str,
    help="001, 002, ... project_id",
)
def main(project_id: str) -> None:
    try:
        code = run(project_id)
        sys.exit(code)
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        sys.exit(130)
    except Exception:
        logger.exception("Unhandled exception")
        sys.exit(1)


if __name__ == "__main__":
    main()
