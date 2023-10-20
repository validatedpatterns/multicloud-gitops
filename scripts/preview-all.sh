#!/bin/bash

REPO=$1; shift;
TARGET_BRANCH=$1; shift

HUB=$( yq ".main.clusterGroupName" values-global.yaml )
MANAGED_CLUSTERS=$( yq ".clusterGroup.managedClusterGroups.[].name" values-$HUB.yaml )
ALL_CLUSTERS=( $HUB $MANAGED_CLUSTERS )

for cluster in ${ALL_CLUSTERS[@]}; do
    APPS=$( yq ".clusterGroup.applications.[].name" values-$cluster.yaml )
    for app in $APPS; do
        common/scripts/preview.sh $cluster $app $REPO $TARGET_BRANCH
    done
done
