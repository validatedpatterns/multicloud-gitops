#!/bin/sh

PATTERN_DIR="$1"

if [ -z "$PATTERN_DIR" ]; then
    PATTERN_DIR="."
fi

BACKEND=$(yq '.global.secretStore.backend' "$PATTERN_DIR/values-global.yaml" 2>/dev/null)

if [ -z "$BACKEND" -o "$BACKEND" == "null" ]; then
    BACKEND="vault"
fi

echo "$BACKEND"
