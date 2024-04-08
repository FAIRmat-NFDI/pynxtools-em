#!/bin/bash

# call from within the top-level directory of pynxtools_em
dsrc="../../../../paper_paper_paper/scidat_nomad_ebsd/bb_analysis/data/development_spiecker/"
esrc="examples"

examples="eln"

for example in $examples; do
	echo $example
	dataconverter convert $esrc/em.oasis.specific.yaml --reader em --nxdl NXem --output=debug.$example.nxs 1>stdout.$example.nxs.txt 2>stderr.$example.nxs.txt
done
