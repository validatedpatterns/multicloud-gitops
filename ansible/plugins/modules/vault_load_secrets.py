# Copyright 2022 Red Hat, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
Ansible plugin module that loads secrets from a yaml file and pushes them
inside the HashiCorp Vault in an OCP cluster. The values-secrets.yaml file is
expected to be in the following format:
---
# version is optional. When not specified it is assumed it is 1.0
version: 1.0

# These secrets will be pushed in the vault at secret/hub/test The vault will
# have secret/hub/test with secret1 and secret2 as keys with their associated
# values (secrets)
secrets:
  test:
    secret1: foo
    secret2: bar

# This will create the vault key secret/hub/testfoo which will have two
# properties 'b64content' and 'content' which will be the base64-encoded
# content and the normal content respectively
files:
  testfoo: ~/ca.crt

# These secrets will be pushed in the vault at secret/region1/test The vault will
# have secret/region1/test with secret1 and secret2 as keys with their associated
# values (secrets)
secrets.region1:
  test:
    secret1: foo1
    secret2: bar1

# This will create the vault key secret/region2/testbar which will have two
# properties 'b64content' and 'content' which will be the base64-encoded
# content and the normal content respectively
files.region2:
  testbar: ~/ca.crt
"""

import os

import yaml
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.load_secrets_common import parse_values, get_version, run_command, flatten


ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = """
---
module: vault_load_secrets
short_description: Loads secrets into the HashiCorp Vault
version_added: "2.11"
author: "Michele Baldessari"
description:
  - Takes a values-secret.yaml file and uploads the secrets into the HashiCorp Vault
options:
  values_secrets:
    description:
      - Path to the values-secrets file
    required: true
    type: str
  namespace:
    description:
      - Namespace where the vault is running
    required: false
    type: str
    default: vault
  pod:
    description:
      - Name of the vault pod to use to inject secrets
    required: false
    type: str
    default: vault-0
  basepath:
    description:
      - Vault's kv initial part of the path
    required: false
    type: str
    default: secret
  check_missing_secrets:
    description:
      - Validate the ~/values-secret.yaml file against the top-level
        values-secret-template.yaml and error out if secrets are missing
    required: false
    type: bool
    default: False
  values_secret_template:
    description:
      - Path of the values-secret-template.yaml file of the pattern
    required: false
    type: str
    default: ""
"""

RETURN = """
"""

EXAMPLES = """
- name: Loads secrets file into the vault of a cluster
  vault_load_secrets:
    values_secrets: ~/values-secret.yaml
"""




# NOTE(bandini): we shell out to oc exec it because of
# https://github.com/ansible-collections/kubernetes.core/issues/506 and
# https://github.com/kubernetes/kubernetes/issues/89899. Until those are solved
# it makes little sense to invoke the APIs via the python wrappers
def inject_secrets(module, syaml, namespace, pod, basepath, get_secrets_vault_paths_func):
    """
    Walks a secrets yaml object and injects all the secrets into the vault via 'oc exec' calls

    Parameters:
        module(AnsibleModule): The current AnsibleModule being used

        syaml(obj): The parsed yaml object representing the secrets

        namespace(str): The namespace in which the vault is

        pod(str): The pod name where the vault is

        basepath(str): The base string to which we concatenate the vault
        relative paths

    Returns:
        counter(int): The number of secrets injected
    """
    counter = 0
    for i in get_secrets_vault_paths_func(module, syaml, "secrets"):
        path = f"{basepath}/{i[1]}"
        for secret in syaml[i[0]] or []:
            properties = ""
            for key, value in syaml[i[0]][secret].items():
                properties += f"{key}='{value}' "
            properties = properties.rstrip()
            cmd = (
                f"oc exec -n {namespace} {pod} -i -- sh -c "
                f"\"vault kv put '{path}/{secret}' {properties}\""
            )
            run_command(cmd, attempts=3)
            counter += 1

    for i in get_secrets_vault_paths_func(module, syaml, "files"):
        path = f"{basepath}/{i[1]}"
        for filekey in syaml[i[0]] or []:
            file = os.path.expanduser(syaml[i[0]][filekey])
            cmd = (
                f"cat '{file}' | oc exec -n {namespace} {pod} -i -- sh -c "
                f"'cat - > /tmp/vcontent'; "
                f"oc exec -n {namespace} {pod} -i -- sh -c 'base64 --wrap=0 /tmp/vcontent | "
                f"vault kv put {path}/{filekey} b64content=- content=@/tmp/vcontent; "
                f"rm /tmp/vcontent'"
            )
            run_command(cmd, attempts=3)
            counter += 1
    return counter


def check_for_missing_secrets(module, syaml, values_secret_template):
    with open(values_secret_template, "r", encoding="utf-8") as file:
        template_yaml = yaml.safe_load(file.read())
    if template_yaml is None:
        module.fail_json(f"Template {values_secret_template} is empty")

    syaml_flat = flatten(syaml)
    template_flat = flatten(template_yaml)

    syaml_keys = set(syaml_flat.keys())
    template_keys = set(template_flat.keys())

    if template_keys <= syaml_keys:
        return

    diff = template_keys - syaml_keys
    module.fail_json(
        f"Values secret yaml is missing needed secrets from the templates: {diff}"
    )


def run(module):
    """Main ansible module entry point"""
    results = dict(changed=False)

    args = module.params
    values_secrets = os.path.expanduser(args.get("values_secrets"))
    basepath = args.get("basepath")
    namespace = args.get("namespace")
    pod = args.get("pod")
    check_missing_secrets = args.get("check_missing_secrets")
    values_secret_template = args.get("values_secret_template")
    if check_missing_secrets and values_secret_template == "":
        module.fail_json(
            "No values_secret_template defined and check_missing_secrets set to True"
        )

    if not os.path.exists(values_secrets):
        results["failed"] = True
        results["error"] = "Missing values-secrets.yaml file"
        results["msg"] = f"Values secrets file does not exist: {values_secrets}"
        module.exit_json(**results)

    syaml = parse_values(values_secrets)
    version = get_version(syaml)

    if version == "2.0":
        from ansible.module_utils.load_secrets_v2 import sanitize_values, get_secrets_vault_paths
    elif version == "1.0":
        from ansible.module_utils.load_secrets_v1 import sanitize_values, get_secrets_vault_paths
    else:
        module.fail_json(f"Version {version} is currently not supported")

    # In the future we can use the version field to manage different formats if needed
    secrets = sanitize_values(module, syaml)

    # If the user specified check_for_missing_secrets then we read values_secret_template
    # and check if there are any missing secrets
    if check_missing_secrets:
        check_for_missing_secrets(module, syaml, values_secret_template)

    nr_secrets = inject_secrets(module, secrets, namespace, pod, basepath, get_secrets_vault_paths)
    results["failed"] = False
    results["changed"] = True
    results["msg"] = f"{nr_secrets} secrets injected"
    module.exit_json(**results)


def main():
    """Main entry point where the AnsibleModule class is instantiated"""
    module = AnsibleModule(
        argument_spec=yaml.safe_load(DOCUMENTATION)["options"],
        supports_check_mode=False,
    )
    run(module)


if __name__ == "__main__":
    main()
