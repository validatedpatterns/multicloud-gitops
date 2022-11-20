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
        self, module, values_secrets, namespace, pod, values_secret_template
    ):
        self.module = module
        self.namespace = namespace
        self.pod = pod
        self.values_secret_template = values_secret_template
        self.syaml = parse_values(values_secrets)

    def _get_vault_policies(self):
        return self.syaml.get("vaultPolicies", {})

    def _get_secrets(self):
        return self.syaml.get("secrets", {})

    def _get_field_on_missing_value(self, f):
        # By default if 'onMissingValue' is missing we assume we need to
        # error out whenever the value is missing
        return f.get("onMissingValue", "error")

    def _get_field_value(self, f):
        return f.get("value", None)

    def _validate_field(self, f):
        # These fields are mandatory
        try:
            name = f["name"]
        except KeyError:
            return (False, f"Field {f} is missing name")

        on_missing_value = self._get_field_on_missing_value(f)
        if on_missing_value not in ["error", "generate", "prompt"]:
            return (False, f"onMissingValue: {on_missing_value} is invalid")

        value = self._get_field_value(f)
        if on_missing_value in ["error"] and (value == None or len(value) < 1):
            return (False, "Secret has onMissingValue set to 'error' and has no value set")

        if on_missing_value in ["generate", "prompt"] and value != None:
            return (False, "Secret has onMissingValue set to 'generate' or 'prompt' but has a value set")

        vault_policy = f.get("vaultPolicy", None)
        if vault_policy != None and vault_policy not in self._get_vault_policies():
            return (False, f"Secret has vaultPolicy set to {vault_policy} but no such policy exists")

        return (True, '')

    def _validate_file(self, f):
        # These fields are mandatory
        try:
            name = f["name"]
        except KeyError:
            return (False, f"Field {f} is missing name")

        on_missing_value = self._get_field_on_missing_value(f)
        if on_missing_value not in ["error", "prompt"]:
            return (False, f"onMissingValue: {on_missing_value} is invalid")

        path = f.get("path", None)
        if on_missing_value in ["error"] and path == None:
            return (False, f"{name} has unset path")

        if on_missing_value in ["prompt"] and path != None:
            return (False, f"{name} has onMissingValue set to 'prompt' but path is set")

        if on_missing_value in ["prompt"]:
            # FIXME: implement proper prompting
            path = "/tmp/ca.crt"
        if not os.path.isfile(os.path.expanduser(path)):
            return (False, f"{name} has non-existing path: {path}")
        return (True, '')

    def _validate_secrets(self):
        secrets = self._get_secrets()
        if len(secrets) == 0:
            self.module.fail_json(f"No secrets found")

        for s in secrets:
            # These fields are mandatory
            for i in ["name", "vaultPrefixes"]:
                try:
                    tmp = s[i]
                except KeyError:
                    return (False, f"Secret {s} is missing {i}")

            fields = s.get("fields", [])
            files = s.get("files", [])
            if len(fields) == 0 and len(files) == 0:
                return (False, f"Secret {s} does not have either fields nor files")

            for i in fields:
                (ret, msg) = self._validate_field(i)
                if not ret:
                    return (False, msg)

            for i in files:
                (ret, msg) = self._validate_file(i)
                if not ret:
                    return (False, msg)
        return (True, '')


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

        # Check if the vault_policies are sane somehow?
        vault_policies = self._get_vault_policies()


    def get_secrets_vault_paths(self, keyname):
        return

    def inject_secrets(self):
        (ret, msg) = self._validate_secrets()
        if not ret:
            self.module.fail_json(msg)

        # This must come first as some passwords might depend on vault policies to exist.
        # It is a noop when no policies are defined
        self.inject_vault_policies()

        return
