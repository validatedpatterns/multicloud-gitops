#!/bin/sh

PATTERN_DIR="$1"

if [ -z "$PATTERN_DIR" ]; then
    PATTERN_DIR="."
fi

PATNAME=$(yq '.global.pattern' "$PATTERN_DIR/values-global.yaml" 2>/dev/null)

if [ -z "$PATNAME" ] || [ "$PATNAME" == "null" ]; then
    PATNAME="$(basename "$PWD")"
fi

echo "$PATNAME"
