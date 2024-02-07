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
ANSIBLEPATH="$(dirname ${SCRIPTPATH})/ansible"
PLAYBOOKPATH="${ANSIBLEPATH}/playbooks"

export ANSIBLE_CONFIG="${ANSIBLEPATH}/ansible.cfg"

if [ "$#" -ge 1 ]; then
    export VALUES_SECRET=$(get_abs_filename "${1}")
fi

if [[ "$#" == 2 ]]; then
    SECRETS_BACKING_STORE="$2"
else
    SECRETS_BACKING_STORE="$($SCRIPTPATH/determine-secretstore-backend.sh)"
fi

PATTERN_NAME=$(basename "`pwd`")

ansible-playbook -e pattern_name="${PATTERN_NAME}" -e pattern_dir="${PATTERNPATH}" -e secrets_backing_store="${SECRETS_BACKING_STORE}" -e override_no_log=false "${PLAYBOOKPATH}/process_secrets/display_secrets_info.yml"
