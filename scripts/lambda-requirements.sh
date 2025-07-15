#!/bin/bash
set -euxo pipefail

PARENT_DIR="$(dirname "$(dirname "$0")")"

uv export --no-hashes --package update_base_images > "$PARENT_DIR/lambda/update_base_images/requirements.txt"
