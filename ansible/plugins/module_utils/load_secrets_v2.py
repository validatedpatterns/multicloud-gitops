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
Module that implements V2 of the values-secret.yaml spec
"""

import base64
import os

import yaml
from ansible.module_utils.load_secrets_common import get_version, flatten, parse_values, run_command

class LoadSecretsV2:
    def __init__(
        self, module, values_secrets, basepath, namespace, pod, values_secret_template
    ):
        self.module = module
        self.basepath = basepath
        self.namespace = namespace
        self.pod = pod
        self.values_secret_template = values_secret_template
        self.syaml = parse_values(values_secrets)

    def _get_vault_policies(self):
        return self.syaml.get("vaultPolicies", {})


    def inject_vault_policies(self):
        for name, policy in self._get_vault_policies().items():
            cmd = (
                f"echo '{policy}' | oc exec -n {self.namespace} {self.pod} -i -- sh -c "
                f"'cat - > /tmp/{name}.hcl';"
                f"oc exec -n {self.namespace} {self.pod} -i -- sh -c 'vault write sys/policies/password/{name} "
                f" policy=@/tmp/{name}.hcl'"
            )
            run_command(cmd, attempts=3)


    def sanitize_values(self):
        """
        Sanitizes the secrets YAML object version 2.0

        Parameters:

        Returns:
            Nothing: Updates self.syaml(obj) if needed
        """
        v = get_version(self.syaml)
        if v != "2.0":
            self.module.fail_json(f"Version is not 2.0: {v}")

        # Check if they are sane somehow?
        vault_policies = self._get_vault_policies()


    def get_secrets_vault_paths(self, keyname):
        return

    def inject_secrets(self):
        # This must come first as some passwords might depend on vault policies to exist.
        # It is a noop when no policies are defined
        self.inject_vault_policies()
        return
