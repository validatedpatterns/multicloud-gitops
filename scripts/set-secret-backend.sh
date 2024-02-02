#!/bin/sh

BACKEND=$1

yq -i ".global.secretStore.backend = \"$BACKEND\"" values-global.yaml
