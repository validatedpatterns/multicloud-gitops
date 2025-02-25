#!/usr/bin/env bash
set -eu

OUTPUTFILE=${1:-"~/.kube/config"}

get_abs_filename() {
  # $1 : relative filename
  echo "$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
}

SCRIPT=$(get_abs_filename "$0")
SCRIPTPATH=$(dirname "${SCRIPT}")
COMMONPATH=$(dirname "${SCRIPTPATH}")
PATTERNPATH=$(dirname "${COMMONPATH}")

EXTRA_PLAYBOOK_OPTS="${EXTRA_PLAYBOOK_OPTS:-}"

ansible-playbook -e pattern_dir="${PATTERNPATH}" -e kubeconfig_file="${OUTPUTFILE}" ${EXTRA_PLAYBOOK_OPTS} "rhvp.cluster_utils.write-token-kubeconfig"
