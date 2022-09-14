#!/bin/sh

if [ -z "$PATTERN_UTILITY_CONTAINER" ]; then
	PATTERN_UTILITY_CONTAINER="quay.io/hybridcloudpatterns/hybridcloudpatterns-utility-ee"
fi

# Copy Kubeconfig from current environment. The utilities will pick up ~/.kube/config if set so it's not mandatory
# /home/runner is the normal homedir
# $HOME is mounted as itself for any files that are referenced with absolute paths
# $HOME is mounted to /root because the UID in the container is 0 and that's where SSH looks for credentials

podman run -it \
	--security-opt label=disable \
	-e KUBECONFIG="${KUBECONFIG}" \
	-v ${HOME}:/home/runner \
	-v ${HOME}:${HOME} \
	-v ${HOME}:/root \
	-w $(pwd) \
	"$PATTERN_UTILITY_CONTAINER" \
	$@
