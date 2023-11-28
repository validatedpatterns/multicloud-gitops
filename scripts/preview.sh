#!/bin/bash

# DISCLAIMER
# 
# - Parsing of applications needs to be more clever. Currently the code assumes that all 
# targets will be local charts. This is not true, for example, in industrial-edge.
# - There is currently not a mechanism to actually preview against multiple clusters 
# (i.e. a hub and a remote). All previews will be done against the current.
# - Make output can be included in the YAML.

SITE=$1; shift
APP=$1; shift
GIT_REPO=$1; shift
GIT_BRANCH=$1; shift

chart=$(yq ".clusterGroup.applications.$APP.path" values-$SITE.yaml)
namespace=$(yq ".clusterGroup.applications.$APP.namespace" values-$SITE.yaml)
pattern=$(yq ".global.pattern" values-global.yaml)

platform=$(oc get Infrastructure.config.openshift.io/cluster  -o jsonpath='{.spec.platformSpec.type}')
ocpversion=$(oc get clusterversion/version -o jsonpath='{.status.desired.version}' | awk -F. '{print $1"."$2}')
domain=$(oc get Ingress.config.openshift.io/cluster -o jsonpath='{.spec.domain}' | sed 's/^apps.//')

function replaceGlobals() {
    output=$( echo $1 | sed -e 's/ //g' -e 's/\$//g' -e s@^-@@g  -e s@\'@@g )

    output=$(echo $output | sed "s@{{.Values.global.clusterPlatform}}@${platform}@g")
    output=$(echo $output | sed "s@{{.Values.global.clusterVersion}}@${ocpversion}@g")
    output=$(echo $output | sed "s@{{.Values.global.clusterDomain}}@${domain}@g")

    echo $output
}

function getOverrides() {
    overrides=''
    overrides=$( yq ".clusterGroup.applications.$APP.overrides[]" "values-$SITE.yaml" )
    overrides=$( echo "$overrides" | tr -d '\n' )
    overrides=$( echo "$overrides" | sed -e 's/name:/ --set/g; s/value: /=/g' )
    if [ -n "$overrides" ]; then
        echo "$overrides"
    fi
}


CLUSTER_OPTS=""
CLUSTER_OPTS="$CLUSTER_OPTS --set global.pattern=$pattern"
CLUSTER_OPTS="$CLUSTER_OPTS --set global.repoURL=$GIT_REPO"
CLUSTER_OPTS="$CLUSTER_OPTS --set main.git.repoURL=$GIT_REPO"
CLUSTER_OPTS="$CLUSTER_OPTS --set main.git.revision=$GIT_BRANCH"
CLUSTER_OPTS="$CLUSTER_OPTS --set global.namespace=$namespace"
CLUSTER_OPTS="$CLUSTER_OPTS --set global.hubClusterDomain=apps.$domain"
CLUSTER_OPTS="$CLUSTER_OPTS --set global.localClusterDomain=apps.$domain"
CLUSTER_OPTS="$CLUSTER_OPTS --set global.clusterDomain=$domain"
CLUSTER_OPTS="$CLUSTER_OPTS --set global.clusterVersion=$ocpversion"
CLUSTER_OPTS="$CLUSTER_OPTS --set global.clusterPlatform=$platform"


sharedValueFiles=$(yq ".clusterGroup.sharedValueFiles" values-$SITE.yaml)
appValueFiles=$(yq ".clusterGroup.applications.$APP.extraValueFiles" values-$SITE.yaml)
OVERRIDES=$( getOverrides )

VALUE_FILES=""
IFS=$'\n'
for line in $sharedValueFiles; do
    if [ $line != "null" ]; then
	file=$(replaceGlobals $line)
	VALUE_FILES="$VALUE_FILES -f $PWD$file"
    fi
done

for line in $appValueFiles; do
    if [ $line != "null" ]; then
	file=$(replaceGlobals $line)
	VALUE_FILES="$VALUE_FILES -f $PWD$file"
    fi
done

cmd="helm template $chart --name-template ${APP} -n ${namespace} ${VALUE_FILES} ${OVERRIDES} ${CLUSTER_OPTS}"
eval "$cmd"
