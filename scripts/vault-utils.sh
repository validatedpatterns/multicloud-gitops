#!/usr/bin/env bash
set -eu

SCRIPT=$(readlink -f "$0")
SCRIPTPATH=$(dirname "$SCRIPT")
COMMONPATH=$(dirname "$SCRIPTPATH")
ANSIBLEPATH="$(dirname ${SCRIPTPATH})/ansible"
PLAYBOOKPATH="${ANSIBLEPATH}/playbooks"
export ANSIBLE_CONFIG="${ANSIBLEPATH}/ansible.cfg"

# Parse arguments
if [ $# -lt 1 ]; then
  echo "Specify at least the command ($#): $*"
  exit 1
fi

TASK="${1}"
OUTFILE=${2:-"$COMMONPATH"/vault.init}

if [ -z ${TASK} ]; then
	echo "Task is unset"
	exit 1
fi

case "${TASK}" in
  "vault_init")
    TAGS="vault_init,vault_unseal,vault_secrets_init"
    ;;
  *)
    TAGS="${TASK}"
esac

ansible-playbook -t "${TAGS}" -e output_file="${OUTFILE}" "${PLAYBOOKPATH}/vault/vault.yaml"
