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
ANSIBLEPATH="$(dirname ${SCRIPTPATH})/ansible"
PLAYBOOKPATH="${ANSIBLEPATH}/playbooks"
export ANSIBLE_CONFIG="${ANSIBLEPATH}/ansible.cfg"

ansible-playbook -e pattern_dir="${PATTERNPATH}" -e kubeconfig_file="${OUTPUTFILE}" "${PLAYBOOKPATH}/write-token-kubeconfig/write-token-kubeconfig.yml"
