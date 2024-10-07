#!/bin/sh

APP=$1
STATE=$2

MAIN_CLUSTERGROUP_FILE="./values-$(common/scripts/determine-main-clustergroup.sh).yaml"
MAIN_CLUSTERGROUP_PROJECT="$(common/scripts/determine-main-clustergroup.sh)"

case "$APP" in
    "vault")
        APP_NAME="vault"
        NAMESPACE="vault"
        PROJECT="$MAIN_CLUSTERGROUP_PROJECT"
        CHART_NAME="hashicorp-vault"
        CHART_VERSION=0.1.*

    ;;
    "golang-external-secrets")
        APP_NAME="golang-external-secrets"
        NAMESPACE="golang-external-secrets"
        PROJECT="$MAIN_CLUSTERGROUP_PROJECT"
        CHART_NAME="golang-external-secrets"
        CHART_VERSION=0.1.*

    ;;
    *)
        echo "Error - cannot manage $APP can only manage vault and golang-external-secrets"
        exit 1
    ;;
esac

case "$STATE" in
    "present")
        common/scripts/manage-secret-namespace.sh "$NAMESPACE" "$STATE"

        RES=$(yq ".clusterGroup.applications[] | select(.path == \"$CHART_LOCATION\")" "$MAIN_CLUSTERGROUP_FILE" 2>/dev/null)
        if [ -z "$RES" ]; then
            echo "Application with chart location $CHART_LOCATION not found, adding"
            yq -i ".clusterGroup.applications.$APP_NAME = { \"name\": \"$APP_NAME\", \"namespace\": \"$NAMESPACE\", \"project\": \"$PROJECT\", \"chart\": \"$CHART_NAME\",  \"chartVersion\": \"$CHART_VERSION\"}" "$MAIN_CLUSTERGROUP_FILE"
        fi
    ;;
    "absent")
        common/scripts/manage-secret-namespace.sh "$NAMESPACE" "$STATE"
        echo "Removing application wth chart location $CHART_LOCATION"
        yq -i "del(.clusterGroup.applications[] | select(.chart == \"$CHART_NAME\"))" "$MAIN_CLUSTERGROUP_FILE"
    ;;
    *)
        echo "$STATE not supported"
        exit 1
    ;;
esac

exit 0
