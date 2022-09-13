#!/bin/bash
set -eu

# Get the version of the dependency and then unquote it
TMPVER=$(sed -e '1,/^version:/ d' "Chart.yaml" | grep "version:" | awk '{ print $2 }')
VERSION=$(eval echo "${TMPVER}")

# Chart format is vault-0.21.0.tgz
NAME="vault"
TAR="${NAME}-${VERSION}.tgz"
CHARTDIR="charts"

if [ ! -f "${CHARTDIR}/${TAR}" ]; then
	echo "Charts $TAR not found"
	exit 1
fi

pushd "${CHARTDIR}"
rm -rf "${NAME}"
tar xfz "${TAR}"
pushd "${NAME}"
patch -p1 < ../../patch-server-route.diff
popd
tar cvfz "${TAR}" "${NAME}"
rm -rf "${NAME}"
popd
