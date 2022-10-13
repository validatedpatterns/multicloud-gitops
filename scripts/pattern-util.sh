#!/bin/sh

if [ -z "$PATTERN_UTILITY_CONTAINER" ]; then
	PATTERN_UTILITY_CONTAINER="quay.io/hybridcloudpatterns/hybridcloudpatterns-utility-ee"
fi

# Copy Kubeconfig from current environment. The utilities will pick up ~/.kube/config if set so it's not mandatory
# /home/runner is the normal homedir
# $HOME is mounted as itself for any files that are referenced with absolute paths
# $HOME is mounted to /root because the UID in the container is 0 and that's where SSH looks for credentials
# We bind mount the SSH_AUTH_SOCK socket if it is set, so ssh works without user prompting
SSH_SOCK_MOUNTS=""
if [ -n "$SSH_AUTH_SOCK" ]; then
	SSH_SOCK_MOUNTS="-v ${SSH_AUTH_SOCK}:${SSH_AUTH_SOCK} -e SSH_AUTH_SOCK=${SSH_AUTH_SOCK}"
fi

# We must pass -e KUBECONFIG *only* if it is set, otherwise we end up passing
# KUBECONFIG="" which then will confuse ansible
KUBECONF_ENV=""
if [ -n "$KUBECONFIG" ]; then
	KUBECONF_ENV="-e KUBECONFIG=${KUBECONFIG}"
fi

podman run -it \
	--security-opt label=disable \
	${KUBECONF_ENV} \
	${SSH_SOCK_MOUNTS} \
	-v ${HOME}:/home/runner \
	-v ${HOME}:${HOME} \
	-v ${HOME}:/root \
	-w $(pwd) \
	"$PATTERN_UTILITY_CONTAINER" \
	$@
