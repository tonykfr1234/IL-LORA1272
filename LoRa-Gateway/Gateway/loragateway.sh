#!/bin/sh
# Host-side launcher. USB/serial collection runs separately; see the PHP guide.
set -eu
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_dir=$(CDPATH= cd -- "$script_dir/../.." && pwd)
if [ "$#" -eq 0 ]; then
    set -- up --build -d --wait
fi
exec docker compose --project-directory "$repo_dir" -f "$repo_dir/compose.yaml" "$@"
