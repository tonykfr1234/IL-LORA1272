#!/bin/sh
# Compatibility entry point for the new host-side Compose launcher.
set -eu
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec sh "$script_dir/../loragateway.sh" "$@"
