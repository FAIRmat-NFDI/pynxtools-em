#!/bin/bash

# call from within the top-level directory of pynxtools_em
dsrc="../../../../paper_paper_paper/scidat_nomad_ebsd/bb_analysis/data/development_spctrscpy/pdi"
dsrc="../../../../paper_paper_paper/scidat_nomad_ebsd/bb_analysis/data/development_spctrscpy/ikz"
# dsrc="../../../../paper_paper_paper/scidat_nomad_ebsd/bb_analysis/data/production_ebsd_pyxem"

esrc="examples"
trg="debug"

# apex
# Laehnemann, PDI
examples="InGaN_nanowires_spectra.edaxh5"
# Bergmann, Kernke, Brückner, IKZ
examples="AlGaO.nxs GeSi.nxs GeSn_13.nxs VInP_108_L2.h5"
# examples="GeSi.nxs"
# Pauly, Uni Saarland
# examples="207_2081.edaxh5"

for example in $examples; do
	echo $example
	dataconverter convert $esrc/em.oasis.specific.yaml $esrc/eln_data.yaml $dsrc/$example --reader em --nxdl NXem --output=$trg/debug.$example.nxs --skip-verify 1>$trg/stdout.$example.nxs.txt 2>$trg/stderr.$example.nxs.txt
done
