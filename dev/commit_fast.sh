#!/bin/sh

ruff format examples/ger_berlin_koch/ger_berlin_koch_batch_process.py
git add .
git commit -m "fixing"
git push
