[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
![](https://github.com/FAIRmat-NFDI/pynxtools-em/actions/workflows/pytest.yml/badge.svg)
![](https://github.com/FAIRmat-NFDI/pynxtools-em/actions/workflows/pylint.yml/badge.svg)
![](https://github.com/FAIRmat-NFDI/pynxtools-em/actions/workflows/publish.yml/badge.svg)
![](https://img.shields.io/pypi/pyversions/pynxtools-em)
![](https://img.shields.io/pypi/l/pynxtools-em)
![](https://img.shields.io/pypi/v/pynxtools-em)
![](https://coveralls.io/repos/github/FAIRmat-NFDI/pynxtools-em/badge.svg?branch=main)
[![DOI](https://zenodo.org/badge/773960253.svg)](https://zenodo.org/badge/latestdoi/773960253)

# Parse and normalize electron microscopy data

## Installation
It is recommended to use python 3.12 with a dedicated virtual environment for this package.
Learn how to manage [python versions](https://github.com/pyenv/pyenv) and
[virtual environments](https://realpython.com/python-virtual-environments-a-primer/).

This package is a reader plugin for [`pynxtools`](https://github.com/FAIRmat-NFDI/pynxtools) and thus should be installed together with `pynxtools`:
```shell
pip install pynxtools[em]
```

for the latest release version from [pypi](https://pypi.org/project/pynxtools-em/).

If you are interested in the newest version, we recommend to work with a development installation instead.

## Purpose
This reader plugin for [`pynxtools`](https://github.com/FAIRmat-NFDI/pynxtools) is used to translate diverse file formats from the scientific community and technology partners
within the field of electron microscopy into a standardized representation using the [NeXus](https://www.nexusformat.org/) application definition [NXem](https://fairmat-nfdi.github.io/nexus_definitions/classes/applications/NXem.html#nxem).

## Supported file formats
This plugin supports several file formats that are currently used within the research field of electron microscopy.
A detailed summary is available in the [reference section of the documentation](https://fairmat-nfdi.github.io/pynxtools-em).

## Getting started
[A getting started tutorial](https://github.com/FAIRmat-NFDI/pynxtools-em/tree/main/examples) is offered that guides you
on how to use the em reader for converting your data to NeXus from a Jupyter notebook or command line calls. Note that not every combination of input from a supported file format and other input, such as from an electronic lab notebook, allows filling all required and recommended fields including their attributes of the NXem
application definition. Therefore, you may need to provide an ELN file that contains the missing values in order for the
validation step of the EM reader to pass.

## Contributing
We are continuously working on improving the collection of parsers and their functionalities.
If you would like to implement a parser for your data, feel free to get in contact.

## Development install
Install the package with its dependencies:

```shell
git clone https://github.com/FAIRmat-NFDI/pynxtools-em.git --branch main --recursive pynxtools_em
cd pynxtools_em
python -m pip install --upgrade pip
python -m pip install -e ".[dev,docs]"
pre-commit install
```

The last line installs a [pre-commit hook](https://pre-commit.com/#intro) which
automatically formats (linting) and type checks the code before committing.

## Test this software
Especially relevant for developers, there exists a basic test framework written in
[pytest](https://docs.pytest.org/en/stable/) which can be used as follows:

```shell
python -m pytest -sv tests
```

## Contact person in FAIRmat for this reader
[Markus Kühbach](https://www.fairmat-nfdi.eu/fairmat/about-fairmat/team-fairmat)
