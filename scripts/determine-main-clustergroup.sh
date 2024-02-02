#!/bin/bash

PATTERN_DIR="$1"

if [ -z "$PATTERN_DIR" ]; then
    PATTERN_DIR="."
fi

CGNAME=$(yq '.main.clusterGroupName' "$PATTERN_DIR/values-global.yaml")

if [ -z "$CGNAME" ] || [ "$CGNAME" == "null" ]; then
    echo "Error - cannot detrmine clusterGroupName"
    exit 1
fi

echo "$CGNAME"
