#!/bin/bash

function is_available {
  command -v $1 >/dev/null 2>&1 || { echo >&2 "$1 is required but it's not installed. Aborting."; exit 1; }
}

function version {
    echo "$@" | awk -F. '{ printf("%d%03d%03d%03d\n", $1,$2,$3,$4); }'
}

if [ -z "$PATTERN_UTILITY_CONTAINER" ]; then
	PATTERN_UTILITY_CONTAINER="quay.io/validatedpatterns/utility-container"
fi
# If PATTERN_DISCONNECTED_HOME is set it will be used to populate both PATTERN_UTILITY_CONTAINER
# and PATTERN_INSTALL_CHART automatically
if [ -n "${PATTERN_DISCONNECTED_HOME}" ]; then
    PATTERN_UTILITY_CONTAINER="${PATTERN_DISCONNECTED_HOME}/utility-container"
    PATTERN_INSTALL_CHART="oci://${PATTERN_DISCONNECTED_HOME}/pattern-install"
    echo "PATTERN_DISCONNECTED_HOME is set to ${PATTERN_DISCONNECTED_HOME}"
    echo "Setting the following variables:"
    echo "  PATTERN_UTILITY_CONTAINER: ${PATTERN_UTILITY_CONTAINER}"
    echo "  PATTERN_INSTALL_CHART: ${PATTERN_INSTALL_CHART}"
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
    PODMAN_ARGS="--passwd-entry ${MYNAME}:x:${MYUID}:${MYGID}::/pattern-home:/bin/bash --user ${MYUID}:${MYGID} --userns keep-id:uid=${MYUID},gid=${MYGID}"

fi

if [ -n "$KUBECONFIG" ]; then
    if [[ ! "${KUBECONFIG}" =~ ^$HOME* ]]; then
        echo "${KUBECONFIG} is pointing outside of the HOME folder, this will make it unavailable from the container."
        echo "Please move it somewhere inside your $HOME folder, as that is what gets bind-mounted inside the container"
        exit 1
    fi
fi

# Detect if we use podman machine. If we do not then we bind mount local host ssl folders
# if we are using podman machine then we do not bind mount anything (for now!)
REMOTE_PODMAN=$(podman system connection list | tail -n +2 | wc -l)
if [ $REMOTE_PODMAN -eq 0 ]; then # If we are not using podman machine we check the hosts folders
    # We check /etc/pki/tls because on ubuntu /etc/pki/fwupd sometimes
    # exists but not /etc/pki/tls and we do not want to bind mount in such a case
    # as it would find no certificates at all.
    if [ -d /etc/pki/tls ]; then
        PKI_HOST_MOUNT_ARGS="-v /etc/pki:/etc/pki:ro"
    elif [ -d /etc/ssl ]; then
        PKI_HOST_MOUNT_ARGS="-v /etc/ssl:/etc/ssl:ro"
    else
        PKI_HOST_MOUNT_ARGS="-v /usr/share/ca-certificates:/usr/share/ca-certificates:ro"
    fi
else
    PKI_HOST_MOUNT_ARGS=""
fi

# Copy Kubeconfig from current environment. The utilities will pick up ~/.kube/config if set so it's not mandatory
# $HOME is mounted as itself for any files that are referenced with absolute paths
# $HOME is mounted to /root because the UID in the container is 0 and that's where SSH looks for credentials

podman run -it --rm --pull=newer \
    --security-opt label=disable \
    -e EXTRA_HELM_OPTS \
    -e EXTRA_PLAYBOOK_OPTS \
    -e TARGET_ORIGIN \
    -e TARGET_SITE \
    -e TARGET_BRANCH \
    -e NAME \
    -e TOKEN_SECRET \
    -e TOKEN_NAMESPACE \
    -e VALUES_SECRET \
    -e KUBECONFIG \
    -e PATTERN_INSTALL_CHART \
    -e PATTERN_DISCONNECTED_HOME \
    -e DISABLE_VALIDATE_ORIGIN \
    -e K8S_AUTH_HOST \
    -e K8S_AUTH_VERIFY_SSL \
    -e K8S_AUTH_SSL_CA_CERT \
    -e K8S_AUTH_USERNAME \
    -e K8S_AUTH_PASSWORD \
    -e K8S_AUTH_TOKEN \
    ${PKI_HOST_MOUNT_ARGS} \
    -v "$(pwd -P)":"$(pwd -P)" \
    -v "${HOME}":"${HOME}" \
    -v "${HOME}":/pattern-home \
    ${PODMAN_ARGS} \
    ${EXTRA_ARGS} \
    -w "$(pwd -P)" \
    "$PATTERN_UTILITY_CONTAINER" \
    $@
