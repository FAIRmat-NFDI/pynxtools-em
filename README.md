[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
![](https://github.com/FAIRmat-NFDI/pynxtools-em/actions/workflows/pytest.yml/badge.svg)
![](https://github.com/FAIRmat-NFDI/pynxtools-em/actions/workflows/pylint.yml/badge.svg)
![](https://github.com/FAIRmat-NFDI/pynxtools-em/actions/workflows/publish.yml/badge.svg)
![](https://img.shields.io/pypi/pyversions/pynxtools-em)
![](https://img.shields.io/pypi/l/pynxtools-em)
![](https://img.shields.io/pypi/v/pynxtools-em)
![](https://coveralls.io/repos/github/FAIRmat-NFDI/pynxtools-em/badge.svg?branch=main)
[![DOI](https://zenodo.org/badge/759916501.svg)](https://doi.org/10.5281/zenodo.13951684)

# `pynxtools-em`: A `pynxtools` reader for EM data

`pynxtools-em` is a `pynxtools` reader plugin for electron microscopy (EM) data.

This `pynxtools` plugin was generated with [`cookiecutter`](https://github.com/cookiecutter/cookiecutter) using the [`pynxtools-plugin-template`](https://github.com/FAIRmat-NFDI/`pynxtools-plugin-template) template.

## Installation

It is recommended to use python 3.12 with a dedicated virtual environment for this package.
Learn how to manage [python versions](https://github.com/pyenv/pyenv) and
[virtual environments](https://realpython.com/python-virtual-environments-a-primer/).

This package is a reader plugin for [`pynxtools`](https://github.com/FAIRmat-NFDI/pynxtools) and can be installed together with `pynxtools`:

```shell
uv pip install pynxtools[em]
```

for the latest released version.

## Purpose
This reader plugin for [`pynxtools`](https://github.com/FAIRmat-NFDI/pynxtools) is used to translate diverse file formats from the scientific community and technology partners
within the field of electron microscopy into a standardized representation using the [NeXus](https://www.nexusformat.org/) application definition [NXem](https://fairmat-nfdi.github.io/nexus_definitions/classes/applications/NXem.html#nxem).

## Docs

More information about this pynxtools plugin is available in the [documentation](https://fairmat-nfdi.github.io/pynxtools-em/). You will find information about getting started, how-to guides, the supported file formats, how to get involved, and much more there.

## Contact person in FAIRmat for this reader

Markus Kühbach

## How to cite this work

Kühbach, M., Shabih, S., Brockhauser, S., Spiecker, E., Weber, H., Koch, C., Draxl, C. (2025). pynxtools-em: A pynxtools reader plugin for electron microscopy (EM) data. Zenodo. https://doi.org/10.5281/zenodo.13951684
