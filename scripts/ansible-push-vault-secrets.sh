#!/usr/bin/env bash
set -ex

SCRIPT=$(readlink -f "$0")
SCRIPTPATH=$(dirname "$SCRIPT")

export ANSIBLE_CONFIG="${SCRIPTPATH}/ansible.cfg"

ansible-playbook "$SCRIPTPATH/ansible_push_vault_secrets.yaml"
