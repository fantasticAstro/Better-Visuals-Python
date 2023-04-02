#!/usr/bin/env bash

set -o errexit
set -o nounset
set -o pipefail

if [[ "${TRACE-0}" == "1" ]]; then
    set -o xtrace
fi

shopt -s extglob

pwd
rm -f -v sqlite.db
rm -f -v .spotipy_cache
cd saved_data/
pwd
rm -rf -v !(".gitkeep")