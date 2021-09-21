#!/usr/bin/env bash

ns=0
gitops=0

# Check for Namespaces and Secrets to be ready (it takes the cluster a while to deploy them)
while [ 1 ]; do
    if [ oc get namespace manuela-ci >/dev/null 2>/dev/null ]; then
        ns=0
    else
        ns=1
    fi

    if [ oc -n openshift-gitops extract secrets/openshift-gitops-cluster --to=- 1>/dev/null 2>/dev/null ]; then
        gitops=0
    else
        gitops=1
    fi

	if [ "$gitops" == 1 -a "$ns" == 1 ]; then
        break
    fi
done

user=$(echo admin | base64)
password=$(oc -n openshift-gitops extract secrets/openshift-gitops-cluster --to=- 2>/dev/null | base64)

cat <<EOSECRET | oc apply -f-
apiVersion: v1
kind: Secret
metadata:
  name: argocd-env
  namespace: manuela-ci
data:
  ARGOCD_PASSWORD: $password
  ARGOCD_USERNAME: $user
type: Opaque
EOSECRET
