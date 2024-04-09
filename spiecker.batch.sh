#!/bin/bash

# call from within the top-level directory of pynxtools_em
dsrc="../../../../paper_paper_paper/scidat_nomad_ebsd/bb_analysis/data/development_spiecker"
esrc="examples"
trg="debug"

examples="1340_Camera_Ceta_440_kx.emd"
examples="2102_SI_HAADF.emd"

for example in $examples; do
	echo $example
	dataconverter convert $esrc/em.oasis.specific.yaml $esrc/eln_data.yaml $dsrc/$example --reader em --nxdl NXem --output=$trg/debug.$example.nxs 1>$trg/stdout.$example.nxs.txt 2>$trg/stderr.$example.nxs.txt
done
