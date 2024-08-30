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
Simple module to test vault_load_parsed_secrets
"""

import json
import os
import sys
import unittest
from unittest.mock import call, patch

import test_util_datastructures
from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes

# TODO(bandini): I could not come up with something better to force the imports to be existing
# when we 'import vault_load_secrets'
sys.path.insert(1, "./ansible/plugins/module_utils")
sys.path.insert(1, "./ansible/plugins/modules")

import vault_load_parsed_secrets  # noqa: E402

sys.modules["ansible.modules.vault_load_parsed_secrets"] = vault_load_parsed_secrets


def set_module_args(args):
    """prepare arguments so that they will be picked up during module creation"""
    args = json.dumps({"ANSIBLE_MODULE_ARGS": args})
    basic._ANSIBLE_ARGS = to_bytes(args)


class AnsibleExitJson(Exception):
    """Exception class to be raised by module.exit_json and caught by the test case"""

    pass


class AnsibleFailJson(Exception):
    """Exception class to be raised by module.fail_json and caught by the test case"""

    pass


def exit_json(*args, **kwargs):
    """function to patch over exit_json; package return data into an exception"""
    if "changed" not in kwargs:
        kwargs["changed"] = False
    raise AnsibleExitJson(kwargs)


def fail_json(*args, **kwargs):
    """function to patch over fail_json; package return data into an exception"""
    kwargs["failed"] = True
    kwargs["args"] = args
    raise AnsibleFailJson(kwargs)


class TestMyModule(unittest.TestCase):

    def setUp(self):
        self.mock_module_helper = patch.multiple(
            basic.AnsibleModule, exit_json=exit_json, fail_json=fail_json
        )
        self.mock_module_helper.start()
        self.addCleanup(self.mock_module_helper.stop)
        self.testdir_v2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "v2")

    def tearDown(self):
        return

    def test_module_fail_when_required_args_missing(self):
        with self.assertRaises(AnsibleFailJson):
            set_module_args({})
            vault_load_parsed_secrets.main()

    # For these tests, we need the data structures that parse_secrets_info outputs.
    # Several have been saved in the test_util_datastructures module for this purpose
    def test_ensure_value_injection_works(self):
        set_module_args(
            {
                "parsed_secrets": test_util_datastructures.PARSED_SECRET_VALUE_TEST[
                    "parsed_secrets"
                ],
                "vault_policies": test_util_datastructures.PARSED_SECRET_VALUE_TEST[
                    "vault_policies"
                ],
            }
        )
        with patch.object(
            vault_load_parsed_secrets.VaultSecretLoader, "_run_command"
        ) as mock_run_command:
            stdout = ""
            stderr = ""
            ret = 0
            mock_run_command.return_value = ret, stdout, stderr  # successful execution

            with self.assertRaises(AnsibleExitJson) as result:
                vault_load_parsed_secrets.main()
            self.assertTrue(
                result.exception.args[0]["changed"]
            )  # ensure result is changed
            assert mock_run_command.call_count == 2

        calls = [
            call(
                'echo \'length=20\nrule "charset" { charset = "abcdefghijklmnopqrstuvwxyz" min-chars = 1 }\nrule "charset" { charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" min-chars = 1 }\nrule "charset" { charset = "0123456789" min-chars = 1 }\nrule "charset" { charset = "!@#%^&*" min-chars = 1 }\n\' | oc exec -n vault vault-0 -i -- sh -c \'cat - > /tmp/validatedPatternDefaultPolicy.hcl\';oc exec -n vault vault-0 -i -- sh -c \'vault write sys/policies/password/validatedPatternDefaultPolicy  policy=@/tmp/validatedPatternDefaultPolicy.hcl\'',  # noqa: E501
                attempts=3,
            ),
            call(
                "oc exec -n vault vault-0 -i -- sh -c \"vault kv put -mount=secret hub/config-demo secret='\"'value123'\"'\"",  # noqa: E501
                attempts=3,
            ),
        ]
        print(mock_run_command.mock_calls)
        mock_run_command.assert_has_calls(calls)

    def test_ensure_b64_value_injection_works(self):
        set_module_args(
            {
                "parsed_secrets": test_util_datastructures.PARSED_SECRET_B64_VALUE_TEST[
                    "parsed_secrets"
                ],
                "vault_policies": test_util_datastructures.PARSED_SECRET_B64_VALUE_TEST[
                    "vault_policies"
                ],
            }
        )
        with patch.object(
            vault_load_parsed_secrets.VaultSecretLoader, "_run_command"
        ) as mock_run_command:
            stdout = ""
            stderr = ""
            ret = 0
            mock_run_command.return_value = ret, stdout, stderr  # successful execution

            with self.assertRaises(AnsibleExitJson) as result:
                vault_load_parsed_secrets.main()
            self.assertTrue(
                result.exception.args[0]["changed"]
            )  # ensure result is changed
            assert mock_run_command.call_count == 2

        calls = [
            call(
                'echo \'length=20\nrule "charset" { charset = "abcdefghijklmnopqrstuvwxyz" min-chars = 1 }\nrule "charset" { charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" min-chars = 1 }\nrule "charset" { charset = "0123456789" min-chars = 1 }\nrule "charset" { charset = "!@#%^&*" min-chars = 1 }\n\' | oc exec -n vault vault-0 -i -- sh -c \'cat - > /tmp/validatedPatternDefaultPolicy.hcl\';oc exec -n vault vault-0 -i -- sh -c \'vault write sys/policies/password/validatedPatternDefaultPolicy  policy=@/tmp/validatedPatternDefaultPolicy.hcl\'',  # noqa: E501
                attempts=3,
            ),
            call(
                "oc exec -n vault vault-0 -i -- sh -c \"vault kv put -mount=secret hub/config-demo secret='\"'dmFsdWUxMjMK'\"'\"",  # noqa: E501
                attempts=3,
            ),
        ]
        print(mock_run_command.mock_calls)
        mock_run_command.assert_has_calls(calls)

    def test_ensure_file_injection_works(self):
        set_module_args(
            {
                "parsed_secrets": test_util_datastructures.PARSED_SECRET_FILE_INJECTION_TEST[
                    "parsed_secrets"
                ],
                "vault_policies": test_util_datastructures.PARSED_SECRET_FILE_INJECTION_TEST[
                    "vault_policies"
                ],
            }
        )
        with patch.object(
            vault_load_parsed_secrets.VaultSecretLoader, "_run_command"
        ) as mock_run_command:
            stdout = ""
            stderr = ""
            ret = 0
            mock_run_command.return_value = ret, stdout, stderr  # successful execution

            with self.assertRaises(AnsibleExitJson) as result:
                vault_load_parsed_secrets.main()
            self.assertTrue(
                result.exception.args[0]["changed"]
            )  # ensure result is changed
            assert mock_run_command.call_count == 5

        calls = [
            call(
                'echo \'length=20\nrule "charset" { charset = "abcdefghijklmnopqrstuvwxyz" min-chars = 1 }\nrule "charset" { charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" min-chars = 1 }\nrule "charset" { charset = "0123456789" min-chars = 1 }\nrule "charset" { charset = "!@#%^&*" min-chars = 1 }\n\' | oc exec -n vault vault-0 -i -- sh -c \'cat - > /tmp/validatedPatternDefaultPolicy.hcl\';oc exec -n vault vault-0 -i -- sh -c \'vault write sys/policies/password/validatedPatternDefaultPolicy  policy=@/tmp/validatedPatternDefaultPolicy.hcl\'',  # noqa: E501
                attempts=3,
            ),
            call(
                "oc exec -n vault vault-0 -i -- sh -c \"vault kv put -mount=secret secret/region-one/config-demo secret='\"'value123'\"'\"",  # noqa: E501
                attempts=3,
            ),
            call(
                "oc exec -n vault vault-0 -i -- sh -c \"vault kv put -mount=secret secret/snowflake.blueprints.rhecoeng.com/config-demo secret='\"'value123'\"'\"",  # noqa: E501
                attempts=3,
            ),
            call(
                "cat '/tmp/footest' | oc exec -n vault vault-0 -i -- sh -c 'cat - > /tmp/vcontent'; oc exec -n vault vault-0 -i -- sh -c 'vault kv put -mount=secret secret/region-two/config-demo-file test=@/tmp/vcontent; rm /tmp/vcontent'",  # noqa: E501
                attempts=3,
            ),
            call(
                "cat '/tmp/footest' | oc exec -n vault vault-0 -i -- sh -c 'cat - > /tmp/vcontent'; oc exec -n vault vault-0 -i -- sh -c 'vault kv put -mount=secret secret/snowflake.blueprints.rhecoeng.com/config-demo-file test=@/tmp/vcontent; rm /tmp/vcontent'",  # noqa: E501
                attempts=3,
            ),
        ]
        print(mock_run_command.mock_calls)
        mock_run_command.assert_has_calls(calls)

    def test_ensure_file_b64_injection_works(self):
        set_module_args(
            {
                "parsed_secrets": test_util_datastructures.PARSED_SECRET_FILE_B64_INJECTION_TEST[
                    "parsed_secrets"
                ],
                "vault_policies": test_util_datastructures.PARSED_SECRET_FILE_B64_INJECTION_TEST[
                    "vault_policies"
                ],
            }
        )
        with patch.object(
            vault_load_parsed_secrets.VaultSecretLoader, "_run_command"
        ) as mock_run_command:
            stdout = ""
            stderr = ""
            ret = 0
            mock_run_command.return_value = ret, stdout, stderr  # successful execution

            with self.assertRaises(AnsibleExitJson) as result:
                vault_load_parsed_secrets.main()
            self.assertTrue(
                result.exception.args[0]["changed"]
            )  # ensure result is changed
            assert mock_run_command.call_count == 5

        calls = [
            call(
                'echo \'length=20\nrule "charset" { charset = "abcdefghijklmnopqrstuvwxyz" min-chars = 1 }\nrule "charset" { charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" min-chars = 1 }\nrule "charset" { charset = "0123456789" min-chars = 1 }\nrule "charset" { charset = "!@#%^&*" min-chars = 1 }\n\' | oc exec -n vault vault-0 -i -- sh -c \'cat - > /tmp/validatedPatternDefaultPolicy.hcl\';oc exec -n vault vault-0 -i -- sh -c \'vault write sys/policies/password/validatedPatternDefaultPolicy  policy=@/tmp/validatedPatternDefaultPolicy.hcl\'',  # noqa: E501
                attempts=3,
            ),
            call(
                "oc exec -n vault vault-0 -i -- sh -c \"vault kv put -mount=secret secret/region-one/config-demo secret='\"'value123'\"'\"",  # noqa: E501
                attempts=3,
            ),
            call(
                "oc exec -n vault vault-0 -i -- sh -c \"vault kv put -mount=secret secret/snowflake.blueprints.rhecoeng.com/config-demo secret='\"'value123'\"'\"",  # noqa: E501
                attempts=3,
            ),
            call(
                "cat '/tmp/footest' | oc exec -n vault vault-0 -i -- sh -c 'cat - | base64 --wrap=0> /tmp/vcontent'; oc exec -n vault vault-0 -i -- sh -c 'vault kv put -mount=secret secret/region-two/config-demo-file test=@/tmp/vcontent; rm /tmp/vcontent'",  # noqa: E501
                attempts=3,
            ),
            call(
                "cat '/tmp/footest' | oc exec -n vault vault-0 -i -- sh -c 'cat - | base64 --wrap=0> /tmp/vcontent'; oc exec -n vault vault-0 -i -- sh -c 'vault kv put -mount=secret secret/snowflake.blueprints.rhecoeng.com/config-demo-file test=@/tmp/vcontent; rm /tmp/vcontent'",  # noqa: E501
                attempts=3,
            ),
        ]
        print(mock_run_command.mock_calls)
        mock_run_command.assert_has_calls(calls)

    def test_ensure_b64_generate_passwords_works(self):
        set_module_args(
            {
                "parsed_secrets": test_util_datastructures.GENERATE_POLICY_B64_TEST[
                    "parsed_secrets"
                ],
                "vault_policies": test_util_datastructures.GENERATE_POLICY_B64_TEST[
                    "vault_policies"
                ],
            }
        )
        with patch.object(
            vault_load_parsed_secrets.VaultSecretLoader, "_run_command"
        ) as mock_run_command:
            stdout = ""
            stderr = ""
            ret = 0
            mock_run_command.return_value = ret, stdout, stderr  # successful execution

            with self.assertRaises(AnsibleExitJson) as result:
                vault_load_parsed_secrets.main()
            self.assertTrue(
                result.exception.args[0]["changed"]
            )  # ensure result is changed
            assert mock_run_command.call_count == 4

        calls = [
            call(
                'echo \'length=10\nrule "charset" { charset = "abcdefghijklmnopqrstuvwxyz" min-chars = 1 }\nrule "charset" { charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" min-chars = 1 }\nrule "charset" { charset = "0123456789" min-chars = 1 }\n\' | oc exec -n vault vault-0 -i -- sh -c \'cat - > /tmp/basicPolicy.hcl\';oc exec -n vault vault-0 -i -- sh -c \'vault write sys/policies/password/basicPolicy  policy=@/tmp/basicPolicy.hcl\'',  # noqa: E501
                attempts=3,
            ),
            call(
                'echo \'length=20\nrule "charset" { charset = "abcdefghijklmnopqrstuvwxyz" min-chars = 1 }\nrule "charset" { charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" min-chars = 1 }\nrule "charset" { charset = "0123456789" min-chars = 1 }\nrule "charset" { charset = "!@#%^&*" min-chars = 1 }\n\' | oc exec -n vault vault-0 -i -- sh -c \'cat - > /tmp/validatedPatternDefaultPolicy.hcl\';oc exec -n vault vault-0 -i -- sh -c \'vault write sys/policies/password/validatedPatternDefaultPolicy  policy=@/tmp/validatedPatternDefaultPolicy.hcl\'',  # noqa: E501
                attempts=3,
            ),
            call(
                'oc exec -n vault vault-0 -i -- sh -c "vault read -field=password sys/policies/password/basicPolicy/generate | base64 --wrap=0 | vault kv put -mount=secret region-one/config-demo secret=-"',  # noqa: E501
                attempts=3,
            ),
            call(
                'oc exec -n vault vault-0 -i -- sh -c "vault read -field=password sys/policies/password/basicPolicy/generate | base64 --wrap=0 | vault kv put -mount=secret snowflake.blueprints.rhecoeng.com/config-demo secret=-"',  # noqa: E501
                attempts=3,
            ),
        ]
        print(mock_run_command.mock_calls)
        mock_run_command.assert_has_calls(calls)


if __name__ == "__main__":
    unittest.main()
