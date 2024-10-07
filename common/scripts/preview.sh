#!/bin/bash

# DISCLAIMER
# 
# - Parsing of applications needs to be more clever.
# - There is currently not a mechanism to actually preview against multiple clusters 
# (i.e. a hub and a remote). All previews will be done against the current.
# - Make output can be included in the YAML.

SITE=$1; shift
APPNAME=$1; shift
GIT_REPO=$1; shift
GIT_BRANCH=$1; shift

if [ "${APPNAME}" != "clustergroup" ]; then
  # This covers the following case:
  # foobar:
  #   name: foo
  #   namespace: foo
  #   project: foo
  #   path: charts/all/foo
  # So we retrieve the actual index ("foobar") given the name attribute of the application
  APP=$(yq ".clusterGroup.applications | with_entries(select(.value.name == \"$APPNAME\")) | keys | .[0]" values-$SITE.yaml)
  isLocalHelmChart=$(yq ".clusterGroup.applications.$APP.path" values-$SITE.yaml)
  if [ $isLocalHelmChart != "null" ]; then
    chart=$(yq ".clusterGroup.applications.$APP.path" values-$SITE.yaml)
  else
    helmrepo=$(yq ".clusterGroup.applications.$APP.repoURL" values-$SITE.yaml)
    helmrepo="${helmrepo:+oci://quay.io/hybridcloudpatterns}"
    chartversion=$(yq ".clusterGroup.applications.$APP.chartVersion" values-$SITE.yaml)
    chartname=$(yq ".clusterGroup.applications.$APP.chart" values-$SITE.yaml)
    chart="${helmrepo}/${chartname} --version ${chartversion}"
  fi
  namespace=$(yq ".clusterGroup.applications.$APP.namespace" values-$SITE.yaml)
else
  APP=$APPNAME
  clusterGroupChartVersion=$(yq ".main.multiSourceConfig.clusterGroupChartVersion" values-global.yaml)
  helmrepo="oci://quay.io/hybridcloudpatterns"
  chart="${helmrepo}/clustergroup --version ${clusterGroupChartVersion}"
  namespace="openshift-operators"
fi
pattern=$(yq ".global.pattern" values-global.yaml)

# You can override the default lookups by using OCP_{PLATFORM,VERSION,DOMAIN}
# Note that when using the utility container you need to pass in the above variables
# by export EXTRA_ARGS="-e OCP_PLATFORM -e OCP_VERSION -e OCP_DOMAIN" before
# invoking pattern-util.sh
platform=${OCP_PLATFORM:-$(oc get Infrastructure.config.openshift.io/cluster  -o jsonpath='{.spec.platformSpec.type}')}
ocpversion=${OCP_VERSION:-$(oc get clusterversion/version -o jsonpath='{.status.desired.version}' | awk -F. '{print $1"."$2}')}
domain=${OCP_DOMAIN:-$(oc get Ingress.config.openshift.io/cluster -o jsonpath='{.spec.domain}' | sed 's/^apps.//')}

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
isKustomize=$(yq ".clusterGroup.applications.$APP.kustomize" values-$SITE.yaml)
OVERRIDES=$( getOverrides )

VALUE_FILES="-f values-global.yaml -f values-$SITE.yaml"
IFS=$'\n'
for line in $sharedValueFiles; do
    if [ $line != "null" ] && [ -f $line ]; then
	    file=$(replaceGlobals $line)
	    VALUE_FILES="$VALUE_FILES -f $PWD$file"
    fi
done

for line in $appValueFiles; do
    if [ $line != "null" ] && [ -f $line ]; then
	    file=$(replaceGlobals $line)
	    VALUE_FILES="$VALUE_FILES -f $PWD$file"
    fi
done

if [ $isKustomize == "true" ]; then
    kustomizePath=$(yq ".clusterGroup.applications.$APP.path" values-$SITE.yaml)
    repoURL=$(yq ".clusterGroup.applications.$APP.repoURL" values-$SITE.yaml)
    if [[ $repoURL == http* ]] || [[ $repoURL == git@ ]]; then
         kustomizePath="${repoURL}/${kustomizePath}"
    fi
    cmd="oc kustomize ${kustomizePath}"
    eval "$cmd"
else
    cmd="helm template $chart --name-template ${APP} -n ${namespace} ${VALUE_FILES} ${OVERRIDES} ${CLUSTER_OPTS}"
    eval "$cmd"
fi
