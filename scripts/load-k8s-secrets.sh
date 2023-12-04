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

PATTERN_NAME=${1:-$(basename "`pwd`")}

ansible-playbook -e pattern_name="${PATTERN_NAME}" -e pattern_dir="${PATTERNPATH}" "${PLAYBOOKPATH}/k8s_secrets/k8s_secrets.yml"
