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
import getpass
import os

from ansible.module_utils.load_secrets_common import (
    get_input,
    get_version,
    parse_values,
    run_command,
)


class LoadSecretsV2:
    def __init__(self, module, values_secrets, namespace, pod, values_secret_template):
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

    def _get_field_path(self, f):
        return f.get("path", None)

    def _get_field_kind(self, f):
        value = self._get_field_value(f)
        path = self._get_field_path(f)
        if value is not None and path is not None:
            return (False, "Both 'value' and 'path' cannot be used")
        if path is not None:
            return "path"
        return "value"

    def _get_field_description(self, f):
        return f.get("description", None)

    def _get_field_base64(self, f):
        return bool(f.get("base64", False))

    def _validate_field(self, f):
        # These fields are mandatory
        try:
            _ = f["name"]
        except KeyError:
            return (False, f"Field {f} is missing name")

        on_missing_value = self._get_field_on_missing_value(f)
        if on_missing_value not in ["error", "generate", "prompt"]:
            return (False, f"onMissingValue: {on_missing_value} is invalid")

        value = self._get_field_value(f)
        path = self._get_field_path(f)
        _ = self._get_field_kind(f)

        # Test is base64 is a correct boolean (defaults to False)
        _ = self._get_field_base64(f)

        vault_policy = f.get("vaultPolicy", None)
        if vault_policy is not None and vault_policy not in self._get_vault_policies():
            return (
                False,
                f"Secret has vaultPolicy set to {vault_policy} but no such policy exists",
            )

        if on_missing_value in ["error"]:
            if (value is None or len(value) < 1) and (path is None or len(path) < 1):
                return (
                    False,
                    "Secret has onMissingValue set to 'error' and has neither value nor path set",
                )
            if path is not None and not os.path.isfile(os.path.expanduser(path)):
                return (False, f"Field has non-existing path: {path}")

        if on_missing_value in ["generate"]:
            if value is not None:
                return (
                    False,
                    "Secret has onMissingValue set to 'generate' but has a value set",
                )
            if path is not None:
                return (
                    False,
                    "Secret has onMissingValue set to 'generate' but has a path set",
                )
            if vault_policy is None:
                return (
                    False,
                    "Secret has no vaultPolicy but onMissingValue is set to 'generate'",
                )

        if on_missing_value in ["prompt"]:
            if value is not None:
                return (
                    False,
                    "Secret has onMissingValue set to 'prompt' but has a value set",
                )
            if value is None and path is not None:
                return (
                    False,
                    "Secret has onMissingValue set to 'prompt' but has value set to null and path set to a value",
                )

        return (True, "")

    def _validate_secrets(self):
        secrets = self._get_secrets()
        if len(secrets) == 0:
            self.module.fail_json("No secrets found")

        for s in secrets:
            # These fields are mandatory
            for i in ["name", "vaultPrefixes"]:
                try:
                    _ = s[i]
                except KeyError:
                    return (False, f"Secret {s['name']} is missing {i}")

            vault_prefixes = s.get("vaultPrefixes", [])
            if vault_prefixes is None or len(vault_prefixes) == 0:
                return (False, f"Secret {s['name']} has empty vaultPrefixes")

            fields = s.get("fields", [])
            if len(fields) == 0:
                return (False, f"Secret {s['name']} does not have any fields")

            for i in fields:
                (ret, msg) = self._validate_field(i)
                if not ret:
                    return (False, msg)

        return (True, "")

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
        # vault_policies = self._get_vault_policies()

        (ret, msg) = self._validate_secrets()
        if not ret:
            self.module.fail_json(msg)

    def _get_secret_value(self, name, field):
        on_missing_value = self._get_field_on_missing_value(field)
        # We cannot use match + case as RHEL8 has python 3.9 (it needs 3.10)
        # We checked for errors in _validate_secrets() already
        if on_missing_value == "error":
            return field.get("value")
        elif on_missing_value == "prompt":
            prompt = self._get_field_description(field)
            if prompt is None:
                prompt = f"Type secret for {name}/{field['name']}: "
            return getpass.getpass(prompt)
        return None

    def _get_file_path(self, name, field):
        on_missing_value = self._get_field_on_missing_value(field)
        if on_missing_value == "error":
            return field.get("path")
        elif on_missing_value == "prompt":
            prompt = self._get_field_description(field)
            path = self._get_field_path(field)
            if path is None:
                path = ""

            if prompt is None:
                text = f"Type path for file {name}/{field['name']} [{path}]: "
            else:
                text = f"{prompt} [{path}]: "

            path = get_input(text)

            if os.path.isfile(os.path.expanduser(path)):
                return path
            self.module.fail_json("File not found, exiting")

        self.module.fail_json("File with wrong onMissingValue")

    def _inject_field(self, secret_name, f, mount, prefixes, first=False):
        on_missing_value = self._get_field_on_missing_value(f)
        kind = self._get_field_kind(f)
        # If we're generating the password then we just push the secret in the vault directly
        verb = "put" if first else "patch"
        b64 = self._get_field_base64(f)
        if kind == "value":
            if on_missing_value == "generate":
                vault_policy = f.get("vaultPolicy")
                gen_cmd = f"vault read -field=password sys/policies/password/{vault_policy}/generate"
                if b64:
                    gen_cmd += " | base64 --wrap=0"
                for prefix in prefixes:
                    cmd = (
                        f"oc exec -n {self.namespace} {self.pod} -i -- sh -c "
                        f"\"{gen_cmd} | vault kv {verb} -mount={mount} {prefix}/{secret_name} {f['name']}=-\""
                    )
                    run_command(cmd)
                return

            # If we're not generating the secret inside the vault directly we either read it from the file ("error")
            # or we are prompting the user for it
            secret = self._get_secret_value(secret_name, f)
            if b64:
                secret = base64.b64encode(secret.encode())
            for prefix in prefixes:
                cmd = (
                    f"oc exec -n {self.namespace} {self.pod} -i -- sh -c "
                    f"\"vault kv {verb} -mount={mount} {prefix}/{secret_name} {f['name']}={secret}\""
                )
                run_command(cmd)

        else:  # path. we upload files
            # If we're generating the password then we just push the secret in the vault directly
            verb = "put" if first else "patch"
            path = self._get_file_path(secret_name, f)
            for prefix in prefixes:
                if b64:
                    b64_cmd = "base64 --wrap=0 /tmp/vcontent | "
                else:
                    b64_cmd = ""
                cmd = (
                    f"cat '{path}' | oc exec -n {self.namespace} {self.pod} -i -- sh -c "
                    f"'cat - > /tmp/vcontent'; "
                    f"oc exec -n {self.namespace} {self.pod} -i -- sh -c '{b64_cmd}"
                    f"vault kv {verb} -mount={mount} {prefix}/{secret_name} {f['name']}=/tmp/vcontent; "
                    f"rm /tmp/vcontent'"
                )
                run_command(cmd)

    # This assumes that self.sanitize_values() has already been called
    # so we do a lot less validation as it has already happened
    def inject_secrets(self):
        # This must come first as some passwords might depend on vault policies to exist.
        # It is a noop when no policies are defined
        self.inject_vault_policies()
        secrets = self._get_secrets()

        counter = 0
        for s in secrets:
            sname = s.get("name")
            fields = s.get("fields", [])
            mount = s.get("vaultMount", "secret")
            vault_prefixes = s.get("vaultPrefixes", [])
            for i in fields:
                self._inject_field(sname, i, mount, vault_prefixes, counter == 0)
                counter += 1

        return counter
