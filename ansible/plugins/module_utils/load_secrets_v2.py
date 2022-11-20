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
from ansible.module_utils.load_secrets_common import flatten, parse_values, run_command


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


    def sanitize_values(self):
        """
        Sanitizes the secrets YAML object version 2.0
        ..TODO..

        Parameters:
            module(AnsibleModule): The current AnsibleModule being used

            syaml(obj): The parsed yaml object representing the secrets

        Returns:
            syaml(obj): The parsed yaml object sanitized
        """

        return syaml


    def get_secrets_vault_paths(self, keyname):
        return
