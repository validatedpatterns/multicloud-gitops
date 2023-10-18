#!/bin/bash -x

SITE=$1; shift
APP=$1; shift
GIT_REPO=$1; shift
GIT_BRANCH=$1; shift


export APP=config-demo;
chart=$(yq ".clusterGroup.applications.$APP.path" values-$SITE.yaml)
namespace=$(yq ".clusterGroup.applications.$APP.namespace" values-$SITE.yaml)
pattern=$(yq ".global.pattern" values-global.yaml)

platform=$(oc get Infrastructure.config.openshift.io/cluster  -o jsonpath='{.spec.platformSpec.type}')
ocpversion=$(oc get clusterversion/version -o jsonpath='{.status.desired.version}' | awk -F. '{print $1"."$2}')
domain=$(oc get Ingress.config.openshift.io/cluster -o jsonpath='{.spec.domain}' | sed 's/^apps.//')

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


helm template $chart --name-template ${APP} -n ${namespace} ${CLUSTER_OPTS}
