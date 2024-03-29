#!/bin/bash

REPO=$1; shift;
TARGET_BRANCH=$1; shift

HUB=$( yq ".main.clusterGroupName" values-global.yaml )
MANAGED_CLUSTERS=$( yq ".clusterGroup.managedClusterGroups.[].name" values-$HUB.yaml )
ALL_CLUSTERS=( $HUB $MANAGED_CLUSTERS )

CLUSTER_INFO_OUT=$(oc cluster-info 2>&1)
CLUSTER_INFO_RET=$?
if [ $CLUSTER_INFO_RET -ne 0 ]; then
    echo "Could not access the cluster:"
    echo "${CLUSTER_INFO_OUT}"
    exit 1
fi

for cluster in ${ALL_CLUSTERS[@]}; do
    # We always add clustergroup as it is the entry point and it gets special cased in preview.sh.
    APPS="clustergroup $( yq ".clusterGroup.applications.[].name" values-$cluster.yaml )"
    for app in $APPS; do
        printf "# Parsing application $app from cluster $cluster\n"
        common/scripts/preview.sh $cluster $app $REPO $TARGET_BRANCH
    done
done
