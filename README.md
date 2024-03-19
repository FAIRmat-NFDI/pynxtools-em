[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
![](https://github.com/FAIRmat-NFDI/pynxtools-em/actions/workflows/pytest.yml/badge.svg)
![](https://github.com/FAIRmat-NFDI/pynxtools-em/actions/workflows/pylint.yml/badge.svg)
![](https://github.com/FAIRmat-NFDI/pynxtools-em/actions/workflows/publish.yml/badge.svg)
![](https://coveralls.io/repos/github/FAIRmat-NFDI/pynxtools-em/badge.svg?branch=master)

# A reader for electron microscopy (EM) data

# Installation

TODO:add installation e.g. following xps, mpes

# Purpose
This reader plugin for [pynxtools](https://github.com/FAIRmat-NFDI/pynxtools) is used to translate diverse file formats from the scientific community and technology partners
within the field of electron microscopy into a standardized representation using the
[NeXus](https://www.nexusformat.org/) application definition [NXem](https://fairmat-nfdi.github.io/nexus_definitions/classes/contributed_definitions/NXem.html#nxapm).

## Supported file formats
TODO:

# Getting started
TODO: Point to jupyter notebook giving examples.

# Contributing
We are continously working on adding parsers for other data formats, technology partners, and atom probers.
If you would like to implement a parser for your data, feel free to get in contact.

## Development install

Install the package with its dependencies:

```shell
git clone https://github.com/FAIRmat-NFDI/pynxtools-em.git \\
    --branch master \\
    --recursive pynxtools_em
cd pynxtools_apm
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install -e ".[dev]"
```

There is also a [pre-commit hook](https://pre-commit.com/#intro) available
which formats the code and checks the linting before actually commiting.
It can be installed with
```shell
pre-commit install
```
from the root of this repository.

## Development Notes
TODO: Give details about envisioned development of the parser.

## Test this software

Especially relevant for developers, there exists a basic test framework written in
[pytest](https://docs.pytest.org/en/stable/) which can be used as follows:

```shell
python -m pytest -sv tests
```

## Contact person in FAIRmat for this reader
Markus Kühbach
