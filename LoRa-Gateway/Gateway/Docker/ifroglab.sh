#!/bin/sh
# Compatibility entry point; run on the Docker host, not inside an old image.
set -eu
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec sh "$script_dir/../loragateway.sh" "$@"
