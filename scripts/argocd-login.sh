#!/usr/bin/env bash

## Login to validated patterns argocd instances

# Detect Argo CD namespaces
ARGOCD_NAMESPACES=$(oc get argoCD -A -o jsonpath='{.items[*].metadata.namespace}')
if [ -z "$ARGOCD_NAMESPACES" ]; then
    echo "Error: No Argo CD instances found in the cluster."
    exit 1
fi

# Split the namespaces into an array
NAMESPACES=($ARGOCD_NAMESPACES)

# Check if there are at least two Argo CD instances
if [ ${#NAMESPACES[@]} -lt 2 ]; then
    echo "Error: Less than two Argo CD instances found.  Found instances in namespaces: $ARGOCD_NAMESPACES"
    exit 1
fi


for NAMESPACE in ${NAMESPACES[@]}; do
    # get the instance name
    ARGOCD_INSTANCE=$(oc get argocd -n "$NAMESPACE" -o jsonpath='{.items[0].metadata.name}') # assume only one per NS
    SERVER_URL=$(oc get route "$ARGOCD_INSTANCE"-server -n "$NAMESPACE" -o jsonpath='{.status.ingress[0].host}')
    PASSWORD=$(oc get secret "$ARGOCD_INSTANCE"-cluster -n "$NAMESPACE" -o jsonpath='{.data.admin\.password}' | base64 -d)
    echo $PASSWORD
    argocd login --skip-test-tls --insecure --grpc-web "$SERVER_URL" --username "admin" --password "$PASSWORD"
    if [ "$?" -ne 0 ]; then
      echo "Login to Argo CD ${SERVER_URL} failed. Exiting."
      exit 1
    fi
    
done 
