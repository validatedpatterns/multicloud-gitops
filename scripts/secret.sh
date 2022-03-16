#!/bin/sh

#This script must receive arguments for the following parameters; it is easiest to pass them as environment variables from the command line.
#Example values from the first use for it, in industrial-edge
#
#This script is written to be POSIX-compliant, as not all sh are created equal - many are bash but
#Debian-derivatives use dash which doesn't support some bash syntax
#
#PATTERN=industrial-edge
#TARGET_NAMESPACE=manuela-ci
#COMPONENT=datacenter
#SECRET_NAME='argocd-env'

passwd_resource="secrets/${COMPONENT}-gitops-cluster"
src_ns="${PATTERN}-${COMPONENT}"

ns=0
gitops=0

# Function log
# Arguments:
#   $1 are for the options for echo
#   $2 is for the message
#   \033[0K\r - Trailing escape sequence to leave output on the same line
function log {
	if [ -z "$2" ]; then
		echo -e "\033[0K\r\033[1;36m$1\033[0m"
	else
		echo -e $1 "\033[0K\r\033[1;36m$2"
	fi
}

# Check for Namespaces and Secrets to be ready (it takes the cluster a few minutes to deploy them)
spin='-\|/'
i=0
while [ 1 ] ; do
	i=$(( (i+1) %4 ))
	log -n "Checking for namespace $TARGET_NAMESPACE to exist: ${spin:$i:1}"
	if [ oc get namespace $TARGET_NAMESPACE >/dev/null 2>/dev/null ]; then
		ns=0
		sleep 2
		continue
	else
		log "Checking for namespace $TARGET_NAMESPACE to exist: OK"
		ns=1
		break
	fi
done

i=0
while [ 1 ] ; do
	i=$(( (i+1) %4 ))
	log -n "Checking for $passwd_resource to be populated in $src_ns: ${spin:$i:1}"
	pw=`oc -n $src_ns extract $passwd_resource --to=- 2>/dev/null`
	if [ "$?" = 0 ] && [ -n "$pw" ]; then
		log "Checking for $passwd_resource to be populated in $src_ns: OK"
		gitops=1
	else
		gitops=0
		sleep 2
		continue
	fi

	log "Conditions met, managing secret $SECRET_NAME in $TARGET_NAMESPACE"
	break
done

user=$(echo admin | base64)
password=$(echo $pw | base64)

echo "{ \"apiVersion\": \"v1\", \"kind\": \"Secret\", \"metadata\": { \"name\": \"$SECRET_NAME\", \"namespace\": \"$TARGET_NAMESPACE\" }, \"data\": { \"ARGOCD_PASSWORD\": \"$password\", \"ARGOCD_USERNAME\": \"$user\" }, \"type\": \"Opaque\" }" | oc apply -f-
