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
SECRETS_BACKING_STORE="$($SCRIPTPATH/determine-secretstore-backend.sh)"

EXTRA_PLAYBOOK_OPTS="${EXTRA_PLAYBOOK_OPTS:-}"

ansible-playbook -e pattern_name="${PATTERN_NAME}" -e pattern_dir="${PATTERNPATH}" -e secrets_backing_store="${SECRETS_BACKING_STORE}" ${EXTRA_PLAYBOOK_OPTS} "rhvp.cluster_utils.process_secrets"
