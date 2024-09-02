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
Simple module to test vault_load_secrets
"""

import configparser
import json
import os
import sys
import unittest
from unittest import mock
from unittest.mock import call, patch

from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes

# TODO(bandini): I could not come up with something better to force the imports to be existing
# when we 'import vault_load_secrets'
sys.path.insert(1, "./ansible/plugins/module_utils")
sys.path.insert(1, "./ansible/plugins/modules")
import load_secrets_common  # noqa: E402

sys.modules["ansible.module_utils.load_secrets_common"] = load_secrets_common
import load_secrets_v1  # noqa: E402
import load_secrets_v2  # noqa: E402

sys.modules["ansible.module_utils.load_secrets_v1"] = load_secrets_v1
sys.modules["ansible.module_utils.load_secrets_v2"] = load_secrets_v2
import vault_load_secrets  # noqa: E402


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


@mock.patch("getpass.getpass")
class TestMyModule(unittest.TestCase):

    def create_inifile(self):
        self.inifile = open("/tmp/awscredentials", "w")
        config = configparser.ConfigParser()
        config["default"] = {
            "aws_access_key_id": "123123",
            "aws_secret_access_key": "abcdefghi",
        }
        config["foobar"] = {
            "aws_access_key_id": "345345",
            "aws_secret_access_key": "rstuvwxyz",
        }
        with self.inifile as configfile:
            config.write(configfile)

    def setUp(self):
        self.mock_module_helper = patch.multiple(
            basic.AnsibleModule, exit_json=exit_json, fail_json=fail_json
        )
        self.mock_module_helper.start()
        self.addCleanup(self.mock_module_helper.stop)
        self.testdir_v2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "v2")
        self.testfile = open("/tmp/ca.crt", "w")
        self.create_inifile()

    def tearDown(self):
        self.testfile.close()
        try:
            os.remove("/tmp/ca.crt")
            # os.remove("/tmp/awscredentials")
        except OSError:
            pass

    def test_module_fail_when_required_args_missing(self, getpass):
        with self.assertRaises(AnsibleFailJson):
            set_module_args({})
            vault_load_secrets.main()

    def test_module_fail_when_values_secret_not_existing(self, getpass):
        with self.assertRaises(AnsibleExitJson) as ansible_err:
            set_module_args(
                {
                    "values_secrets": "/tmp/nonexisting",
                }
            )
            vault_load_secrets.main()

        ret = ansible_err.exception.args[0]
        self.assertEqual(ret["failed"], True)
        self.assertEqual(ret["error"], "Missing /tmp/nonexisting file")
        self.assertEqual(
            ret["msg"], "Values secrets file does not exist: /tmp/nonexisting"
        )

    def test_ensure_no_vault_policies_is_ok(self, getpass):
        set_module_args(
            {
                "values_secrets": os.path.join(
                    self.testdir_v2, "values-secret-v2-nopolicies.yaml"
                ),
            }
        )
        getpass.return_value = "foo"
        with patch.object(
            load_secrets_v2.LoadSecretsV2, "_run_command"
        ) as mock_run_command:
            stdout = "configuration updated"
            stderr = ""
            ret = 0
            mock_run_command.return_value = ret, stdout, stderr  # successful execution

            with self.assertRaises(AnsibleExitJson) as result:
                vault_load_secrets.main()
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
                "oc exec -n vault vault-0 -i -- sh -c \"vault kv put -mount=secret secret/region-one/config-demo secret='value123'\"",  # noqa: E501
                attempts=3,
            ),
            call(
                "oc exec -n vault vault-0 -i -- sh -c \"vault kv put -mount=secret secret/snowflake.blueprints.rhecoeng.com/config-demo secret='value123'\"",  # noqa: E501
                attempts=3,
            ),
            call(
                "cat '/tmp/ca.crt' | oc exec -n vault vault-0 -i -- sh -c 'cat - | base64 --wrap=0 > /tmp/vcontent'; oc exec -n vault vault-0 -i -- sh -c 'vault kv put -mount=secret secret/region-two/config-demo-file ca_crt=@/tmp/vcontent; rm /tmp/vcontent'",  # noqa: E501
                attempts=3,
            ),
            call(
                "cat '/tmp/ca.crt' | oc exec -n vault vault-0 -i -- sh -c 'cat - | base64 --wrap=0 > /tmp/vcontent'; oc exec -n vault vault-0 -i -- sh -c 'vault kv put -mount=secret secret/snowflake.blueprints.rhecoeng.com/config-demo-file ca_crt=@/tmp/vcontent; rm /tmp/vcontent'",  # noqa: E501
                attempts=3,
            ),
        ]
        mock_run_command.assert_has_calls(calls)

    def test_ensure_policies_are_injected(self, getpass):
        set_module_args(
            {
                "values_secrets": os.path.join(
                    self.testdir_v2, "values-secret-v2-base.yaml"
                ),
            }
        )
        # this will be used for both a secret and a file path
        getpass.return_value = "/tmp/ca.crt"
        with patch.object(
            load_secrets_v2.LoadSecretsV2, "_run_command"
        ) as mock_run_command:
            stdout = "configuration updated"
            stderr = ""
            ret = 0
            mock_run_command.return_value = ret, stdout, stderr  # successful execution

            with self.assertRaises(AnsibleExitJson) as result:
                vault_load_secrets.main()
            self.assertTrue(
                result.exception.args[0]["changed"]
            )  # ensure result is changed
            assert mock_run_command.call_count == 11

        calls = [
            call(
                'echo \'length=20\nrule "charset" { charset = "abcdefghijklmnopqrstuvwxyz" min-chars = 1 }\nrule "charset" { charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" min-chars = 1 }\nrule "charset" { charset = "0123456789" min-chars = 1 }\nrule "charset" { charset = "!@#%^&*" min-chars = 1 }\n\' | oc exec -n vault vault-0 -i -- sh -c \'cat - > /tmp/validatedPatternDefaultPolicy.hcl\';oc exec -n vault vault-0 -i -- sh -c \'vault write sys/policies/password/validatedPatternDefaultPolicy  policy=@/tmp/validatedPatternDefaultPolicy.hcl\'',  # noqa: E501
                attempts=3,
            ),
            call(
                'echo \'length=10\nrule "charset" { charset = "abcdefghijklmnopqrstuvwxyz" min-chars = 1 }\nrule "charset" { charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" min-chars = 1 }\nrule "charset" { charset = "0123456789" min-chars = 1 }\n\' | oc exec -n vault vault-0 -i -- sh -c \'cat - > /tmp/basicPolicy.hcl\';oc exec -n vault vault-0 -i -- sh -c \'vault write sys/policies/password/basicPolicy  policy=@/tmp/basicPolicy.hcl\'',  # noqa: E501
                attempts=3,
            ),
            call(
                'echo \'length=20\nrule "charset" { charset = "abcdefghijklmnopqrstuvwxyz" min-chars = 1 }\nrule "charset" { charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" min-chars = 1 }\nrule "charset" { charset = "0123456789" min-chars = 1 }\nrule "charset" { charset = "!@#%^&*" min-chars = 1 }\n\' | oc exec -n vault vault-0 -i -- sh -c \'cat - > /tmp/advancedPolicy.hcl\';oc exec -n vault vault-0 -i -- sh -c \'vault write sys/policies/password/advancedPolicy  policy=@/tmp/advancedPolicy.hcl\'',  # noqa: E501
                attempts=3,
            ),
            call(
                'oc exec -n vault vault-0 -i -- sh -c "vault read -field=password sys/policies/password/basicPolicy/generate | vault kv put -mount=secret region-one/config-demo secret=-"',  # noqa: E501
                attempts=3,
            ),
            call(
                'oc exec -n vault vault-0 -i -- sh -c "vault read -field=password sys/policies/password/basicPolicy/generate | vault kv put -mount=secret snowflake.blueprints.rhecoeng.com/config-demo secret=-"',  # noqa: E501
                attempts=3,
            ),
            call(
                "oc exec -n vault vault-0 -i -- sh -c \"vault kv patch -mount=secret region-one/config-demo secret2='/tmp/ca.crt'\"",  # noqa: E501
                attempts=3,
            ),
            call(
                "oc exec -n vault vault-0 -i -- sh -c \"vault kv patch -mount=secret snowflake.blueprints.rhecoeng.com/config-demo secret2='/tmp/ca.crt'\"",  # noqa: E501
                attempts=3,
            ),
            call(
                "cat '/tmp/ca.crt' | oc exec -n vault vault-0 -i -- sh -c 'cat - > /tmp/vcontent'; oc exec -n vault vault-0 -i -- sh -c 'vault kv patch -mount=secret region-one/config-demo ca_crt=@/tmp/vcontent; rm /tmp/vcontent'",  # noqa: E501
                attempts=3,
            ),
            call(
                "cat '/tmp/ca.crt' | oc exec -n vault vault-0 -i -- sh -c 'cat - > /tmp/vcontent'; oc exec -n vault vault-0 -i -- sh -c 'vault kv patch -mount=secret snowflake.blueprints.rhecoeng.com/config-demo ca_crt=@/tmp/vcontent; rm /tmp/vcontent'",  # noqa: E501
                attempts=3,
            ),
            call(
                "cat '/tmp/ca.crt' | oc exec -n vault vault-0 -i -- sh -c 'cat - | base64 --wrap=0 > /tmp/vcontent'; oc exec -n vault vault-0 -i -- sh -c 'vault kv patch -mount=secret region-one/config-demo ca_crt2=@/tmp/vcontent; rm /tmp/vcontent'",  # noqa: E501
                attempts=3,
            ),
            call(
                "cat '/tmp/ca.crt' | oc exec -n vault vault-0 -i -- sh -c 'cat - | base64 --wrap=0 > /tmp/vcontent'; oc exec -n vault vault-0 -i -- sh -c 'vault kv patch -mount=secret snowflake.blueprints.rhecoeng.com/config-demo ca_crt2=@/tmp/vcontent; rm /tmp/vcontent'",  # noqa: E501
                attempts=3,
            ),
        ]
        mock_run_command.assert_has_calls(calls)

    def test_ensure_error_wrong_onmissing_value(self, getpass):
        with self.assertRaises(AnsibleFailJson) as ansible_err:
            set_module_args(
                {
                    "values_secrets": os.path.join(
                        self.testdir_v2, "values-secret-v2-wrong-onmissingvalue.yaml"
                    ),
                }
            )
            vault_load_secrets.main()

        ret = ansible_err.exception.args[0]
        self.assertEqual(ret["failed"], True)
        assert (
            ret["args"][1]
            == "Secret has vaultPolicy set to nonExisting but no such policy exists"
        )

    def test_ensure_error_wrong_vaultpolicy(self, getpass):
        with self.assertRaises(AnsibleFailJson) as ansible_err:
            set_module_args(
                {
                    "values_secrets": os.path.join(
                        self.testdir_v2, "values-secret-v2-wrong-vaultpolicy.yaml"
                    ),
                }
            )
            vault_load_secrets.main()

        ret = ansible_err.exception.args[0]
        self.assertEqual(ret["failed"], True)
        assert (
            ret["args"][1]
            == "Secret has vaultPolicy set to nonExisting but no such policy exists"
        )

    def test_ensure_error_file_wrong_onmissing_value(self, getpass):
        with self.assertRaises(AnsibleFailJson) as ansible_err:
            set_module_args(
                {
                    "values_secrets": os.path.join(
                        self.testdir_v2,
                        "values-secret-v2-files-wrong-onmissingvalue.yaml",
                    ),
                }
            )
            vault_load_secrets.main()

        ret = ansible_err.exception.args[0]
        self.assertEqual(ret["failed"], True)
        assert (
            ret["args"][1]
            == "Secret has onMissingValue set to 'generate' but has a path set"
        )

    def test_ensure_error_file_emptypath(self, getpass):
        with self.assertRaises(AnsibleFailJson) as ansible_err:
            set_module_args(
                {
                    "values_secrets": os.path.join(
                        self.testdir_v2, "values-secret-v2-files-emptypath.yaml"
                    ),
                }
            )
            vault_load_secrets.main()

        ret = ansible_err.exception.args[0]
        self.assertEqual(ret["failed"], True)
        assert (
            ret["args"][1]
            == "Secret has onMissingValue set to 'error' and has neither value nor path nor ini_file set"
        )

    def test_ensure_error_file_wrongpath(self, getpass):
        with self.assertRaises(AnsibleFailJson) as ansible_err:
            set_module_args(
                {
                    "values_secrets": os.path.join(
                        self.testdir_v2, "values-secret-v2-files-wrongpath.yaml"
                    ),
                }
            )
            vault_load_secrets.main()

        ret = ansible_err.exception.args[0]
        self.assertEqual(ret["failed"], True)
        assert ret["args"][1] == "Field has non-existing path: /tmp/nonexisting"

    def test_ensure_error_empty_vaultprefix(self, getpass):
        with self.assertRaises(AnsibleFailJson) as ansible_err:
            set_module_args(
                {
                    "values_secrets": os.path.join(
                        self.testdir_v2, "values-secret-v2-emptyvaultprefix.yaml"
                    ),
                }
            )
            vault_load_secrets.main()
        ret = ansible_err.exception.args[0]
        self.assertEqual(ret["failed"], True)
        assert ret["args"][1] == "Secret config-demo has empty vaultPrefixes"

    def test_ensure_default_no_vaultprefix(self, getpass):
        set_module_args(
            {
                "values_secrets": os.path.join(
                    self.testdir_v2, "values-secret-v2-novaultprefix.yaml"
                ),
            }
        )
        with patch.object(
            load_secrets_v2.LoadSecretsV2, "_run_command"
        ) as mock_run_command:
            stdout = "configuration updated"
            stderr = ""
            ret = 0
            mock_run_command.return_value = ret, stdout, stderr  # successful execution

            with self.assertRaises(AnsibleExitJson) as result:
                vault_load_secrets.main()
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
                "oc exec -n vault vault-0 -i -- sh -c \"vault kv put -mount=secret hub/config-demo secret='value123'\"",  # noqa: E501
                attempts=3,
            ),
        ]
        mock_run_command.assert_has_calls(calls)

    def test_ensure_only_generate_passwords_works(self, getpass):
        set_module_args(
            {
                "values_secrets": os.path.join(
                    self.testdir_v2, "values-secret-v2-onlygenerate.yaml"
                ),
            }
        )
        with patch.object(
            load_secrets_v2.LoadSecretsV2, "_run_command"
        ) as mock_run_command:
            stdout = "configuration updated"
            stderr = ""
            ret = 0
            mock_run_command.return_value = ret, stdout, stderr  # successful execution

            with self.assertRaises(AnsibleExitJson) as result:
                vault_load_secrets.main()
            self.assertTrue(
                result.exception.args[0]["changed"]
            )  # ensure result is changed
            assert mock_run_command.call_count == 7

        calls = [
            call(
                'echo \'length=20\nrule "charset" { charset = "abcdefghijklmnopqrstuvwxyz" min-chars = 1 }\nrule "charset" { charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" min-chars = 1 }\nrule "charset" { charset = "0123456789" min-chars = 1 }\nrule "charset" { charset = "!@#%^&*" min-chars = 1 }\n\' | oc exec -n vault vault-0 -i -- sh -c \'cat - > /tmp/validatedPatternDefaultPolicy.hcl\';oc exec -n vault vault-0 -i -- sh -c \'vault write sys/policies/password/validatedPatternDefaultPolicy  policy=@/tmp/validatedPatternDefaultPolicy.hcl\'',  # noqa: E501
                attempts=3,
            ),
            call(
                'echo \'length=10\nrule "charset" { charset = "abcdefghijklmnopqrstuvwxyz" min-chars = 1 }\nrule "charset" { charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" min-chars = 1 }\nrule "charset" { charset = "0123456789" min-chars = 1 }\n\' | oc exec -n vault vault-0 -i -- sh -c \'cat - > /tmp/basicPolicy.hcl\';oc exec -n vault vault-0 -i -- sh -c \'vault write sys/policies/password/basicPolicy  policy=@/tmp/basicPolicy.hcl\'',  # noqa: E501
                attempts=3,
            ),
            call(
                'echo \'length=20\nrule "charset" { charset = "abcdefghijklmnopqrstuvwxyz" min-chars = 1 }\nrule "charset" { charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" min-chars = 1 }\nrule "charset" { charset = "0123456789" min-chars = 1 }\nrule "charset" { charset = "!@#%^&*" min-chars = 1 }\n\' | oc exec -n vault vault-0 -i -- sh -c \'cat - > /tmp/advancedPolicy.hcl\';oc exec -n vault vault-0 -i -- sh -c \'vault write sys/policies/password/advancedPolicy  policy=@/tmp/advancedPolicy.hcl\'',  # noqa: E501
                attempts=3,
            ),
            call(
                'oc exec -n vault vault-0 -i -- sh -c "vault read -field=password sys/policies/password/basicPolicy/generate | vault kv put -mount=foo region-one/config-demo secret=-"',  # noqa: E501
                attempts=3,
            ),
            call(
                'oc exec -n vault vault-0 -i -- sh -c "vault read -field=password sys/policies/password/basicPolicy/generate | vault kv put -mount=foo snowflake.blueprints.rhecoeng.com/config-demo secret=-"',  # noqa: E501
                attempts=3,
            ),
            call(
                'oc exec -n vault vault-0 -i -- sh -c "vault read -field=password sys/policies/password/advancedPolicy/generate | vault kv patch -mount=foo region-one/config-demo secret2=-"',  # noqa: E501
                attempts=3,
            ),
            call(
                'oc exec -n vault vault-0 -i -- sh -c "vault read -field=password sys/policies/password/advancedPolicy/generate | vault kv patch -mount=foo snowflake.blueprints.rhecoeng.com/config-demo secret2=-"',  # noqa: E501
                attempts=3,
            ),
        ]
        mock_run_command.assert_has_calls(calls)

    def test_generate_password_base64_works(self, getpass):
        set_module_args(
            {
                "values_secrets": os.path.join(
                    self.testdir_v2, "values-secret-v2-generate-base64.yaml"
                ),
            }
        )
        with patch.object(
            load_secrets_v2.LoadSecretsV2, "_run_command"
        ) as mock_run_command:
            stdout = "configuration updated"
            stderr = ""
            ret = 0
            mock_run_command.return_value = ret, stdout, stderr  # successful execution

            with self.assertRaises(AnsibleExitJson) as result:
                vault_load_secrets.main()
            self.assertTrue(
                result.exception.args[0]["changed"]
            )  # ensure result is changed
            assert mock_run_command.call_count == 4

        calls = [
            call(
                'echo \'length=20\nrule "charset" { charset = "abcdefghijklmnopqrstuvwxyz" min-chars = 1 }\nrule "charset" { charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" min-chars = 1 }\nrule "charset" { charset = "0123456789" min-chars = 1 }\nrule "charset" { charset = "!@#%^&*" min-chars = 1 }\n\' | oc exec -n vault vault-0 -i -- sh -c \'cat - > /tmp/validatedPatternDefaultPolicy.hcl\';oc exec -n vault vault-0 -i -- sh -c \'vault write sys/policies/password/validatedPatternDefaultPolicy  policy=@/tmp/validatedPatternDefaultPolicy.hcl\'',  # noqa: E501
                attempts=3,
            ),
            call(
                'echo \'length=10\nrule "charset" { charset = "abcdefghijklmnopqrstuvwxyz" min-chars = 1 }\nrule "charset" { charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" min-chars = 1 }\nrule "charset" { charset = "0123456789" min-chars = 1 }\n\' | oc exec -n vault vault-0 -i -- sh -c \'cat - > /tmp/basicPolicy.hcl\';oc exec -n vault vault-0 -i -- sh -c \'vault write sys/policies/password/basicPolicy  policy=@/tmp/basicPolicy.hcl\'',  # noqa: E501
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
        mock_run_command.assert_has_calls(calls)

    def test_ensure_error_secrets_same_name(self, getpass):
        with self.assertRaises(AnsibleFailJson) as ansible_err:
            set_module_args(
                {
                    "values_secrets": os.path.join(
                        self.testdir_v2, "values-secret-v2-same-secret-names.yaml"
                    ),
                }
            )
            vault_load_secrets.main()

        ret = ansible_err.exception.args[0]
        self.assertEqual(ret["failed"], True)
        assert (
            ret["args"][1] == "You cannot have duplicate secret names: ['config-demo']"
        )

    def test_ensure_error_fields_same_name(self, getpass):
        with self.assertRaises(AnsibleFailJson) as ansible_err:
            set_module_args(
                {
                    "values_secrets": os.path.join(
                        self.testdir_v2, "values-secret-v2-same-field-names.yaml"
                    ),
                }
            )
            vault_load_secrets.main()

        ret = ansible_err.exception.args[0]
        self.assertEqual(ret["failed"], True)
        assert ret["args"][1] == "You cannot have duplicate field names: ['secret']"

    def test_password_base64_secret(self, getpass):
        set_module_args(
            {
                "values_secrets": os.path.join(
                    self.testdir_v2, "values-secret-v2-secret-base64.yaml"
                ),
            }
        )
        with patch.object(
            load_secrets_v2.LoadSecretsV2, "_run_command"
        ) as mock_run_command:
            stdout = "configuration updated"
            stderr = ""
            ret = 0
            mock_run_command.return_value = ret, stdout, stderr  # successful execution

            with self.assertRaises(AnsibleExitJson) as result:
                vault_load_secrets.main()
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
                "oc exec -n vault vault-0 -i -- sh -c \"vault kv put -mount=secret test/config-demo secret='Zm9v'\"",  # noqa: E501
                attempts=3,
            ),
        ]
        mock_run_command.assert_has_calls(calls)

    def test_ensure_error_on_unsupported_backingstore(self, getpass):
        with self.assertRaises(AnsibleFailJson) as ansible_err:
            set_module_args(
                {
                    "values_secrets": os.path.join(
                        self.testdir_v2,
                        "values-secret-v2-nonexisting-backingstore.yaml",
                    ),
                }
            )
            vault_load_secrets.main()

        ret = ansible_err.exception.args[0]
        self.assertEqual(ret["failed"], True)
        assert (
            ret["args"][1]
            == "Currently only the 'vault' backingStore is supported: nonexisting"
        )

    def test_password_default_vp_policy(self, getpass):
        set_module_args(
            {
                "values_secrets": os.path.join(
                    self.testdir_v2, "values-secret-v2-defaultvp-policy.yaml"
                ),
            }
        )
        with patch.object(
            load_secrets_v2.LoadSecretsV2, "_run_command"
        ) as mock_run_command:
            stdout = "configuration updated"
            stderr = ""
            ret = 0
            mock_run_command.return_value = ret, stdout, stderr  # successful execution

            with self.assertRaises(AnsibleExitJson) as result:
                vault_load_secrets.main()
            self.assertTrue(
                result.exception.args[0]["changed"]
            )  # ensure result is changed
            assert mock_run_command.call_count == 6

        calls = [
            call(
                'echo \'length=20\nrule "charset" { charset = "abcdefghijklmnopqrstuvwxyz" min-chars = 1 }\nrule "charset" { charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" min-chars = 1 }\nrule "charset" { charset = "0123456789" min-chars = 1 }\nrule "charset" { charset = "!@#%^&*" min-chars = 1 }\n\' | oc exec -n vault vault-0 -i -- sh -c \'cat - > /tmp/validatedPatternDefaultPolicy.hcl\';oc exec -n vault vault-0 -i -- sh -c \'vault write sys/policies/password/validatedPatternDefaultPolicy  policy=@/tmp/validatedPatternDefaultPolicy.hcl\'',  # noqa: E501
                attempts=3,
            ),
            call(
                'echo \'length=10\nrule "charset" { charset = "abcdefghijklmnopqrstuvwxyz" min-chars = 1 }\nrule "charset" { charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" min-chars = 1 }\nrule "charset" { charset = "0123456789" min-chars = 1 }\n\' | oc exec -n vault vault-0 -i -- sh -c \'cat - > /tmp/basicPolicy.hcl\';oc exec -n vault vault-0 -i -- sh -c \'vault write sys/policies/password/basicPolicy  policy=@/tmp/basicPolicy.hcl\'',  # noqa: E501
                attempts=3,
            ),
            call(
                'oc exec -n vault vault-0 -i -- sh -c "vault read -field=password sys/policies/password/basicPolicy/generate | vault kv put -mount=secret region-one/config-demo secret=-"',  # noqa: E501
                attempts=3,
            ),
            call(
                'oc exec -n vault vault-0 -i -- sh -c "vault read -field=password sys/policies/password/basicPolicy/generate | vault kv put -mount=secret snowflake.blueprints.rhecoeng.com/config-demo secret=-"',  # noqa: E501
                attempts=3,
            ),
            call(
                'oc exec -n vault vault-0 -i -- sh -c "vault read -field=password sys/policies/password/validatedPatternDefaultPolicy/generate | vault kv patch -mount=secret region-one/config-demo secret2=-"',  # noqa: E501
                attempts=3,
            ),
            call(
                'oc exec -n vault vault-0 -i -- sh -c "vault read -field=password sys/policies/password/validatedPatternDefaultPolicy/generate | vault kv patch -mount=secret snowflake.blueprints.rhecoeng.com/config-demo secret2=-"',  # noqa: E501
                attempts=3,
            ),
        ]
        mock_run_command.assert_has_calls(calls)

    def test_ensure_error_on_wrong_override(self, getpass):
        with self.assertRaises(AnsibleFailJson) as ansible_err:
            set_module_args(
                {
                    "values_secrets": os.path.join(
                        self.testdir_v2,
                        "values-secret-v2-wrong-override.yaml",
                    ),
                }
            )
            vault_load_secrets.main()

        ret = ansible_err.exception.args[0]
        self.assertEqual(ret["failed"], True)
        assert (
            ret["args"][1]
            == "'override' attribute requires 'onMissingValue' to be set to 'generate'"
        )

    def test_ensure_override_works(self, getpass):
        set_module_args(
            {
                "values_secrets": os.path.join(
                    self.testdir_v2, "values-secret-v2-test-override.yaml"
                ),
            }
        )
        # this will be used for both a secret and a file path
        getpass.return_value = "/tmp/ca.crt"
        with patch.object(
            load_secrets_v2.LoadSecretsV2, "_run_command"
        ) as mock_run_command:
            stdout = "configuration updated"
            stderr = ""
            ret = 0
            mock_run_command.return_value = ret, stdout, stderr  # successful execution

            with self.assertRaises(AnsibleExitJson) as result:
                vault_load_secrets.main()
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
                'echo \'length=10\nrule "charset" { charset = "abcdefghijklmnopqrstuvwxyz" min-chars = 1 }\nrule "charset" { charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" min-chars = 1 }\nrule "charset" { charset = "0123456789" min-chars = 1 }\n\' | oc exec -n vault vault-0 -i -- sh -c \'cat - > /tmp/basicPolicy.hcl\';oc exec -n vault vault-0 -i -- sh -c \'vault write sys/policies/password/basicPolicy  policy=@/tmp/basicPolicy.hcl\'',  # noqa: E501
                attempts=3,
            ),
            call(
                'echo \'length=20\nrule "charset" { charset = "abcdefghijklmnopqrstuvwxyz" min-chars = 1 }\nrule "charset" { charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" min-chars = 1 }\nrule "charset" { charset = "0123456789" min-chars = 1 }\nrule "charset" { charset = "!@#%^&*" min-chars = 1 }\n\' | oc exec -n vault vault-0 -i -- sh -c \'cat - > /tmp/advancedPolicy.hcl\';oc exec -n vault vault-0 -i -- sh -c \'vault write sys/policies/password/advancedPolicy  policy=@/tmp/advancedPolicy.hcl\'',  # noqa: E501
                attempts=3,
            ),
            call(
                'oc exec -n vault vault-0 -i -- sh -c "vault kv get -mount=secret -field=secret region-one/config-demo"',  # noqa: E501
                attempts=1,
                checkrc=False,
            ),
            call(
                'oc exec -n vault vault-0 -i -- sh -c "vault kv get -mount=secret -field=secret snowflake.blueprints.rhecoeng.com/config-demo"',  # noqa: E501
                attempts=1,
                checkrc=False,
            ),
        ]
        mock_run_command.assert_has_calls(calls)

    def test_ensure_error_wrong_ini_file(self, getpass):
        with self.assertRaises(AnsibleFailJson) as ansible_err:
            set_module_args(
                {
                    "values_secrets": os.path.join(
                        self.testdir_v2, "values-secret-v2-wrong-ini-file.yaml"
                    ),
                }
            )
            vault_load_secrets.main()

        ret = ansible_err.exception.args[0]
        self.assertEqual(ret["failed"], True)
        assert ret["args"][1] == "ini_file requires at least ini_key to be defined"

    def test_ensure_ini_file_works(self, getpass):
        set_module_args(
            {
                "values_secrets": os.path.join(
                    self.testdir_v2, "values-secret-v2-ini-file.yaml"
                ),
            }
        )
        with patch.object(
            load_secrets_v2.LoadSecretsV2, "_run_command"
        ) as mock_run_command:
            stdout = "configuration updated"
            stderr = ""
            ret = 0
            mock_run_command.return_value = ret, stdout, stderr  # successful execution

            with self.assertRaises(AnsibleExitJson) as result:
                vault_load_secrets.main()
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
                "oc exec -n vault vault-0 -i -- sh -c \"vault kv put -mount=secret hub/aws aws_access_key_id='123123'\"",  # noqa: E501
                attempts=3,
            ),
            call(
                "oc exec -n vault vault-0 -i -- sh -c \"vault kv patch -mount=secret hub/aws aws_secret_access_key='abcdefghi'\"",  # noqa: E501
                attempts=3,
            ),
            call(
                "oc exec -n vault vault-0 -i -- sh -c \"vault kv put -mount=secret hub/awsfoobar aws_access_key_id='345345'\"",  # noqa: E501
                attempts=3,
            ),
            call(
                "oc exec -n vault vault-0 -i -- sh -c \"vault kv patch -mount=secret hub/awsfoobar aws_secret_access_key='rstuvwxyz'\"",  # noqa: E501
                attempts=3,
            ),
        ]
        mock_run_command.assert_has_calls(calls)


if __name__ == "__main__":
    unittest.main()
