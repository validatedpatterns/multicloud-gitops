# Copyright 2022, 2023 Red Hat, Inc.
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
    find_dupes,
    get_ini_value,
    get_version,
    stringify_dict,
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

secret_store_namespace = "validated-patterns-secrets"


class ParseSecretsV2:

    def __init__(self, module, syaml, secrets_backing_store):
        self.module = module
        self.syaml = syaml
        self.secrets_backing_store = str(secrets_backing_store)
        self.secret_store_namespace = None
        self.parsed_secrets = {}
        self.kubernetes_secret_objects = []
        self.vault_policies = {}

    def _get_backingstore(self):
        """
        Backing store is now influenced by the caller more than the file. Setting
        Return the backingStore: of the parsed yaml object. In most cases the file
        key was not set anyway - since vault was the only supported option. Since
        we are introducing new options now, this method of defining behavior is
        deprecated, but if the file key is included it must match the option defined
        by values-global in the pattern, or there is an error. The default remains
        'vault' if the key is unspecified.

        Returns:
            ret(str): The value of the top-level 'backingStore:' key
        """
        file_backing_store = str(self.syaml.get("backingStore", "unset"))

        if file_backing_store == "unset":
            pass
        else:
            if file_backing_store != self.secrets_backing_store:
                self.module.fail_json(
                    f"Secrets file specifies '{file_backing_store}' backend but pattern config "
                    f"specifies '{self.secrets_backing_store}'."
                )

        return self.secrets_backing_store

    def _get_vault_policies(self, enable_default_vp_policies=True):
        # We start off with the hard-coded default VP policy and add the user-defined ones
        if enable_default_vp_policies:
            policies = default_vp_vault_policies.copy()
        else:
            policies = {}

        # This is useful for embedded newlines, which occur with YAML
        # flow-type scalars (|, |- for example)
        for name, policy in self.syaml.get("vaultPolicies", {}).items():
            policies[name] = self._sanitize_yaml_value(policy)

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

    def _get_field_annotations(self, f):
        return f.get("annotations", {})

    def _get_field_labels(self, f):
        return f.get("labels", {})

    def _get_field_kind(self, f):
        # value: null will be interpreted with None, so let's just
        # check for the existence of the field, as we use 'value: null' to say
        # "we want a value/secret and not a file path"
        found = []
        for i in ["value", "path", "ini_file"]:
            if i in f:
                found.append(i)

        if len(found) > 1:  # you can only have one of value, path and ini_file
            self.module.fail_json(
                f"Both '{found[0]}' and '{found[1]}' cannot be used "
                f"in field {f['name']}"
            )

        if len(found) == 0:
            return ""
        return found[0]

    def _get_field_prompt(self, f):
        return f.get("prompt", None)

    def _get_field_base64(self, f):
        return bool(f.get("base64", False))

    def _get_field_override(self, f):
        return bool(f.get("override", False))

    def _get_secret_store_namespace(self):
        return str(self.syaml.get("secretStoreNamespace", secret_store_namespace))

    def _get_vault_prefixes(self, s):
        return list(s.get("vaultPrefixes", ["hub"]))

    def _get_default_labels(self):
        return self.syaml.get("defaultLabels", {})

    def _get_default_annotations(self):
        return self.syaml.get("defaultAnnotations", {})

    def _append_kubernetes_secret(self, secret_obj):
        self.kubernetes_secret_objects.append(secret_obj)

    def _sanitize_yaml_value(self, value):
        # This is useful for embedded newlines, which occur with YAML
        # flow-type scalars (|, |- for example)
        if value is not None:
            sanitized_value = bytes(value, "utf-8").decode("unicode_escape")
        else:
            sanitized_value = None

        return sanitized_value

    def _create_k8s_secret(self, sname, secret_type, namespace, labels, annotations):
        return {
            "type": secret_type,
            "kind": "Secret",
            "apiVersion": "v1",
            "metadata": {
                "name": sname,
                "namespace": namespace,
                "annotations": annotations,
                "labels": labels,
            },
            "stringData": {},
        }

    # This does what inject_secrets used to (mostly)
    def parse(self):
        self.sanitize_values()
        self.vault_policies = self._get_vault_policies()
        self.secret_store_namespace = self._get_secret_store_namespace()
        backing_store = self._get_backingstore()
        secrets = self._get_secrets()

        total_secrets = 0  # Counter for all the secrets uploaded
        for s in secrets:
            total_secrets += 1
            counter = 0  # This counter is to use kv put on first secret and kv patch on latter
            sname = s.get("name")
            fields = s.get("fields", [])
            vault_prefixes = self._get_vault_prefixes(s)
            secret_type = s.get("type", "Opaque")
            vault_mount = s.get("vaultMount", "secret")
            target_namespaces = s.get("targetNamespaces", [])
            labels = stringify_dict(s.get("labels", self._get_default_labels()))
            annotations = stringify_dict(
                s.get("annotations", self._get_default_annotations())
            )

            self.parsed_secrets[sname] = {
                "name": sname,
                "fields": {},
                "vault_mount": vault_mount,
                "vault_policies": {},
                "vault_prefixes": vault_prefixes,
                "override": [],
                "generate": [],
                "paths": {},
                "base64": [],
                "ini_file": {},
                "type": secret_type,
                "target_namespaces": target_namespaces,
                "labels": labels,
                "annotations": annotations,
            }

            for i in fields:
                self._inject_field(sname, i)
                counter += 1

            if backing_store == "kubernetes":
                k8s_namespaces = [self._get_secret_store_namespace()]
            else:
                k8s_namespaces = target_namespaces

            for tns in k8s_namespaces:
                k8s_secret = self._create_k8s_secret(
                    sname, secret_type, tns, labels, annotations
                )
                k8s_secret["stringData"] = self.parsed_secrets[sname]["fields"]
                self.kubernetes_secret_objects.append(k8s_secret)

        return total_secrets

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
        backing_store = self._get_backingstore()
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

            namespaces = s.get("targetNamespaces", [])
            if not isinstance(namespaces, list):
                return (False, f"Secret {s['name']} targetNamespaces must be a list")

            if backing_store == "none" and namespaces == []:
                return (
                    False,
                    f"Secret {s['name']} targetNamespaces cannot be empty for secrets backend {backing_store}",
                )  # noqa: E501

            labels = s.get("labels", {})
            if not isinstance(labels, dict):
                return (False, f"Secret {s['name']} labels must be a dictionary")

            annotations = s.get("annotations", {})
            if not isinstance(annotations, dict):
                return (False, f"Secret {s['name']} annotations must be a dictionary")

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

    def sanitize_values(self):
        """
        Sanitizes the secrets YAML object version 2.0

        Parameters:

        Returns:
            Nothing: Updates self.syaml(obj) if needed
        """
        v = get_version(self.syaml)
        if v not in ["2.0"]:
            self.module.fail_json(f"Version is not 2.0: {v}")

        backing_store = self._get_backingstore()
        if backing_store not in [
            "kubernetes",
            "vault",
            "none",
        ]:  # we currently only support vault
            self.module.fail_json(
                f"Currently only the 'vault', 'kubernetes' and 'none' backingStores are supported: {backing_store}"
            )

        (ret, msg) = self._validate_secrets()
        if not ret:
            self.module.fail_json(msg)

    def _get_secret_value(self, name, field):
        on_missing_value = self._get_field_on_missing_value(field)
        # We cannot use match + case as RHEL8 has python 3.9 (it needs 3.10)
        # We checked for errors in _validate_secrets() already
        if on_missing_value == "error":
            return self._sanitize_yaml_value(field.get("value"))
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

    def _inject_field(self, secret_name, f):
        on_missing_value = self._get_field_on_missing_value(f)
        override = self._get_field_override(f)
        kind = self._get_field_kind(f)
        b64 = self._get_field_base64(f)

        if kind in ["value", ""]:
            if on_missing_value == "generate":
                self.parsed_secrets[secret_name]["generate"].append(f["name"])
                if self._get_backingstore() != "vault":
                    self.module.fail_json(
                        "You cannot have onMissingValue set to 'generate' unless using vault backingstore "
                        f"for secret {secret_name} field {f['name']}"
                    )
                else:
                    if kind in ["path", "ini_file"]:
                        self.module.fail_json(
                            "You cannot have onMissingValue set to 'generate' with a path or ini_file"
                            f" for secret {secret_name} field {f['name']}"
                        )

                vault_policy = f.get("vaultPolicy", "validatedPatternDefaultPolicy")

                if override:
                    self.parsed_secrets[secret_name]["override"].append(f["name"])

                if b64:
                    self.parsed_secrets[secret_name]["base64"].append(f["name"])

                self.parsed_secrets[secret_name]["fields"][f["name"]] = None
                self.parsed_secrets[secret_name]["vault_policies"][
                    f["name"]
                ] = vault_policy

                return

            # If we're not generating the secret inside the vault directly we either read it from the file ("error")
            # or we are prompting the user for it
            secret = self._get_secret_value(secret_name, f)
            if b64:
                secret = base64.b64encode(secret.encode()).decode("utf-8")
                self.parsed_secrets[secret_name]["base64"].append(f["name"])

            self.parsed_secrets[secret_name]["fields"][f["name"]] = secret

        elif kind == "path":  # path. we upload files
            path = self._get_file_path(secret_name, f)
            self.parsed_secrets[secret_name]["paths"][f["name"]] = path

            binfile = False

            # Default to UTF-8
            try:
                secret = open(path, encoding="utf-8").read()
            except UnicodeDecodeError:
                secret = open(path, "rb").read()
                binfile = True

            if b64:
                self.parsed_secrets[secret_name]["base64"].append(f["name"])
                if binfile:
                    secret = base64.b64encode(bytes(secret)).decode("utf-8")
                else:
                    secret = base64.b64encode(secret.encode()).decode("utf-8")

            self.parsed_secrets[secret_name]["fields"][f["name"]] = secret
        elif kind == "ini_file":  # ini_file. we parse an ini_file
            ini_file = os.path.expanduser(f.get("ini_file"))
            ini_section = f.get("ini_section", "default")
            ini_key = f.get("ini_key")
            secret = get_ini_value(ini_file, ini_section, ini_key)
            if b64:
                self.parsed_secrets[secret_name]["base64"].append(f["name"])
                secret = base64.b64encode(secret.encode()).decode("utf-8")

            self.parsed_secrets[secret_name]["ini_file"][f["name"]] = {
                "ini_file": ini_file,
                "ini_section": ini_section,
                "ini_key": ini_key,
            }
            self.parsed_secrets[secret_name]["fields"][f["name"]] = secret

        return
