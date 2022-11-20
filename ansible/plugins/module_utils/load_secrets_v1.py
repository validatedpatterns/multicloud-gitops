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
        tmp = key.split(".", 1)
        if len(tmp) != 2:
            module.fail_json(f"values-secrets.yaml key is non-conformant: {key}")

        keys_paths.append((key, tmp[1]))

    return keys_paths
