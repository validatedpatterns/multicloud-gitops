DEFAULT_PARSED_SECRET_VALUE = {
    "name": "overwrite-me",
    "fields": {},
    "base64": [],
    "ini_file": {},
    "generate": [],
    "override": [],
    "vault_mount": "secret",
    "vault_policies": {},
    "vault_prefixes": ["hub"],
    "type": "Opaque",
    "target_namespaces": [],
    "labels": {},
    "annotations": {},
    "paths": {},
}

DEFAULT_KUBERNETES_METADATA = {
    "name": "overwrite-me",
    "labels": {},
    "annotations": {},
    "namespace": "validated-patterns-secrets",
}
DEFAULT_KUBERNETES_SECRET_OBJECT = {
    "kind": "Secret",
    "type": "Opaque",
    "apiVersion": "v1",
    "metadata": DEFAULT_KUBERNETES_METADATA,
    "stringData": {},
}

DEFAULT_VAULT_POLICIES = {
    "validatedPatternDefaultPolicy": (
        "length=20\n"
        'rule "charset" { charset = "abcdefghijklmnopqrstuvwxyz" min-chars = 1 }\n'  # noqa: E501
        'rule "charset" { charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" min-chars = 1 }\n'  # noqa: E501
        'rule "charset" { charset = "0123456789" min-chars = 1 }\n'
        'rule "charset" { charset = "!@#%^&*" min-chars = 1 }\n'
    ),
}

GENERATE_POLICY_B64_TEST = {
    "vault_policies": {
        "basicPolicy": 'length=10\nrule "charset" { charset = "abcdefghijklmnopqrstuvwxyz" min-chars = 1 }\nrule "charset" { charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" min-chars = 1 }\nrule "charset" { charset = "0123456789" min-chars = 1 }\n',  # noqa: E501
        "validatedPatternDefaultPolicy": 'length=20\nrule "charset" { charset = "abcdefghijklmnopqrstuvwxyz" min-chars = 1 }\nrule "charset" { charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" min-chars = 1 }\nrule "charset" { charset = "0123456789" min-chars = 1 }\nrule "charset" { charset = "!@#%^&*" min-chars = 1 }\n',  # noqa: E501
    },
    "parsed_secrets": {
        "config-demo": {
            "annotations": {},
            "base64": ["secret"],
            "fields": {"secret": None},
            "generate": ["secret"],
            "ini_file": {},
            "labels": {},
            "name": "config-demo",
            "namespace": "validated-patterns-secrets",
            "override": ["secret"],
            "paths": {},
            "type": "Opaque",
            "vault_mount": "secret",
            "vault_policies": {"secret": "basicPolicy"},
            "vault_prefixes": ["region-one", "snowflake.blueprints.rhecoeng.com"],
        }
    },
}

PARSED_SECRET_VALUE_TEST = {
    "parsed_secrets": {
        "config-demo": {
            "annotations": {},
            "base64": [],
            "fields": {"secret": "value123"},
            "generate": [],
            "ini_file": {},
            "labels": {},
            "name": "config-demo",
            "namespace": "validated-patterns-secrets",
            "override": [],
            "paths": {},
            "type": "Opaque",
            "vault_mount": "secret",
            "vault_policies": {},
            "vault_prefixes": ["hub"],
        }
    },
    "vault_policies": {
        "validatedPatternDefaultPolicy": 'length=20\nrule "charset" { charset = "abcdefghijklmnopqrstuvwxyz" min-chars = 1 }\nrule "charset" { charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" min-chars = 1 }\nrule "charset" { charset = "0123456789" min-chars = 1 }\nrule "charset" { charset = "!@#%^&*" min-chars = 1 }\n'  # noqa: E501
    },
}

