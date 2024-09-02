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
Module that implements V1 of the values-secret.yaml spec
"""

import base64
import os
import time

import yaml
from ansible.module_utils.load_secrets_common import flatten, get_version


class LoadSecretsV1:

    def __init__(
        self,
        module,
        syaml,
        basepath,
        namespace,
        pod,
        values_secret_template,
        check_missing_secrets,
    ):
        self.module = module
        self.basepath = basepath
        self.namespace = namespace
        self.pod = pod
        self.values_secret_template = values_secret_template
        self.check_missing_secrets = check_missing_secrets
        self.syaml = syaml

    def _run_command(self, command, attempts=1, sleep=3):
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
                check_rc=True,
                use_unsafe_shell=True,
                environ_update=os.environ.copy(),
            )
            if ret[0] == 0:
                return ret
            if attempt >= attempts - 1:
                return ret
            time.sleep(sleep)

    def sanitize_values(self):
        """
        Sanitizes the secrets YAML object. If a specific secret key has
        s3.accessKey and s3.secretKey but not s3Secret, the latter will be
        generated as the base64 encoding of both s3.accessKey and s3.secretKey.

          secrets:
            test:
              s3.accessKey: "1234"
              s3.secretKey: "4321"

        will push three secrets at 'secret/hub/test':

        s3.accessKey: 1234
        s3.secretKey: 4321
        s3Secret: czMuYWNjZXNzS2V5OiAxMjM0CnMzLnNlY3JldEtleTogNDMyMQ==

        Parameters:

        Returns:
            Nothing: Updates self.syaml(obj)
        """
        v = get_version(self.syaml)
        if v != "1.0":
            self.module.fail_json(f"Version is not 1.0: {v}")

        if not ("secrets" in self.syaml or "files" in self.syaml):
            self.module.fail_json(
                f"Values secrets file does not contain 'secrets' or"
                f"'files' keys: {self.syaml}"
            )

        if self.check_missing_secrets and self.values_secret_template == "":
            self.module.fail_json(
                "No values_secret_template defined and check_missing_secrets set to True"
            )
        # If the user specified check_for_missing_secrets then we read values_secret_template
        # and check if there are any missing secrets. Makes sense only for v1.0
        if self.check_missing_secrets:
            self.check_for_missing_secrets()

        secrets = self.syaml.get("secrets", {})
        # We need to explicitely check for None because the file might contain the
        # top-level 'secrets:' or 'files:' key but have nothing else under it which will
        # return None and not {}
        if secrets is None:
            secrets = {}
        files = self.syaml.get("files", {})
        if files is None:
            files = {}
        if len(secrets) == 0 and len(files) == 0:
            self.module.fail_json(
                "Neither 'secrets' nor 'files have any secrets to be parsed"
            )

        if isinstance(secrets, list) or isinstance(files, list):
            self.module.fail_json("Neither 'secrets' nor 'files can be lists")

        for secret in secrets:
            if not isinstance(secrets[secret], dict):
                self.module.fail_json(
                    "Each key under 'secrets' needs to point to "
                    "a dictionary of key value pairs"
                )

        for file in files:
            path = files[file]
            if not os.path.isfile(os.path.expanduser(path)):
                self.module.fail_json(f"File {path} does not exist")

        # If s3Secret key does not exist but s3.accessKey and s3.secretKey do exist
        # generate s3Secret so a user does not need to do it manually which tends to be error-prone
        for secret in secrets:
            tmp = secrets[secret]
            if (
                "s3.accessKey" in tmp
                and "s3.secretKey" in tmp
                and "s3Secret" not in tmp
            ):
                s3secret = (
                    f"s3.accessKey: {tmp['s3.accessKey']}\n"
                    f"s3.secretKey: {tmp['s3.secretKey']}"
                )
                s3secretb64 = base64.b64encode(s3secret.encode())
                secrets[secret]["s3Secret"] = s3secretb64.decode("utf-8")

    def get_secrets_vault_paths(self, keyname):
        """
        Walks a secrets yaml object to look for all top-level keys that start with
        'keyname' and returns a list of tuples [(keyname1, path1), (keyname2, path2)...]
        where the path is the relative vault path
        For example, given a yaml with the following:
            secrets:
                foo: bar
            secrets.region1:
                foo: baz
            secrets.region2:
                foo: barbaz

        a call with keyname set to 'secrets' will return the following:
        [('secrets', 'hub'), ('secrets', 'region1'), ('secrets', 'region2')]

        Parameters:
            keyname(str): The keytypes to look for either usually 'secrets' or 'files'

        Returns:
            keys_paths(list): List of tuples containing (keyname, relative-vault-path)
        """
        all_keys = self.syaml.keys()
        keys_paths = []
        for key in all_keys:
            # We skip any key that does not start with 'secrets' or 'files'
            # (We should probably bail out in the presence of unexpected top-level keys)
            if not key.startswith(keyname):
                continue

            # If there is no '.' after secrets or files, assume the secrets need to
            # go to the hub vault path
            if key == keyname:
                keys_paths.append((key, "hub"))
                continue

            # We are in the presence of either 'secrets.region-one' or 'files.cluster1' top-level keys
            tmp = key.split(".", 1)
            if len(tmp) != 2:
                self.module.fail_json(
                    f"values-secrets.yaml key is non-conformant: {key}"
                )

            keys_paths.append((key, tmp[1]))

        return keys_paths

    # NOTE(bandini): we shell out to oc exec it because of
    # https://github.com/ansible-collections/kubernetes.core/issues/506 and
    # https://github.com/kubernetes/kubernetes/issues/89899. Until those are solved
    # it makes little sense to invoke the APIs via the python wrappers
    def inject_secrets(self):
        """
        Walks a secrets yaml object and injects all the secrets into the vault via 'oc exec' calls

        Parameters:

        Returns:
            counter(int): The number of secrets injected
        """
        counter = 0
        for i in self.get_secrets_vault_paths("secrets"):
            path = f"{self.basepath}/{i[1]}"
            for secret in self.syaml[i[0]] or []:
                properties = ""
                for key, value in self.syaml[i[0]][secret].items():
                    properties += f"{key}='{value}' "
                properties = properties.rstrip()
                cmd = (
                    f"oc exec -n {self.namespace} {self.pod} -i -- sh -c "
                    f"\"vault kv put '{path}/{secret}' {properties}\""
                )
                self._run_command(cmd, attempts=3)
                counter += 1

        for i in self.get_secrets_vault_paths("files"):
            path = f"{self.basepath}/{i[1]}"
            for filekey in self.syaml[i[0]] or []:
                file = os.path.expanduser(self.syaml[i[0]][filekey])
                cmd = (
                    f"cat '{file}' | oc exec -n {self.namespace} {self.pod} -i -- sh -c "
                    f"'cat - > /tmp/vcontent'; "
                    f"oc exec -n {self.namespace} {self.pod} -i -- sh -c 'base64 --wrap=0 /tmp/vcontent | "
                    f"vault kv put {path}/{filekey} b64content=- content=@/tmp/vcontent; "
                    f"rm /tmp/vcontent'"
                )
                self._run_command(cmd, attempts=3)
                counter += 1
        return counter

    def check_for_missing_secrets(self):
        with open(self.values_secret_template, "r", encoding="utf-8") as file:
            template_yaml = yaml.safe_load(file.read())
        if template_yaml is None:
            self.module.fail_json(f"Template {self.values_secret_template} is empty")

        syaml_flat = flatten(self.syaml)
        template_flat = flatten(template_yaml)

        syaml_keys = set(syaml_flat.keys())
        template_keys = set(template_flat.keys())

        if template_keys <= syaml_keys:
            return

        diff = template_keys - syaml_keys
        self.module.fail_json(
            f"Values secret yaml is missing needed secrets from the templates: {diff}"
        )
