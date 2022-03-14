#!/usr/bin/env bash
set -e

SCRIPT=$(readlink -f "$0")
SCRIPTPATH=$(dirname "$SCRIPT")
ANSIBLEPATH="$(dirname ${SCRIPTPATH})/ansible"
PLAYBOOKPATH="${ANSIBLEPATH}/playbooks"
export ANSIBLE_CONFIG="${ANSIBLEPATH}/ansible.cfg"

ansible-playbook "$PLAYBOOKPATH/vault/push_secrets.yaml"
