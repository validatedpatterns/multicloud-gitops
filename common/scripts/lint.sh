#!/bin/bash

# helm template (even with --dry-run) can interact with the cluster
# This won't protect us if a user has ~/.kube
# Also call helm template with a non existing --kubeconfig while we're at it
unset KUBECONFIG
target=$1
shift
name=$(echo $target | sed -e s@/@-@g -e s@charts-@@)

# Test the charts as the pattern would drive them
INPUTS=$(ls -1 common/examples/*.yaml | grep -v secret)
for input in $INPUTS; do
    helm lint $* -f $input $target
    if [ $? != 0 ]; then exit 1; fi
done

exit 0
