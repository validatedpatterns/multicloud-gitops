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
import time

from ansible.module_utils.load_secrets_common import (
    find_dupes,
    get_ini_value,
    get_version,
)

default_vp_vault_policies = {
    "validatedPatternDefaultPolicy": (
        "length=20\n"
        'rule "charset" { charset = "abcdefghijklmnopqrstuvwxyz" min-chars = 1 }\n'
        'rule "charset" { charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" min-chars = 1 }\n'
        'rule "charset" { charset = "0123456789" min-chars = 1 }\n'
        'rule "charset" { charset = "!@#%^&*" min-chars = 1 }\n'
    )
}


class LoadSecretsV2:
    def __init__(self, module, syaml, namespace, pod):
        self.module = module
        self.namespace = namespace
        self.pod = pod
        self.syaml = syaml

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

    def _get_backingstore(self):
        """
        Return the backingStore: of the parsed yaml object. If it does not exist
        return 'vault'

        Returns:
            ret(str): The value of the top-level 'backingStore:' key
        """
        return str(self.syaml.get("backingStore", "vault"))

    def _get_vault_policies(self, enable_default_vp_policies=True):
        # We start off with the hard-coded default VP policy and add the user-defined ones
        if enable_default_vp_policies:
            policies = default_vp_vault_policies.copy()
        else:
            policies = {}
        policies.update(self.syaml.get("vaultPolicies", {}))
        return policies

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

    def _get_field_ini_file(self, f):
        return f.get("ini_file", None)

    def _get_field_kind(self, f):
        # value: null will be interpreted with None, so let's just
        # check for the existence of the field, as we use 'value: null' to say
        # "we want a value/secret and not a file path"
        found = []
        for i in ["value", "path", "ini_file"]:
            if i in f:
                found.append(i)

        if len(found) > 1:  # you can only have one of value, path and ini_file
            self.module.fail_json(f"Both '{found[0]}' and '{found[1]}' cannot be used")

        if len(found) == 0:
            return ""
        return found[0]

    def _get_field_prompt(self, f):
        return f.get("prompt", None)

    def _get_field_base64(self, f):
        return bool(f.get("base64", False))

    def _get_field_override(self, f):
        return bool(f.get("override", False))

    # This function could use some rewriting and it should call a specific validation function
    # for each type (value, path, ini_file)
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
        ini_file = self._get_field_ini_file(f)
        kind = self._get_field_kind(f)
        if kind == "ini_file":
            # if we are using ini_file then at least ini_key needs to be defined
            # ini_section defaults to 'default' when omitted
            ini_key = f.get("ini_key", None)
            if ini_key is None:
                return (
                    False,
                    "ini_file requires at least ini_key to be defined",
                )

        # Test if base64 is a correct boolean (defaults to False)
        _ = self._get_field_base64(f)
        _ = self._get_field_override(f)

        vault_policy = f.get("vaultPolicy", None)
        if vault_policy is not None and vault_policy not in self._get_vault_policies():
            return (
                False,
                f"Secret has vaultPolicy set to {vault_policy} but no such policy exists",
            )

        if on_missing_value in ["error"]:
            if (
                (value is None or len(value) < 1)
                and (path is None or len(path) < 1)
                and (ini_file is None or len(ini_file) < 1)
            ):
                return (
                    False,
                    "Secret has onMissingValue set to 'error' and has neither value nor path nor ini_file set",
                )
            if path is not None and not os.path.isfile(os.path.expanduser(path)):
                return (False, f"Field has non-existing path: {path}")

            if ini_file is not None and not os.path.isfile(
                os.path.expanduser(ini_file)
            ):
                return (False, f"Field has non-existing ini_file: {ini_file}")

            if "override" in f:
                return (
                    False,
                    "'override' attribute requires 'onMissingValue' to be set to 'generate'",
                )

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
            # When we prompt, the user needs to set one of the following:
            # - value: null # prompt for a secret without a default value
            # - value: 123 # prompt for a secret but use a default value
            # - path: null # prompt for a file path without a default value
            # - path: /tmp/ca.crt # prompt for a file path with a default value
            if "value" not in f and "path" not in f:
                return (
                    False,
                    "Secret has onMissingValue set to 'prompt' but has no value nor path fields",
                )

            if "override" in f:
                return (
                    False,
                    "'override' attribute requires 'onMissingValue' to be set to 'generate'",
                )

        return (True, "")

    def _validate_secrets(self):
        secrets = self._get_secrets()
        if len(secrets) == 0:
            self.module.fail_json("No secrets found")

        names = []
        for s in secrets:
            # These fields are mandatory
            for i in ["name"]:
                try:
                    _ = s[i]
                except KeyError:
                    return (False, f"Secret {s['name']} is missing {i}")
            names.append(s["name"])

            vault_prefixes = s.get("vaultPrefixes", ["hub"])
            # This checks for the case when vaultPrefixes: is specified but empty
            if vault_prefixes is None or len(vault_prefixes) == 0:
                return (False, f"Secret {s['name']} has empty vaultPrefixes")

            fields = s.get("fields", [])
            if len(fields) == 0:
                return (False, f"Secret {s['name']} does not have any fields")

            field_names = []
            for i in fields:
                (ret, msg) = self._validate_field(i)
                if not ret:
                    return (False, msg)
                field_names.append(i["name"])
            field_dupes = find_dupes(field_names)
            if len(field_dupes) > 0:
                return (False, f"You cannot have duplicate field names: {field_dupes}")

        dupes = find_dupes(names)
        if len(dupes) > 0:
            return (False, f"You cannot have duplicate secret names: {dupes}")
        return (True, "")

    def inject_vault_policies(self):
        for name, policy in self._get_vault_policies().items():
            cmd = (
                f"echo '{policy}' | oc exec -n {self.namespace} {self.pod} -i -- sh -c "
                f"'cat - > /tmp/{name}.hcl';"
                f"oc exec -n {self.namespace} {self.pod} -i -- sh -c 'vault write sys/policies/password/{name} "
                f" policy=@/tmp/{name}.hcl'"
            )
            self._run_command(cmd, attempts=3)

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

        backing_store = self._get_backingstore()
        if backing_store != "vault":  # we currently only support vault
            self.module.fail_json(
                f"Currently only the 'vault' backingStore is supported: {backing_store}"
            )

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
            prompt = self._get_field_prompt(field)
            if prompt is None:
                prompt = f"Type secret for {name}/{field['name']}: "
            value = self._get_field_value(field)
            if value is not None:
                prompt += f" [{value}]"
            prompt += ": "
            return getpass.getpass(prompt)
        return None

    def _get_file_path(self, name, field):
        on_missing_value = self._get_field_on_missing_value(field)
        if on_missing_value == "error":
            return os.path.expanduser(field.get("path"))
        elif on_missing_value == "prompt":
            prompt = self._get_field_prompt(field)
            path = self._get_field_path(field)
            if path is None:
                path = ""

            if prompt is None:
                text = f"Type path for file {name}/{field['name']} [{path}]: "
            else:
                text = f"{prompt} [{path}]: "

            newpath = getpass.getpass(text)
            if newpath == "":  # Set the default if no string was entered
                newpath = path

            if os.path.isfile(os.path.expanduser(newpath)):
                return newpath
            self.module.fail_json(f"File {newpath} not found, exiting")

        self.module.fail_json("File with wrong onMissingValue")

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

    def _inject_field(self, secret_name, f, mount, prefixes, first=False):
        on_missing_value = self._get_field_on_missing_value(f)
        override = self._get_field_override(f)
        kind = self._get_field_kind(f)
        # If we're generating the password then we just push the secret in the vault directly
        verb = "put" if first else "patch"
        b64 = self._get_field_base64(f)
        if kind in ["value", ""]:
            if on_missing_value == "generate":
                if kind == "path":
                    self.module.fail_json(
                        "You cannot have onMissingValue set to 'generate' with a path"
                    )
                vault_policy = f.get("vaultPolicy")
                gen_cmd = f"vault read -field=password sys/policies/password/{vault_policy}/generate"
                if b64:
                    gen_cmd += " | base64 --wrap=0"
                for prefix in prefixes:
                    # if the override field is False and the secret attribute exists at the prefix then we just
                    # skip, as we do not want to overwrite the existing secret
                    if not override and self._vault_secret_attr_exists(
                        mount, prefix, secret_name, f["name"]
                    ):
                        continue
                    cmd = (
                        f"oc exec -n {self.namespace} {self.pod} -i -- sh -c "
                        f"\"{gen_cmd} | vault kv {verb} -mount={mount} {prefix}/{secret_name} {f['name']}=-\""
                    )
                    self._run_command(cmd, attempts=3)
                return

            # If we're not generating the secret inside the vault directly we either read it from the file ("error")
            # or we are prompting the user for it
            secret = self._get_secret_value(secret_name, f)
            if b64:
                secret = base64.b64encode(secret.encode()).decode("utf-8")
            for prefix in prefixes:
                cmd = (
                    f"oc exec -n {self.namespace} {self.pod} -i -- sh -c "
                    f"\"vault kv {verb} -mount={mount} {prefix}/{secret_name} {f['name']}='{secret}'\""
                )
                self._run_command(cmd, attempts=3)

        elif kind == "path":  # path. we upload files
            # If we're generating the password then we just push the secret in the vault directly
            verb = "put" if first else "patch"
            path = self._get_file_path(secret_name, f)
            for prefix in prefixes:
                if b64:
                    b64_cmd = "| base64 --wrap=0 "
                else:
                    b64_cmd = ""
                cmd = (
                    f"cat '{path}' | oc exec -n {self.namespace} {self.pod} -i -- sh -c "
                    f"'cat - {b64_cmd}> /tmp/vcontent'; "
                    f"oc exec -n {self.namespace} {self.pod} -i -- sh -c '"
                    f"vault kv {verb} -mount={mount} {prefix}/{secret_name} {f['name']}=@/tmp/vcontent; "
                    f"rm /tmp/vcontent'"
                )
                self._run_command(cmd, attempts=3)
        elif kind == "ini_file":  # ini_file. we parse an ini_file
            verb = "put" if first else "patch"
            ini_file = os.path.expanduser(f.get("ini_file"))
            ini_section = f.get("ini_section", "default")
            ini_key = f.get("ini_key")
            secret = get_ini_value(ini_file, ini_section, ini_key)
            if b64:
                secret = base64.b64encode(secret.encode()).decode("utf-8")
            for prefix in prefixes:
                cmd = (
                    f"oc exec -n {self.namespace} {self.pod} -i -- sh -c "
                    f"\"vault kv {verb} -mount={mount} {prefix}/{secret_name} {f['name']}='{secret}'\""
                )
                self._run_command(cmd, attempts=3)

    # This assumes that self.sanitize_values() has already been called
    # so we do a lot less validation as it has already happened
    def inject_secrets(self):
        # This must come first as some passwords might depend on vault policies to exist.
        # It is a noop when no policies are defined
        self.inject_vault_policies()
        secrets = self._get_secrets()

        total_secrets = 0  # Counter for all the secrets uploaded
        for s in secrets:
            counter = 0  # This counter is to use kv put on first secret and kv patch on latter
            sname = s.get("name")
            fields = s.get("fields", [])
            mount = s.get("vaultMount", "secret")
            vault_prefixes = s.get("vaultPrefixes", ["hub"])
            for i in fields:
                self._inject_field(sname, i, mount, vault_prefixes, counter == 0)
                counter += 1
                total_secrets += 1

        return total_secrets
