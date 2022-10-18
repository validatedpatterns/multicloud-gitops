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

import base64
import os
import subprocess
import time
from collections.abc import MutableMapping

import yaml
from ansible.module_utils.basic import AnsibleModule

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


def parse_values(values_file):
    """
    Parses a values-secrets.yaml file (usually placed in ~)
    and returns a Python Obect with the parsed yaml.

    Parameters:
        values_file(str): The path of the values-secrets.yaml file
        to be parsed.

    Returns:
        secrets_yaml(obj): The python object containing the parsed yaml
    """
    with open(values_file, "r", encoding="utf-8") as file:
        secrets_yaml = yaml.safe_load(file.read())
    if secrets_yaml is None:
        return {}
    return secrets_yaml


def get_version(syaml):
    """
    Return the version: of the parsed yaml object. If it does not exist
    return 1.0

    Returns:
        ret(str): The version value in of the top-level 'version:' key
    """
    return syaml.get("version", "1.0")


def run_command(command, attempts=1, sleep=3):
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
        try:
            ret = subprocess.run(
                command,
                shell=True,
                env=os.environ.copy(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                check=True,
            )
            return ret
        except subprocess.CalledProcessError as e:
            # We reached maximum nr of retries. Re-raise the last error
            if attempt >= attempts - 1:
                raise e
            time.sleep(sleep)


def flatten(dictionary, parent_key=False, separator="."):
    """
    Turn a nested dictionary into a flattened dictionary and also
    drop any key that has 'None' as their value

    Parameters:
        dictionary(dict): The dictionary to flatten

        parent_key(str): The string to prepend to dictionary's keys

        separator(str): The string used to separate flattened keys

    Returns:

        dictionary: A flattened dictionary where the keys represent the
        path to reach the leaves
    """

    items = []
    for key, value in dictionary.items():
        new_key = str(parent_key) + separator + key if parent_key else key
        if isinstance(value, MutableMapping):
            items.extend(flatten(value, new_key, separator).items())
        elif isinstance(value, list):
            for k, v in enumerate(value):
                items.extend(flatten({str(k): v}, new_key).items())
        else:
            if value is not None:
                items.append((new_key, value))
    return dict(items)


def sanitize_values(module, syaml):
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
        module(AnsibleModule): The current AnsibleModule being used

        syaml(obj): The parsed yaml object representing the secrets

    Returns:
        syaml(obj): The parsed yaml object sanitized
    """
    if not ("secrets" in syaml or "files" in syaml):
        module.fail_json(
            f"Values secrets file does not contain 'secrets' or"
            f"'files' keys: {syaml}"
        )

    secrets = syaml.get("secrets", {})
    # We need to explicitely check for None because the file might contain the
    # top-level 'secrets:' or 'files:' key but have nothing else under it which will
    # return None and not {}
    if secrets is None:
        secrets = {}
    files = syaml.get("files", {})
    if files is None:
        files = {}
    if len(secrets) == 0 and len(files) == 0:
        module.fail_json(
            f"Neither 'secrets' nor 'files have any secrets to be parsed: {syaml}"
        )

    if isinstance(secrets, list) or isinstance(files, list):
        module.fail_json(f"Neither 'secrets' nor 'files can be lists: {syaml}")

    for secret in secrets:
        if not isinstance(secrets[secret], dict):
            module.fail_json(
                f"Each key under 'secrets' needs to point to "
                f"a dictionary of key value pairs: {syaml}"
            )

    for file in files:
        path = files[file]
        if not os.path.isfile(os.path.expanduser(path)):
            module.fail_json(f"File {path} does not exist")

    # If s3Secret key does not exist but s3.accessKey and s3.secretKey do exist
    # generate s3Secret so a user does not need to do it manually which tends to be error-prone
    for secret in secrets:
        tmp = secrets[secret]
        if "s3.accessKey" in tmp and "s3.secretKey" in tmp and "s3Secret" not in tmp:
            s3secret = (
                f"s3.accessKey: {tmp['s3.accessKey']}\n"
                f"s3.secretKey: {tmp['s3.secretKey']}"
            )
            s3secretb64 = base64.b64encode(s3secret.encode())
            secrets[secret]["s3Secret"] = s3secretb64.decode("utf-8")

    return syaml


def get_secrets_vault_paths(module, syaml, keyname):
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
        module(AnsibleModule): The current AnsibleModule being used

        syaml(obj): The parsed yaml object representing the secrets

        keyname(str): The keytypes to look for either usually 'secrets' or 'files'

    Returns:
        keys_paths(list): List of tuples containing (keyname, relative-vault-path)
    """
    all_keys = syaml.keys()
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
        tmp = key.split(".")
        if len(tmp) != 2:
            module.fail_json(f"values-secrets.yaml key is non-conformant: {key}")

        keys_paths.append((key, tmp[1]))

    return keys_paths


# NOTE(bandini): we shell out to oc exec it because of
# https://github.com/ansible-collections/kubernetes.core/issues/506 and
# https://github.com/kubernetes/kubernetes/issues/89899. Until those are solved
# it makes little sense to invoke the APIs via the python wrappers
def inject_secrets(module, syaml, namespace, pod, basepath):
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
    for i in get_secrets_vault_paths(module, syaml, "secrets"):
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

    for i in get_secrets_vault_paths(module, syaml, "files"):
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

    if version != "1.0":
        module.fail_json(f"Version {version} is currently not supported")

    # In the future we can use the version field to manage different formats if needed
    secrets = sanitize_values(module, syaml)

    # If the user specified check_for_missing_secrets then we read values_secret_template
    # and check if there are any missing secrets
    if check_missing_secrets:
        check_for_missing_secrets(module, syaml, values_secret_template)

    nr_secrets = inject_secrets(module, secrets, namespace, pod, basepath)
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
