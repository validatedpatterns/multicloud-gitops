#!/bin/bash

function is_available {
  command -v $1 >/dev/null 2>&1 || { echo >&2 "$1 is required but it's not installed. Aborting."; exit 1; }
}

function version {
    echo "$@" | awk -F. '{ printf("%d%03d%03d%03d\n", $1,$2,$3,$4); }'
}

if [ -z "$PATTERN_UTILITY_CONTAINER" ]; then
	PATTERN_UTILITY_CONTAINER="quay.io/hybridcloudpatterns/utility-container"
fi

readonly commands=(podman)
for cmd in ${commands[@]}; do is_available "$cmd"; done

UNSUPPORTED_PODMAN_VERSIONS="1.6 1.5"
PODMAN_VERSION_STR=$(podman --version)
for i in ${UNSUPPORTED_PODMAN_VERSIONS}; do
	# We add a space
	if echo "${PODMAN_VERSION_STR}" | grep -q -E "\b${i}"; then
		echo "Unsupported podman version. We recommend > 4.3.0"
		podman --version
		exit 1
	fi
done

# podman --version outputs:
# podman version 4.8.2
PODMAN_VERSION=$(echo "${PODMAN_VERSION_STR}" | awk '{ print $NF }')

# podman < 4.3.0 do not support keep-id:uid=...
if [ $(version "${PODMAN_VERSION}") -lt $(version "4.3.0") ]; then
    PODMAN_ARGS="-v ${HOME}:/root"
else
    # We do not rely on bash's $UID and $GID because on MacOSX $GID is not set
    MYNAME=$(id -n -u)
    MYUID=$(id -u)
    MYGID=$(id -g)
    PODMAN_ARGS="--passwd-entry ${MYNAME}:x:${MYUID}:${MYGID}:/pattern-home:/bin/bash --user ${MYUID}:${MYGID} --userns keep-id:uid=${MYUID},gid=${MYGID}"
fi

if [ -n "$KUBECONFIG" ]; then
    if [[ ! "${KUBECONFIG}" =~ ^$HOME* ]]; then
        echo "${KUBECONFIG} is pointing outside of the HOME folder, this will make it unavailable from the container."
        echo "Please move it somewhere inside your $HOME folder, as that is what gets bind-mounted inside the container"
        exit 1
    fi
fi

# Use /etc/pki by default and try a couple of fallbacks if it does not exist
if [ -d /etc/pki ]; then
    PKI_HOST_MOUNT="/etc/pki"
elif [ -d /etc/ssl ]; then
    PKI_HOST_MOUNT="/etc/ssl"
else
    PKI_HOST_MOUNT="/usr/share/ca-certificates"
fi

# Copy Kubeconfig from current environment. The utilities will pick up ~/.kube/config if set so it's not mandatory
# $HOME is mounted as itself for any files that are referenced with absolute paths
# $HOME is mounted to /root because the UID in the container is 0 and that's where SSH looks for credentials

podman run -it --rm --pull=newer \
	--security-opt label=disable \
	-e EXTRA_HELM_OPTS \
	-e EXTRA_PLAYBOOK_OPTS \
	-e KUBECONFIG \
	-v "${PKI_HOST_MOUNT}":/etc/pki:ro \
	-v "${HOME}":"${HOME}" \
	-v "${HOME}":/pattern-home \
	${PODMAN_ARGS} \
	${EXTRA_ARGS} \
	-w "$(pwd)" \
	"$PATTERN_UTILITY_CONTAINER" \
	$@
