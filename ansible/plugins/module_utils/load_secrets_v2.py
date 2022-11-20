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

def sanitize_values_v2(module, syaml):
    """
    Sanitizes the secrets YAML object version 2.0
    ..TODO..

    Parameters:
        module(AnsibleModule): The current AnsibleModule being used

        syaml(obj): The parsed yaml object representing the secrets

    Returns:
        syaml(obj): The parsed yaml object sanitized
    """
    version = get_version(syaml)
    if version != "2.0":
        module.fail_json(f"Version expected is 2.0 but got: {version}")

    return syaml

def get_secrets_vault_paths(module, syaml, keyname):
    return
