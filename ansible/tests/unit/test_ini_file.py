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
Simple module to test ini parsing function
"""

import os
import sys
import unittest

# TODO(bandini): I could not come up with something better to force the imports to be existing
# when we 'import vault_load_secrets'
sys.path.insert(1, "./ansible/plugins/module_utils")
sys.path.insert(1, "./ansible/plugins/modules")
import load_secrets_common  # noqa: E402


class TestMyModule(unittest.TestCase):

    def setUp(self):
        self.testdir_v2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "v2")

    def test_ensure_ini_file_parsed_correctly(self):
        f = os.path.join(self.testdir_v2, "aws-example.ini")
        key_id = load_secrets_common.get_ini_value(f, "default", "aws_access_key_id")
        access_key = load_secrets_common.get_ini_value(
            f, "default", "aws_secret_access_key"
        )
        self.assertEqual(key_id, "A123456789012345678A")
        self.assertEqual(access_key, "A12345678901234567890123456789012345678A")

    def test_ensure_ini_file_missing_value_is_none(self):
        f = os.path.join(self.testdir_v2, "aws-example.ini")
        missing_id = load_secrets_common.get_ini_value(f, "default", "nonexisting")
        self.assertEqual(missing_id, None)

    def test_ensure_ini_file_missing_section_is_none(self):
        f = os.path.join(self.testdir_v2, "aws-example.ini")
        missing_id = load_secrets_common.get_ini_value(f, "nonexisting", "nonexisting")
        self.assertEqual(missing_id, None)


if __name__ == "__main__":
    unittest.main()
