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
Simple module to test parse_secret_info
"""

import base64
import configparser
import json
import os
import sys
import unittest
from unittest import mock
from unittest.mock import patch

from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes
from test_util_datastructures import (
    DEFAULT_KUBERNETES_METADATA,
    DEFAULT_KUBERNETES_SECRET_OBJECT,
    DEFAULT_PARSED_SECRET_VALUE,
    DEFAULT_VAULT_POLICIES,
)

# from unittest.mock import call, patch

# TODO(bandini): I could not come up with something better to force the imports to be existing
# when we "import parse_secrets_info"
sys.path.insert(1, "./ansible/plugins/module_utils")
sys.path.insert(1, "./ansible/plugins/modules")

import load_secrets_common  # noqa: E402

sys.modules["ansible.module_utils.load_secrets_common"] = load_secrets_common

import parse_secrets_v2  # noqa: E402

sys.modules["ansible.module_utils.parse_secrets_v2"] = parse_secrets_v2

import parse_secrets_info  # noqa: E402

sys.modules["ansible.modules.parse_secrets_info"] = parse_secrets_info


def set_module_args(args):
    """prepare arguments so that they will be picked up during module creation"""
    args = json.dumps({"ANSIBLE_MODULE_ARGS": args})
    basic._ANSIBLE_ARGS = to_bytes(args)


class BytesEncoder(json.JSONEncoder):

    def default(self, o):
        if isinstance(o, bytes):
            return base64.b64encode(o).decode("ascii")
        else:
            return super().default(o)


def json_str(a):
    return json.dumps(a, sort_keys=True, cls=BytesEncoder)


def ds_eq(a, b):
    """
    This function takes two arbitrary data structures, sorts their keys, stringifies them into JSON
    and compares them. The idea here is to test data structure difference without having to write
    an involved recursive data structure parser. If the function returns true, the two data
    structures are equal.
    """
    print("a=" + json_str(a))
    print("b=" + json_str(b))
    return json_str(a) == json_str(b)


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

    def create_testbinfile(self):
        with open(self.binfilename, "wb") as f:
            f.write(bytes([8, 6, 7, 5, 3, 0, 9]))
            f.close()

    def setUp(self):
        self.binfilename = "/tmp/testbinfile.bin"
        self.mock_module_helper = patch.multiple(
            basic.AnsibleModule, exit_json=exit_json, fail_json=fail_json
        )
        self.mock_module_helper.start()
        self.addCleanup(self.mock_module_helper.stop)
        self.testdir_v2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "v2")
        self.testfile = open("/tmp/ca.crt", "w")
        self.create_inifile()
        self.create_testbinfile()
        # For ~/expanduser tests
        self.orig_home = os.environ["HOME"]
        os.environ["HOME"] = self.testdir_v2

    def tearDown(self):
        os.environ["HOME"] = self.orig_home
        self.testfile.close()
        try:
            os.remove("/tmp/ca.crt")
            os.remove(self.binfilename)
            # os.remove("/tmp/awscredentials")
        except OSError:
            pass

    def get_file_as_stdout(self, filename, openmode="r"):
        with open(filename, mode=openmode, encoding="utf-8") as f:
            return f.read()

    def test_module_fail_when_required_args_missing(self, getpass):
        with self.assertRaises(AnsibleFailJson):
            set_module_args({})
            parse_secrets_info.main()

    def test_module_parse_base(self, getpass):
        getpass.return_value = "/tmp/ca.crt"
        testfile_output = self.get_file_as_stdout(
            os.path.join(self.testdir_v2, "values-secret-v2-base.yaml")
        )
        with self.assertRaises(AnsibleExitJson) as result:
            set_module_args(
                {
                    "values_secrets_plaintext": testfile_output,
                }
            )
            parse_secrets_info.main()

        ret = result.exception.args[0]
        self.assertTrue(
            (ret["failed"] is False)
            and (ret["changed"] is False)
            and (len(ret["parsed_secrets"])) == 1
            and (len(ret["kubernetes_secret_objects"]) == 0)
        )

    def test_module_parse_base_parsed_secrets(self, getpass):
        getpass.return_value = "/tmp/ca.crt"
        testfile_output = self.get_file_as_stdout(
            os.path.join(self.testdir_v2, "values-secret-v2-base.yaml")
        )
        with self.assertRaises(AnsibleExitJson) as result:
            set_module_args(
                {
                    "values_secrets_plaintext": testfile_output,
                }
            )
            parse_secrets_info.main()

        vp = DEFAULT_VAULT_POLICIES | {
            "basicPolicy": 'length=10\nrule "charset" { charset = "abcdefghijklmnopqrstuvwxyz" min-chars = 1 }\nrule "charset" { charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" min-chars = 1 }\nrule "charset" { charset = "0123456789" min-chars = 1 }\n',  # noqa: E501
            "advancedPolicy": 'length=20\nrule "charset" { charset = "abcdefghijklmnopqrstuvwxyz" min-chars = 1 }\nrule "charset" { charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" min-chars = 1 }\nrule "charset" { charset = "0123456789" min-chars = 1 }\nrule "charset" { charset = "!@#%^&*" min-chars = 1 }\n',  # noqa: E501
        }

        # Beware reading this structure aloud to your cat...
        pspsps = {
            "config-demo": DEFAULT_PARSED_SECRET_VALUE
            | {
                "name": "config-demo",
                "fields": {
                    "secret": None,
                    "secret2": "/tmp/ca.crt",
                    "ca_crt": "",
                    "ca_crt2": "",
                },
                "base64": ["ca_crt2"],
                "generate": ["secret"],
                "override": ["secret"],
                "vault_policies": {
                    "secret": "basicPolicy",
                },
                "vault_prefixes": [
                    "region-one",
                    "snowflake.blueprints.rhecoeng.com",
                ],
                "paths": {
                    "ca_crt": "/tmp/ca.crt",
                    "ca_crt2": "/tmp/ca.crt",
                },
            },
        }

        ret = result.exception.args[0]
        self.assertTrue(
            (ret["failed"] is False)
            and (ret["changed"] is False)
            and (ds_eq(vp, ret["vault_policies"]))
            and (ds_eq(pspsps, ret["parsed_secrets"]))
        )

    def test_module_parsed_secret_ini_files(self, getpass):
        testfile_output = self.get_file_as_stdout(
            os.path.join(self.testdir_v2, "values-secret-v2-ini-file.yaml")
        )
        with self.assertRaises(AnsibleExitJson) as result:
            set_module_args(
                {
                    "values_secrets_plaintext": testfile_output,
                }
            )
            parse_secrets_info.main()

        ps = {
            "aws": DEFAULT_PARSED_SECRET_VALUE
            | {
                "name": "aws",
                "fields": {
                    "aws_access_key_id": "123123",
                    "aws_secret_access_key": "abcdefghi",
                },
                "ini_file": {
                    "aws_access_key_id": {
                        "ini_file": "/tmp/awscredentials",
                        "ini_section": "default",
                        "ini_key": "aws_access_key_id",
                    },
                    "aws_secret_access_key": {
                        "ini_file": "/tmp/awscredentials",
                        "ini_section": "default",
                        "ini_key": "aws_secret_access_key",
                    },
                },
            },
            "awsfoobar": DEFAULT_PARSED_SECRET_VALUE
            | {
                "name": "awsfoobar",
                "fields": {
                    "aws_access_key_id": "345345",
                    "aws_secret_access_key": "rstuvwxyz",
                },
                "ini_file": {
                    "aws_access_key_id": {
                        "ini_file": "/tmp/awscredentials",
                        "ini_section": "foobar",
                        "ini_key": "aws_access_key_id",
                    },
                    "aws_secret_access_key": {
                        "ini_file": "/tmp/awscredentials",
                        "ini_section": "foobar",
                        "ini_key": "aws_secret_access_key",
                    },
                },
            },
        }

        ret = result.exception.args[0]
        self.assertTrue(
            (ret["failed"] is False)
            and (ret["changed"] is False)
            and (len(ret["parsed_secrets"]) == 2)
            and (ds_eq(ps, ret["parsed_secrets"]))
        )

    def test_module_parsed_secret_ini_files_base64(self, getpass):
        testfile_output = self.get_file_as_stdout(
            os.path.join(self.testdir_v2, "values-secret-v2-ini-file-b64.yaml")
        )
        with self.assertRaises(AnsibleExitJson) as result:
            set_module_args(
                {
                    "values_secrets_plaintext": testfile_output,
                }
            )
            parse_secrets_info.main()

        ps = {
            "aws": DEFAULT_PARSED_SECRET_VALUE
            | {
                "name": "aws",
                "fields": {
                    "aws_access_key_id": "A123456789012345678A",
                    "aws_secret_access_key": "A12345678901234567890123456789012345678A",
                },
                "ini_file": {
                    "aws_access_key_id": {
                        "ini_file": f"{os.environ['HOME']}/aws-example.ini",
                        "ini_section": "default",
                        "ini_key": "aws_access_key_id",
                    },
                    "aws_secret_access_key": {
                        "ini_file": f"{os.environ['HOME']}/aws-example.ini",
                        "ini_section": "default",
                        "ini_key": "aws_secret_access_key",
                    },
                },
            },
            "awsb64": DEFAULT_PARSED_SECRET_VALUE
            | {
                "name": "awsb64",
                "fields": {
                    "aws_access_key_id": "QTEyMzQ1Njc4OTAxMjM0NTY3OEE=",
                    "aws_secret_access_key": "QTEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDEyMzQ1Njc4QQ==",
                },
                "base64": [
                    "aws_access_key_id",
                    "aws_secret_access_key",
                ],
                "ini_file": {
                    "aws_access_key_id": {
                        "ini_file": f"{os.environ['HOME']}/aws-example.ini",
                        "ini_section": "default",
                        "ini_key": "aws_access_key_id",
                    },
                    "aws_secret_access_key": {
                        "ini_file": f"{os.environ['HOME']}/aws-example.ini",
                        "ini_section": "default",
                        "ini_key": "aws_secret_access_key",
                    },
                },
            },
        }

        ret = result.exception.args[0]
        self.assertTrue(
            (ret["failed"] is False)
            and (ret["changed"] is False)
            and (len(ret["parsed_secrets"]) == 2)
            and (len(ret["kubernetes_secret_objects"]) == 0)
            and (ds_eq(ps, ret["parsed_secrets"]))
        )

    def test_module_parsed_secret_ini_files_base64_kubernetes(self, getpass):
        testfile_output = self.get_file_as_stdout(
            os.path.join(self.testdir_v2, "values-secret-v2-ini-file-b64.yaml")
        )
        with self.assertRaises(AnsibleExitJson) as result:
            set_module_args(
                {
                    "values_secrets_plaintext": testfile_output,
                    "secrets_backing_store": "kubernetes",
                }
            )
            parse_secrets_info.main()

        ps = {
            "aws": DEFAULT_PARSED_SECRET_VALUE
            | {
                "name": "aws",
                "fields": {
                    "aws_access_key_id": "A123456789012345678A",
                    "aws_secret_access_key": "A12345678901234567890123456789012345678A",
                },
                "ini_file": {
                    "aws_access_key_id": {
                        "ini_file": f"{os.environ['HOME']}/aws-example.ini",
                        "ini_section": "default",
                        "ini_key": "aws_access_key_id",
                    },
                    "aws_secret_access_key": {
                        "ini_file": f"{os.environ['HOME']}/aws-example.ini",
                        "ini_section": "default",
                        "ini_key": "aws_secret_access_key",
                    },
                },
            },
            "awsb64": DEFAULT_PARSED_SECRET_VALUE
            | {
                "name": "awsb64",
                "fields": {
                    "aws_access_key_id": "QTEyMzQ1Njc4OTAxMjM0NTY3OEE=",
                    "aws_secret_access_key": "QTEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDEyMzQ1Njc4QQ==",
                },
                "base64": [
                    "aws_access_key_id",
                    "aws_secret_access_key",
                ],
                "ini_file": {
                    "aws_access_key_id": {
                        "ini_file": f"{os.environ['HOME']}/aws-example.ini",
                        "ini_section": "default",
                        "ini_key": "aws_access_key_id",
                    },
                    "aws_secret_access_key": {
                        "ini_file": f"{os.environ['HOME']}/aws-example.ini",
                        "ini_section": "default",
                        "ini_key": "aws_secret_access_key",
                    },
                },
            },
        }

        ret = result.exception.args[0]
        self.assertTrue(
            (ret["failed"] is False)
            and (ret["changed"] is False)
            and (len(ret["parsed_secrets"]) == 2)
            and (len(ret["kubernetes_secret_objects"]) == 2)
            and (ds_eq(ps, ret["parsed_secrets"]))
        )

    def test_module_default_labels(self, getpass):
        testfile_output = self.get_file_as_stdout(
            os.path.join(self.testdir_v2, "values-secret-v2-default-labels.yaml")
        )
        with self.assertRaises(AnsibleExitJson) as result:
            set_module_args(
                {
                    "values_secrets_plaintext": testfile_output,
                    "secrets_backing_store": "kubernetes",
                }
            )
            parse_secrets_info.main()

        ret = result.exception.args[0]
        self.assertTrue(
            ds_eq(
                ret["kubernetes_secret_objects"][0],
                DEFAULT_KUBERNETES_SECRET_OBJECT
                | {
                    "metadata": DEFAULT_KUBERNETES_METADATA
                    | {
                        "name": "test-secret",
                        "labels": {"testlabel": "4"},
                        "namespace": "validated-patterns-secrets",
                    },
                    "stringData": {"username": "user"},
                },
            )
        )

    def test_module_override_labels(self, getpass):
        testfile_output = self.get_file_as_stdout(
            os.path.join(self.testdir_v2, "values-secret-v2-override-labels.yaml")
        )
        with self.assertRaises(AnsibleExitJson) as result:
            set_module_args(
                {
                    "values_secrets_plaintext": testfile_output,
                    "secrets_backing_store": "kubernetes",
                }
            )
            parse_secrets_info.main()
        ret = result.exception.args[0]
        self.assertTrue(
            ds_eq(
                ret["kubernetes_secret_objects"][0],
                DEFAULT_KUBERNETES_SECRET_OBJECT
                | {
                    "metadata": DEFAULT_KUBERNETES_METADATA
                    | {
                        "name": "test-secret",
                        "labels": {"overridelabel": "42"},
                    },
                    "stringData": {"username": "user"},
                },
            )
        )

    def test_module_override_namespace(self, getpass):
        testfile_output = self.get_file_as_stdout(
            os.path.join(self.testdir_v2, "values-secret-v2-override-namespace.yaml")
        )
        with self.assertRaises(AnsibleExitJson) as result:
            set_module_args(
                {
                    "values_secrets_plaintext": testfile_output,
                    "secrets_backing_store": "kubernetes",
                }
            )
            parse_secrets_info.main()
        ret = result.exception.args[0]
        self.assertTrue(
            len(ret["kubernetes_secret_objects"]) == 1
            and ds_eq(
                ret["kubernetes_secret_objects"][0],
                DEFAULT_KUBERNETES_SECRET_OBJECT
                | {
                    "metadata": DEFAULT_KUBERNETES_METADATA
                    | {
                        "name": "test-secret",
                        "namespace": "overridden-namespace",
                    },
                    "stringData": {"username": "user"},
                },
            )
        )

    def test_module_none_extra_namespaces(self, getpass):
        testfile_output = self.get_file_as_stdout(
            os.path.join(self.testdir_v2, "values-secret-v2-more-namespaces.yaml")
        )
        with self.assertRaises(AnsibleExitJson) as result:
            set_module_args(
                {
                    "values_secrets_plaintext": testfile_output,
                    "secrets_backing_store": "none",
                }
            )
            parse_secrets_info.main()
        ret = result.exception.args[0]
        self.assertTrue(
            len(ret["kubernetes_secret_objects"]) == 2
            and ds_eq(
                ret["kubernetes_secret_objects"][0],
                DEFAULT_KUBERNETES_SECRET_OBJECT
                | {
                    "metadata": DEFAULT_KUBERNETES_METADATA
                    | {
                        "name": "test-secret",
                        "namespace": "default",
                    },
                    "stringData": {"username": "user"},
                },
            )
            and ds_eq(
                ret["kubernetes_secret_objects"][1],
                DEFAULT_KUBERNETES_SECRET_OBJECT
                | {
                    "metadata": DEFAULT_KUBERNETES_METADATA
                    | {
                        "name": "test-secret",
                        "namespace": "extra",
                    },
                    "stringData": {"username": "user"},
                },
            )
        )

    def test_module_override_type_kubernetes(self, getpass):
        testfile_output = self.get_file_as_stdout(
            os.path.join(self.testdir_v2, "values-secret-v2-override-type.yaml")
        )
        with self.assertRaises(AnsibleExitJson) as result:
            set_module_args(
                {
                    "values_secrets_plaintext": testfile_output,
                    "secrets_backing_store": "kubernetes",
                }
            )
            parse_secrets_info.main()
        ret = result.exception.args[0]
        self.assertTrue(
            len(ret["kubernetes_secret_objects"]) == 1
            and ds_eq(
                ret["kubernetes_secret_objects"][0],
                DEFAULT_KUBERNETES_SECRET_OBJECT
                | {
                    "type": "user-specified",
                    "metadata": DEFAULT_KUBERNETES_METADATA
                    | {
                        "name": "test-secret",
                    },
                    "stringData": {"username": "user"},
                },
            )
        )

    def test_module_override_type_none(self, getpass):
        testfile_output = self.get_file_as_stdout(
            os.path.join(self.testdir_v2, "values-secret-v2-override-type-none.yaml")
        )
        with self.assertRaises(AnsibleExitJson) as result:
            set_module_args(
                {
                    "values_secrets_plaintext": testfile_output,
                    "secrets_backing_store": "none",
                }
            )
            parse_secrets_info.main()
        ret = result.exception.args[0]
        self.assertTrue(
            len(ret["kubernetes_secret_objects"]) == 1
            and ds_eq(
                ret["kubernetes_secret_objects"][0],
                DEFAULT_KUBERNETES_SECRET_OBJECT
                | {
                    "type": "user-specified",
                    "metadata": DEFAULT_KUBERNETES_METADATA
                    | {"name": "test-secret", "namespace": "default"},
                    "stringData": {"username": "user"},
                },
            )
        )

    def test_module_secret_file_contents(self, getpass):
        testfile_output = self.get_file_as_stdout(
            os.path.join(self.testdir_v2, "values-secret-v2-file-contents.yaml")
        )
        with self.assertRaises(AnsibleExitJson) as result:
            set_module_args(
                {
                    "values_secrets_plaintext": testfile_output,
                    "secrets_backing_store": "kubernetes",
                }
            )
            parse_secrets_info.main()
        ret = result.exception.args[0]
        self.assertTrue(
            len(ret["kubernetes_secret_objects"]) == 1
            and ds_eq(
                ret["kubernetes_secret_objects"][0],
                DEFAULT_KUBERNETES_SECRET_OBJECT
                | {
                    "metadata": DEFAULT_KUBERNETES_METADATA
                    | {
                        "name": "test-secret",
                    },
                    "stringData": {"username": "This space intentionally left blank\n"},
                },
            )
        )

    def test_module_secret_file_contents_b64(self, getpass):
        testfile_output = self.get_file_as_stdout(
            os.path.join(self.testdir_v2, "values-secret-v2-file-contents-b64.yaml")
        )
        with self.assertRaises(AnsibleExitJson) as result:
            set_module_args(
                {
                    "values_secrets_plaintext": testfile_output,
                    "secrets_backing_store": "kubernetes",
                }
            )
            parse_secrets_info.main()
        ret = result.exception.args[0]
        self.assertTrue(
            len(ret["kubernetes_secret_objects"]) == 1
            and ds_eq(
                ret["kubernetes_secret_objects"][0],
                DEFAULT_KUBERNETES_SECRET_OBJECT
                | {
                    "metadata": DEFAULT_KUBERNETES_METADATA
                    | {
                        "name": "test-secret",
                    },
                    "stringData": {
                        "username": "VGhpcyBzcGFjZSBpbnRlbnRpb25hbGx5IGxlZnQgYmxhbmsK"
                    },
                },
            )
        )

    def test_module_secret_file_contents_double_b64(self, getpass):
        testfile_output = self.get_file_as_stdout(
            os.path.join(
                self.testdir_v2, "values-secret-v2-file-contents-double-b64.yaml"
            )
        )
        with self.assertRaises(AnsibleExitJson) as result:
            set_module_args(
                {
                    "values_secrets_plaintext": testfile_output,
                    "secrets_backing_store": "kubernetes",
                }
            )
            parse_secrets_info.main()
        ret = result.exception.args[0]
        self.assertTrue(
            len(ret["kubernetes_secret_objects"]) == 1
            and ds_eq(
                ret["kubernetes_secret_objects"][0],
                DEFAULT_KUBERNETES_SECRET_OBJECT
                | {
                    "metadata": DEFAULT_KUBERNETES_METADATA
                    | {
                        "name": "test-secret",
                    },
                    "stringData": {
                        "username": "VkdocGN5QnpjR0ZqWlNCcGJuUmxiblJwYjI1aGJHeDVJR3hsWm5RZ1lteGhibXNL"
                    },
                },
            )
        )

    def test_module_secret_file_contents_binary_b64(self, getpass):
        testfile_output = self.get_file_as_stdout(
            os.path.join(self.testdir_v2, "values-secret-v2-secret-binary-b64.yaml")
        )
        with self.assertRaises(AnsibleExitJson) as result:
            set_module_args(
                {
                    "values_secrets_plaintext": testfile_output,
                    "secrets_backing_store": "kubernetes",
                }
            )
            parse_secrets_info.main()
        ret = result.exception.args[0]

        # The binary bytes are [ 8, 6, 7, 5, 3, 0, 9 ] (IYKYK)
        self.assertTrue(
            len(ret["kubernetes_secret_objects"]) == 1
            and ds_eq(
                ret["kubernetes_secret_objects"][0],
                DEFAULT_KUBERNETES_SECRET_OBJECT
                | {
                    "metadata": DEFAULT_KUBERNETES_METADATA
                    | {
                        "name": "secret",
                    },
                    "stringData": {"secret": "CAYHBQMACQ=="},
                },
            )
        )

    def test_ensure_success_retrieving_block_yaml_policy(self, getpass):
        testfile_output = self.get_file_as_stdout(
            os.path.join(self.testdir_v2, "values-secret-v2-defaultvp-policy.yaml")
        )
        with self.assertRaises(AnsibleExitJson) as ansible_err:
            set_module_args(
                {
                    "values_secrets_plaintext": testfile_output,
                    "secrets_backing_store": "vault",
                }
            )
            parse_secrets_info.main()

        ret = ansible_err.exception.args[0]
        self.assertTrue(
            ds_eq(
                ret["vault_policies"],
                {
                    "basicPolicy": 'length=10\nrule "charset" { charset = "abcdefghijklmnopqrstuvwxyz" min-chars = 1 }\nrule "charset" { charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" min-chars = 1 }\nrule "charset" { charset = "0123456789" min-chars = 1 }\n',  # noqa: E501
                    "validatedPatternDefaultPolicy": 'length=20\nrule "charset" { charset = "abcdefghijklmnopqrstuvwxyz" min-chars = 1 }\nrule "charset" { charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" min-chars = 1 }\nrule "charset" { charset = "0123456789" min-chars = 1 }\nrule "charset" { charset = "!@#%^&*" min-chars = 1 }\n',  # noqa: E501
                },
            )
        )

    def test_ensure_success_retrieving_block_yaml_value(self, getpass):
        testfile_output = self.get_file_as_stdout(
            os.path.join(self.testdir_v2, "values-secret-v2-block-yamlstring.yaml")
        )
        with self.assertRaises(AnsibleExitJson) as ansible_err:
            set_module_args(
                {
                    "values_secrets_plaintext": testfile_output,
                    "secrets_backing_store": "vault",
                }
            )
            parse_secrets_info.main()

        ret = ansible_err.exception.args[0]
        self.assertTrue(
            ds_eq(
                ret["parsed_secrets"],
                {
                    "config-demo": DEFAULT_PARSED_SECRET_VALUE
                    | {
                        "fields": {
                            "sshprivkey": "ssh-rsa oNb/kAvwdQl+FKdwzzKo5rnGIB68UOxWoaKPnKdgF/ts67CDBslWGnpUZCpp8TdaxfHmpoyA6nutMwQw8OAMEUybxvilDn+ZVJ/5qgfRBdi8wLKRLTIj0v+ZW7erN9yuZG53xUQAaQjivM3cRyNLIZ9torShYaYwD1UTTDkV97RMfNDlWI5f5FGRvfy429ZfCwbUWUbijrcv/mWc/uO3x/+MBXwa4f8ubzEYlrt4yH/Vbpzs67kE9UJ9z1zurFUFJydy1ZDAdKSiBS91ImI3ccKnbz0lji2bgSYR0Wp1IQhzSpjyJU2rIu9HAEUh85Rwf2jakfLpMcg/hSBer3sG  kilroy@example.com",  # noqa: E501
                            "sshpubkey": "-----BEGIN OPENSSH PRIVATE KEY-----\nTtzxGgWrNerAr1hzUqPW2xphF/Aur1rQXSLv4J7frEJxNED6u/eScsNgwJMGXwRx7QYVohh0ARHVhJdUzJK7pEIphi4BGw==\nwlo+oQsi828b47SKZB8/K9dbeLlLiXh9/hu47MGpeGHZsKbjAdauncuw+YUDDN2EADJjasNMZHjxYhXKtqDjXTIw1X1n0Q==\n-----END OPENSSH PRIVATE KEY-----",  # noqa: E501
                        },
                        "name": "config-demo",
                    }
                },
            )
        )

    def test_ensure_kubernetes_object_block_yaml_value(self, getpass):
        testfile_output = self.get_file_as_stdout(
            os.path.join(self.testdir_v2, "values-secret-v2-block-yamlstring.yaml")
        )
        with self.assertRaises(AnsibleExitJson) as ansible_err:
            set_module_args(
                {
                    "values_secrets_plaintext": testfile_output,
                    "secrets_backing_store": "kubernetes",
                }
            )
            parse_secrets_info.main()

        ret = ansible_err.exception.args[0]
        self.assertTrue(
            ds_eq(
                ret["kubernetes_secret_objects"][0],
                DEFAULT_KUBERNETES_SECRET_OBJECT
                | {
                    "metadata": DEFAULT_KUBERNETES_METADATA
                    | {
                        "name": "config-demo",
                    },
                    "stringData": {
                        "sshprivkey": "ssh-rsa oNb/kAvwdQl+FKdwzzKo5rnGIB68UOxWoaKPnKdgF/ts67CDBslWGnpUZCpp8TdaxfHmpoyA6nutMwQw8OAMEUybxvilDn+ZVJ/5qgfRBdi8wLKRLTIj0v+ZW7erN9yuZG53xUQAaQjivM3cRyNLIZ9torShYaYwD1UTTDkV97RMfNDlWI5f5FGRvfy429ZfCwbUWUbijrcv/mWc/uO3x/+MBXwa4f8ubzEYlrt4yH/Vbpzs67kE9UJ9z1zurFUFJydy1ZDAdKSiBS91ImI3ccKnbz0lji2bgSYR0Wp1IQhzSpjyJU2rIu9HAEUh85Rwf2jakfLpMcg/hSBer3sG  kilroy@example.com",  # noqa: E501
                        "sshpubkey": "-----BEGIN OPENSSH PRIVATE KEY-----\nTtzxGgWrNerAr1hzUqPW2xphF/Aur1rQXSLv4J7frEJxNED6u/eScsNgwJMGXwRx7QYVohh0ARHVhJdUzJK7pEIphi4BGw==\nwlo+oQsi828b47SKZB8/K9dbeLlLiXh9/hu47MGpeGHZsKbjAdauncuw+YUDDN2EADJjasNMZHjxYhXKtqDjXTIw1X1n0Q==\n-----END OPENSSH PRIVATE KEY-----",  # noqa: E501
                    },
                },
            )
        )

    def test_ensure_kubernetes_backend_allowed(self, getpass):
        testfile_output = self.get_file_as_stdout(
            os.path.join(self.testdir_v2, "values-secret-v2-base-k8s-backend.yaml")
        )
        with self.assertRaises(AnsibleExitJson) as ansible_err:
            set_module_args(
                {
                    "values_secrets_plaintext": testfile_output,
                    "secrets_backing_store": "kubernetes",
                }
            )
            parse_secrets_info.main()

        ret = ansible_err.exception.args[0]
        self.assertFalse(ret["failed"])

    def test_ensure_none_backend_allowed(self, getpass):
        testfile_output = self.get_file_as_stdout(
            os.path.join(self.testdir_v2, "values-secret-v2-base-none-backend.yaml")
        )
        with self.assertRaises(AnsibleExitJson) as ansible_err:
            set_module_args(
                {
                    "values_secrets_plaintext": testfile_output,
                    "secrets_backing_store": "none",
                }
            )
            parse_secrets_info.main()

        ret = ansible_err.exception.args[0]
        self.assertFalse(ret["failed"])

    def test_ensure_error_conflicting_backends(self, getpass):
        testfile_output = self.get_file_as_stdout(
            os.path.join(self.testdir_v2, "values-secret-v2-base-k8s-backend.yaml")
        )
        with self.assertRaises(AnsibleFailJson) as ansible_err:
            set_module_args(
                {
                    "values_secrets_plaintext": testfile_output,
                    "secrets_backing_store": "vault",
                }
            )
            parse_secrets_info.main()

        ret = ansible_err.exception.args[0]
        self.assertEqual(ret["failed"], True)
        assert (
            ret["args"][1]
            == "Secrets file specifies 'kubernetes' backend but pattern config specifies 'vault'."
        )

    def test_ensure_error_unknown_backends(self, getpass):
        testfile_output = self.get_file_as_stdout(
            os.path.join(self.testdir_v2, "values-secret-v2-base-unknown-backend.yaml")
        )
        with self.assertRaises(AnsibleFailJson) as ansible_err:
            set_module_args(
                {
                    "values_secrets_plaintext": testfile_output,
                    "secrets_backing_store": "unknown",
                }
            )
            parse_secrets_info.main()

        ret = ansible_err.exception.args[0]
        self.assertEqual(ret["failed"], True)
        assert (
            ret["args"][1]
            == "Currently only the 'vault', 'kubernetes' and 'none' backingStores are supported: unknown"
        )

    def test_ensure_error_secrets_same_name(self, getpass):
        testfile_output = self.get_file_as_stdout(
            os.path.join(self.testdir_v2, "values-secret-v2-same-secret-names.yaml")
        )
        with self.assertRaises(AnsibleFailJson) as ansible_err:
            set_module_args(
                {
                    "values_secrets_plaintext": testfile_output,
                }
            )
            parse_secrets_info.main()

        ret = ansible_err.exception.args[0]
        self.assertEqual(ret["failed"], True)
        assert (
            ret["args"][1] == "You cannot have duplicate secret names: ['config-demo']"
        )

    def test_ensure_error_fields_same_name(self, getpass):
        testfile_output = self.get_file_as_stdout(
            os.path.join(self.testdir_v2, "values-secret-v2-same-field-names.yaml")
        )
        with self.assertRaises(AnsibleFailJson) as ansible_err:
            set_module_args(
                {
                    "values_secrets_plaintext": testfile_output,
                }
            )
            parse_secrets_info.main()

        ret = ansible_err.exception.args[0]
        self.assertEqual(ret["failed"], True)
        assert ret["args"][1] == "You cannot have duplicate field names: ['secret']"

    def test_ensure_generate_errors_on_kubernetes(self, getpass):
        testfile_output = self.get_file_as_stdout(
            os.path.join(self.testdir_v2, "values-secret-v2-generic-onlygenerate.yaml")
        )
        with self.assertRaises(AnsibleFailJson) as ansible_err:
            set_module_args(
                {
                    "values_secrets_plaintext": testfile_output,
                    "secrets_backing_store": "kubernetes",
                }
            )
            parse_secrets_info.main()

        ret = ansible_err.exception.args[0]
        self.assertEqual(ret["failed"], True)
        assert (
            ret["args"][1]
            == "You cannot have onMissingValue set to 'generate' unless using vault backingstore for secret config-demo field secret"  # noqa: E501
        )

    def test_ensure_generate_errors_on_none_generate(self, getpass):
        testfile_output = self.get_file_as_stdout(
            os.path.join(self.testdir_v2, "values-secret-v2-generic-onlygenerate.yaml")
        )
        with self.assertRaises(AnsibleFailJson) as ansible_err:
            set_module_args(
                {
                    "values_secrets_plaintext": testfile_output,
                    "secrets_backing_store": "none",
                }
            )
            parse_secrets_info.main()

        ret = ansible_err.exception.args[0]
        self.assertEqual(ret["failed"], True)
        assert (
            ret["args"][1]
            == "You cannot have onMissingValue set to 'generate' unless using vault backingstore for secret config-demo field secret"  # noqa: E501
        )


if __name__ == "__main__":
    unittest.main()