PARSED_SECRET_B64_VALUE_TEST = {
    "parsed_secrets": {
        "config-demo": {
            "annotations": {},
            "base64": ["secret"],
            "fields": {"secret": "dmFsdWUxMjMK"},
            "generate": [],
            "ini_file": {},
            "labels": {},
            "name": "config-demo",
            "namespace": "validated-patterns-secrets",
            "override": [],
            "paths": {},
            "type": "Opaque",
            "vault_mount": "secret",
            "vault_policies": {},
            "vault_prefixes": ["hub"],
        }
    },
    "vault_policies": {
        "validatedPatternDefaultPolicy": 'length=20\nrule "charset" { charset = "abcdefghijklmnopqrstuvwxyz" min-chars = 1 }\nrule "charset" { charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" min-chars = 1 }\nrule "charset" { charset = "0123456789" min-chars = 1 }\nrule "charset" { charset = "!@#%^&*" min-chars = 1 }\n'  # noqa: E501
    },
}

PARSED_SECRET_FILE_INJECTION_TEST = {
    "parsed_secrets": {
        "config-demo": {
            "annotations": {},
            "base64": [],
            "fields": {"secret": "value123"},
            "generate": [],
            "ini_file": {},
            "labels": {},
            "name": "config-demo",
            "namespace": "validated-patterns-secrets",
            "override": [],
            "paths": {},
            "type": "Opaque",
            "vault_mount": "secret",
            "vault_policies": {},
            "vault_prefixes": [
                "secret/region-one",
                "secret/snowflake.blueprints.rhecoeng.com",
            ],
        },
        "config-demo-file": {
            "annotations": {},
            "base64": [],
            "fields": {"test": ""},
            "generate": [],
            "ini_file": {},
            "labels": {},
            "name": "config-demo-file",
            "namespace": "validated-patterns-secrets",
            "override": [],
            "paths": {"test": "/tmp/footest"},
            "type": "Opaque",
            "vault_mount": "secret",
            "vault_policies": {},
            "vault_prefixes": [
                "secret/region-two",
                "secret/snowflake.blueprints.rhecoeng.com",
            ],
        },
    },
    "vault_policies": {
        "validatedPatternDefaultPolicy": 'length=20\nrule "charset" { charset = "abcdefghijklmnopqrstuvwxyz" min-chars = 1 }\nrule "charset" { charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" min-chars = 1 }\nrule "charset" { charset = "0123456789" min-chars = 1 }\nrule "charset" { charset = "!@#%^&*" min-chars = 1 }\n'  # noqa: 501
    },
}

PARSED_SECRET_FILE_B64_INJECTION_TEST = {
    "parsed_secrets": {
        "config-demo": {
            "annotations": {},
            "base64": [],
            "fields": {"secret": "value123"},
            "generate": [],
            "ini_file": {},
            "labels": {},
            "name": "config-demo",
            "namespace": "validated-patterns-secrets",
            "override": [],
            "paths": {},
            "type": "Opaque",
            "vault_mount": "secret",
            "vault_policies": {},
            "vault_prefixes": [
                "secret/region-one",
                "secret/snowflake.blueprints.rhecoeng.com",
            ],
        },
        "config-demo-file": {
            "annotations": {},
            "base64": ["test"],
            "fields": {"test": ""},
            "generate": [],
            "ini_file": {},
            "labels": {},
            "name": "config-demo-file",
            "namespace": "validated-patterns-secrets",
            "override": [],
            "paths": {"test": "/tmp/footest"},
            "type": "Opaque",
            "vault_mount": "secret",
            "vault_policies": {},
            "vault_prefixes": [
                "secret/region-two",
                "secret/snowflake.blueprints.rhecoeng.com",
            ],
        },
    },
    "vault_policies": {
        "validatedPatternDefaultPolicy": 'length=20\nrule "charset" { charset = "abcdefghijklmnopqrstuvwxyz" min-chars = 1 }\nrule "charset" { charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" min-chars = 1 }\nrule "charset" { charset = "0123456789" min-chars = 1 }\nrule "charset" { charset = "!@#%^&*" min-chars = 1 }\n'  # noqa: 501
    },
}
