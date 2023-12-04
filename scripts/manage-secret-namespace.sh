#!/bin/sh

NAMESPACE=$1
STATE=$2

MAIN_CLUSTERGROUP_FILE="./values-$(common/scripts/determine-main-clustergroup.sh).yaml"
MAIN_CLUSTERGROUP_PROJECT="$(common/scripts/determine-main-clustergroup.sh)"

case "$STATE" in
    "present")

        RES=$(yq ".clusterGroup.namespaces[] | select(. == \"$NAMESPACE\")" "$MAIN_CLUSTERGROUP_FILE" 2>/dev/null)
        if [ -z "$RES" ]; then
            echo "Namespace $NAMESPACE not found, adding"
            yq -i ".clusterGroup.namespaces += [ \"$NAMESPACE\" ]" "$MAIN_CLUSTERGROUP_FILE"
        fi
    ;;
    "absent")
        echo "Removing namespace $NAMESPACE"
        yq -i "del(.clusterGroup.namespaces[] | select(. == \"$NAMESPACE\"))" "$MAIN_CLUSTERGROUP_FILE"
    ;;
    *)
        echo "$STATE not supported"
        exit 1
    ;;
esac

exit 0
