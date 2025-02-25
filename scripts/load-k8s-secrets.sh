#!/usr/bin/env bash
set -eu

get_abs_filename() {
  # $1 : relative filename
  echo "$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
}

SCRIPT=$(get_abs_filename "$0")
SCRIPTPATH=$(dirname "${SCRIPT}")
COMMONPATH=$(dirname "${SCRIPTPATH}")
PATTERNPATH=$(dirname "${COMMONPATH}")

PATTERN_NAME=${1:-$(basename "`pwd`")}

EXTRA_PLAYBOOK_OPTS="${EXTRA_PLAYBOOK_OPTS:-}"

ansible-playbook -e pattern_name="${PATTERN_NAME}" -e pattern_dir="${PATTERNPATH}" ${EXTRA_PLAYBOOK_OPTS} "rhvp.cluster_utils.k8s_secrets"
