#!/bin/sh

if [ -z "$PATTERN_UTILITY_CONTAINER" ]; then
	PATTERN_UTILITY_CONTAINER="quay.io/hybridcloudpatterns/hybridcloudpatterns-utility-ee"
fi

# This is one of the most concise ways to get a readlink -f command work without going too complicated
# Across Linux and MacOSX
function real_path() {
       echo $(cd $(dirname $1) ; pwd -P)
}

# Copy Kubeconfig from current environment. The utilities will pick up ~/.kube/config if set so it's not mandatory
# /home/runner is the normal homedir
# $HOME is mounted as itself for any files that are referenced with absolute paths
# $HOME is mounted to /root because the UID in the container is 0 and that's where SSH looks for credentials
# We bind mount the SSH_AUTH_SOCK socket if it is set, so ssh works without user prompting
SSH_SOCK_MOUNTS=""
if [ -n "$SSH_AUTH_SOCK" ]; then
	SSH_SOCK_MOUNTS="-v $(real_path $SSH_AUTH_SOCK):/ssh-agent -e SSH_AUTH_SOCK=/ssh-agent"
fi

podman run -it \
	--security-opt label=disable \
	-e KUBECONFIG="${KUBECONFIG}" \
	${SSH_SOCK_MOUNTS} \
	-e GIT_SSH_COMMAND="ssh -o IgnoreUnknown=pubkeyacceptedalgorithms" \
	-v ${HOME}:/home/runner \
	-v ${HOME}:${HOME} \
	-v ${HOME}:/root \
	-w $(pwd) \
	"$PATTERN_UTILITY_CONTAINER" \
	$@
