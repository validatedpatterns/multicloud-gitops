#!/bin/sh

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

# Copy Kubeconfig from current environment. The utilities will pick up ~/.kube/config if set so it's not mandatory
# $HOME is mounted as itself for any files that are referenced with absolute paths
# $HOME is mounted to /root because the UID in the container is 0 and that's where SSH looks for credentials

# We must pass -e KUBECONFIG *only* if it is set, otherwise we end up passing
# KUBECONFIG="" which then will confuse ansible
KUBECONF_ENV=""
if [ -n "$KUBECONFIG" ]; then
	KUBECONF_ENV="-e KUBECONFIG=${KUBECONFIG}"
fi

# Do not quote the ${KUBECONF_ENV} below, otherwise we will pass '' to podman
# which will be confused
podman run -it \
	--security-opt label=disable \
	${KUBECONF_ENV} \
	-v "${HOME}":"${HOME}" \
	-v "${HOME}":/pattern-home \
	-v "${HOME}":/root \
	-w "$(pwd)" \
	"$PATTERN_UTILITY_CONTAINER" \
	$@
