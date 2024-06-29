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
Ansible plugin module that loads secrets and policies once parsed and pushes them
into a HashiCorp Vault in an OCP cluster. The values-secrets.yaml file is
expected to be in the following format:
---
# version is optional. When not specified it is assumed it is 2.0
version: 2.0

"""

import os
import time

import yaml
from ansible.module_utils.basic import AnsibleModule

ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = """
---
module: vault_load_parsed_secrets
short_description: Loads secrets into the HashiCorp Vault
version_added: "2.50"
author: "Martin Jackson"
description:
    - Takes parsed secrets objects and vault policies (as delivered by parse_secrets_info) and runs the commands to
      load them into a vault instance. The relevent metadata will exist in the parsed secrets object. Returns count
      of secrets injected.
options:
  parsed_secrets:
    description:
      - A structure containing the secrets, fields, and their metadata
    required: true
    type: dict
  vault_policies:
    description:
      - Vault policies to inject into the instance.
    required: true
    type: dict
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
"""

RETURN = """
"""

EXAMPLES = """
- name: Loads secrets file into the vault of a cluster
  vault_load_parsed_secrets:
    parsed_secrets: "{{ parsed_secrets_structure_from_parse_secrets_info }}"
    vault_policies: "{{ parsed_vault_policies_structure_from_parse_secrets_info }}"
"""


class VaultSecretLoader:
    def __init__(
        self,
        module,
        parsed_secrets,
        vault_policies,
        namespace,
        pod,
    ):
        self.module = module
        self.parsed_secrets = parsed_secrets
        self.vault_policies = vault_policies
        self.namespace = namespace
        self.pod = pod

    def _run_command(self, command, attempts=1, sleep=3, checkrc=True):
        """
        Runs a command on the host ansible is running on. A failing command
        will raise an exception in this function directly (due to check=True)

        Parameters:
          command(str): The command to be run.
          attempts(int): Number of times to retry in case of Error (defaults to 1)
          sleep(int): Number of seconds to wait in between retry attempts (defaults to 3s)

        Returns:
          ret(subprocess.CompletedProcess): The return value from run()
        """
        for attempt in range(attempts):
            ret = self.module.run_command(
                command,
                check_rc=checkrc,
                use_unsafe_shell=True,
                environ_update=os.environ.copy(),
            )
            if ret[0] == 0:
                return ret
            if attempt >= attempts - 1:
                return ret
            time.sleep(sleep)

    def _vault_secret_attr_exists(self, mount, prefix, secret_name, attribute):
        cmd = (
            f"oc exec -n {self.namespace} {self.pod} -i -- sh -c "
            f'"vault kv get -mount={mount} -field={attribute} {prefix}/{secret_name}"'
        )
        # we ignore stdout and stderr
        (ret, _, _) = self._run_command(cmd, attempts=1, checkrc=False)
        if ret == 0:
            return True

        return False

    def load_vault(self):
        injected_secret_count = 0

        self.inject_vault_policies()

        for secret_name, secret in self.parsed_secrets.items():
            self.inject_secret(secret_name, secret)
            injected_secret_count += 1

        return injected_secret_count

    def inject_field(
        self,
        secret_name,
        soverride,
        sbase64,
        sgenerate,
        spaths,
        svault_policies,
        fieldname,
        fieldvalue,
        mount,
        vault_prefixes,
        first=False,
    ):
        # Special cases:
        #   generate w|wo override
        #   path (w|wo b64)
        #
        #   inifile secrets will be resolved by parser
        #   values (including base64'd ones) will be resolved by parser
        # And we just ignore k8s or other fields

        override = True if fieldname in soverride else False
        b64 = True if fieldname in sbase64 else False
        generate = True if fieldname in sgenerate else False
        path = spaths.get(fieldname, False)
        prefixes = vault_prefixes
        verb = "put" if first else "patch"
        policy = svault_policies.get(fieldname, False)

        # "generate" secrets are created with policies and may be overridden or not
        if generate:
            gen_cmd = (
                f"vault read -field=password sys/policies/password/{policy}/generate"
            )
            if b64:
                gen_cmd += " | base64 --wrap=0"
            for prefix in prefixes:
                # if the override field is False and the secret attribute exists at the prefix then we just
                # skip, as we do not want to overwrite the existing secret
                if not override and self._vault_secret_attr_exists(
                    mount, prefix, secret_name, fieldname
                ):
                    continue
                cmd = (
                    f"oc exec -n {self.namespace} {self.pod} -i -- sh -c "
                    f'"{gen_cmd} | vault kv {verb} -mount={mount} {prefix}/{secret_name} {fieldname}=-"'
                )
                self._run_command(cmd, attempts=3)
            return

        if path:
            for prefix in prefixes:
                if b64:
                    b64_cmd = "| base64 --wrap=0"
                else:
                    b64_cmd = ""
                cmd = (
                    f"cat '{path}' | oc exec -n {self.namespace} {self.pod} -i -- sh -c "
                    f"'cat - {b64_cmd}> /tmp/vcontent'; "
                    f"oc exec -n {self.namespace} {self.pod} -i -- sh -c '"
                    f"vault kv {verb} -mount={mount} {prefix}/{secret_name} {fieldname}=@/tmp/vcontent; "
                    f"rm /tmp/vcontent'"
                )
                self._run_command(cmd, attempts=3)
            return

        for prefix in prefixes:
            cmd = (
                f"oc exec -n {self.namespace} {self.pod} -i -- sh -c "
                f"\"vault kv {verb} -mount={mount} {prefix}/{secret_name} {fieldname}='\"'{fieldvalue}'\"'\""
            )
            self._run_command(cmd, attempts=3)
        return

    def inject_secret(self, secret_name, secret):
        mount = secret.get("vault_mount", "secret")
        vault_prefixes = secret.get("vault_prefixes", ["hub"])

        counter = 0
        # In this structure, each field will have one value
        for fname, fvalue in secret.get("fields").items():
            self.inject_field(
                secret_name=secret_name,
                soverride=secret["override"],
                sbase64=secret["base64"],
                sgenerate=secret["generate"],
                spaths=secret["paths"],
                svault_policies=secret["vault_policies"],
                fieldname=fname,
                fieldvalue=fvalue,
                mount=mount,
                vault_prefixes=vault_prefixes,
                first=counter == 0,
            )
            counter += 1
        return

    def inject_vault_policies(self):
        for name, policy in self.vault_policies.items():
            cmd = (
                f"echo '{policy}' | oc exec -n {self.namespace} {self.pod} -i -- sh -c "
                f"'cat - > /tmp/{name}.hcl';"
                f"oc exec -n {self.namespace} {self.pod} -i -- sh -c 'vault write sys/policies/password/{name} "
                f" policy=@/tmp/{name}.hcl'"
            )
            self._run_command(cmd, attempts=3)


def run(module):
    """Main ansible module entry point"""
    results = dict(changed=False)

    args = module.params

    vault_policies = args.get("vault_policies", {})
    parsed_secrets = args.get("parsed_secrets", {})
    namespace = args.get("namespace", "vault")
    pod = args.get("pod", "vault-0")

    if vault_policies == {}:
        results["failed"] = True
        module.fail_json("Must pass vault_policies")

    if parsed_secrets == {}:
        results["failed"] = True
        module.fail_json("Must pass parsed_secrets")

    loader = VaultSecretLoader(
        module,
        parsed_secrets,
        vault_policies,
        namespace,
        pod,
    )

    nr_secrets = loader.load_vault()

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
