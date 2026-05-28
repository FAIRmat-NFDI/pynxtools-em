#!/bin/sh

ruff format examples/deu_berlin_koch/deu_berlin_koch_batch_process.py
git add .
git commit -m "fixing"
git push
