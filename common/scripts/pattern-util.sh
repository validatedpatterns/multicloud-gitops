#!/bin/bash

if [ -z "$PATTERN_UTILITY_CONTAINER" ]; then
	PATTERN_UTILITY_CONTAINER="quay.io/hybridcloudpatterns/utility-container"
fi

UNSUPPORTED_PODMAN_VERSIONS="1.6 1.5"
for i in ${UNSUPPORTED_PODMAN_VERSIONS}; do
	# We add a space
	if podman --version | grep -q -E "\b${i}"; then
		echo "Unsupported podman version. We recommend >= 4.2.0"
		podman --version
		exit 1
	fi
done

if [ -n "$KUBECONFIG" ]; then
    if [[ ! "${KUBECONFIG}" =~ ^$HOME* ]]; then
        echo "${KUBECONFIG} is pointing outside of the HOME folder, this will make it unavailable from the container."
        echo "Please move it somewhere inside your $HOME folder, as that is what gets bind-mounted inside the container"
        exit 1
    fi
fi
# Copy Kubeconfig from current environment. The utilities will pick up ~/.kube/config if set so it's not mandatory
# $HOME is mounted as itself for any files that are referenced with absolute paths
# $HOME is mounted to /root because the UID in the container is 0 and that's where SSH looks for credentials

# Do not quote the ${KUBECONF_ENV} below, otherwise we will pass '' to podman
# which will be confused
podman run -it --rm --pull=newer \
	--security-opt label=disable \
	-e EXTRA_HELM_OPTS \
	-e KUBECONFIG \
	-v "${HOME}":"${HOME}" \
	-v "${HOME}":/pattern-home \
	-v "${HOME}":/root \
	-w "$(pwd)" \
	"$PATTERN_UTILITY_CONTAINER" \
	$@
