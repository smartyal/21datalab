#!/bin/bash
: "${PATH_BASE:="$(git rev-parse --show-toplevel)"}" 

# --- export envs
export HTTP_PROXY=
export HTTPS_PROXY=
export http_proxy=
export https_proxy=

# --- start
cd "${PATH_BASE}" 
python -S restservice.py importer
