#!/bin/sh

#This script is written to be POSIX-compliant, as not all sh are created equal - many are bash but
#Debian-derivatives use dash which doesn't support some bash syntax
#
#TARGET_NAMESPACE=manuela-ci

TARGET_NAMESPACE="external-secrets-deployable"
token_resource="vault"
src_ns="vault"

ns=0
ok=0

# Check for Namespaces and Secrets to be ready (it takes the cluster a few minutes to deploy them)
while [ 1 ] ; do
	echo -n "Checking for namespace $TARGET_NAMESPACE to exist..."
	if [ oc get namespace $TARGET_NAMESPACE >/dev/null 2>/dev/null ]; then
		echo "not yet"
		ns=0
		sleep 2
		continue
	else
		echo "OK"
		ns=1
	fi

	echo -n "Checking for $token_resource to be populated in $src_ns..."
	tok=`oc sa get-token -n $src_ns $token_resource 2>/dev/null`
	if [ "$?" = 0 ] && [ -n "$tok" ]; then
		echo "OK"
		ok=1
	else
		echo "not yet"
		ok=0
		sleep 2
		continue
	fi

	echo "Conditions met, managing sa token $token_resource in $TARGET_NAMESPACE"
	break
done

TOKEN=$(echo $tok | base64 -w 0)
cat << HERE | oc apply -f-
apiVersion: apps.open-cluster-management.io/v1
kind: Deployable
metadata:
  name: custom-kubernetes-token
  namespace: external-secrets-deployable
spec:
  channels:
  - external-secrets-ns
  template:
    apiVersion: v1
    kind: Secret
    metadata:
      name: custom-kubernetes-token
    data:
      token: ${TOKEN}
    type: Opaque
HERE

#echo "{ \"apiVersion\": \"apps.open-cluster-management.io/v1\", \"kind\": \"Deployable\", \"metadata\": { \"name\": \"custom-kubernetes-token\", \"namespace\": \"external-secrets-deployable\" }, { spec: { \"channels\": \[\"data\": { \"ARGOCD_PASSWORD\": \"$password\", \"ARGOCD_USERNAME\": \"$user\" }, \"type\": \"Opaque\" }" | oc apply -f-
