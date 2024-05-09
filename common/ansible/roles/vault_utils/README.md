# Role Name

Bunch of utilities to manage the vault inside k8s imperatively

## Requirements

ansible-galaxy collection install kubernetes.core (formerly known as community.kubernetes)

## Role Variables

Defaults as to where the values-secret.yaml file is and the two ways to connect to a kubernetes cluster
(KUBERCONFIG and ~/.kube/config respectively):

```yaml
values_secret: "{{ lookup('env', 'HOME') }}/values-secret.yaml"
kubeconfig: "{{ lookup('env', 'KUBECONFIG') }}"
kubeconfig_backup: "{{ lookup('env', 'HOME') }}/.kube/config"
```

Default values for vault configuration:

```yaml
vault_ns: "vault"
vault_pod: "vault-0"
vault_hub: "hub"
vault_hub_kubernetes_host: https://$KUBERNETES_PORT_443_TCP_ADDR:443
# Needs extra escaping due to how it gets injected via shell in the vault
vault_hub_capabilities: '[\\\"read\\\"]'
vault_base_path: "secret"
vault_path: "{{ vault_base_path }}/{{ vault_hub }}"
vault_hub_ttl: "15m"
vault_pki_max_lease_ttl: "8760h"
external_secrets_ns: golang-external-secrets
external_secrets_sa: golang-external-secrets
unseal_secret: "vaultkeys"
unseal_namespace: "imperative"
```

## Dependencies

This relies on [kubernetes.core](https://docs.ansible.com/ansible/latest/collections/kubernetes/core/k8s_module.html)

## Values secret file format

Currently this role supports two formats: version 1.0 (which is the assumed
default when not specified) and version 2.0. The latter is more fatureful and
supports generating secrets directly into the vault and also prompting the user
for a secret.

By default, the first file that will looked up is
`~/.config/hybrid-cloud-patterns/values-secret-<patternname>.yaml`, then
`~/.config/validated-patterns/values-secret-<patternname>.yaml`,
`~/values-secret-<patternname>.yaml` and should that not exist it will look for
`~/values-secret.yaml`.
The paths can be overridden by setting the environment variable `VALUES_SECRET` to the path of the
secret file.

The values secret yaml files can be encrypted with `ansible-vault`. If the role detects they are encrypted, the password to
decrypt them will be prompted when needed.

### Version 1.0

Here is a well-commented example of a version 1.0 file:

```yaml
---
# By default when a top-level 'version: 1.0' is missing it is assumed to be '1.0'
# NEVER COMMIT THESE VALUES TO GIT

secrets:
  # These secrets will be pushed in the vault at secret/hub/test The vault will
  # have secret/hub/test with secret1 and secret2 as keys with their associated
  # values (secrets)
  test:
    secret1: foo
    secret2: bar

  # This ends up as the s3Secret attribute to the path secret/hub/aws
  aws:
    s3Secret: test-secret

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
```

### Version 2.0

Here is a version 2.0 example file (specifying `version: 2.0` is mandatory in this case):

```yaml
# NEVER COMMIT THESE VALUES TO GIT (unless your file only uses generated
# passwords or only points to files)

# Needed to specify the new format (missing version means old version: 1.0 by default)
version: 2.0

backingStore: vault # 'vault' is the default when omitted

# These are the vault policies to be created in the vault
# these are used when we let the vault generate the passwords
# by setting the 'onMissingValue' attribute to 'generate'
# See https://developer.hashicorp.com/vault/docs/concepts/password-policies
vaultPolicies:
  basicPolicy: |
    length=10
    rule "charset" { charset = "abcdefghijklmnopqrstuvwxyz" min-chars = 1 }
    rule "charset" { charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" min-chars = 1 }
    rule "charset" { charset = "0123456789" min-chars = 1 }

  advancedPolicy: |
    length=20
    rule "charset" { charset = "abcdefghijklmnopqrstuvwxyz" min-chars = 1 }
    rule "charset" { charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" min-chars = 1 }
    rule "charset" { charset = "0123456789" min-chars = 1 }
    rule "charset" { charset = "!@#$%^&*" min-chars = 1 }

# This is the mandatory top-level secrets entry
secrets:
  # This will create the following keys + attributes:
  # - secret/region-one/config-demo:
  #     secret: ...<generated basicPolicy secret>...
  #     secretprompt: ...<as input by the user>...
  #     secretprompt2: ...<as input by the user. If just enter is pressed it will be 'defaultvalue'>...
  #     secretfile: ...<content of the file as input by user. If just enter is pressed the file will be /tmp/ca.crt...0
  #     ca_crt: ...<content of /tmp/ca.crt>...
  #     ca_crt_b64: ...<content of /tmp/ca.crt base64-encoded before uploading to vault>...
  # - secret/snowflake.blueprints.rhecoeng.com:
  #     secret: ...<generated basicPolicy secret>...
  #     secretprompt: ...<as input by the user>...
  #     secretprompt2: ...<as input by the user. If just enter is pressed it will be 'defaultvalue'>...
  #     secretfile: ...<content of the file as input by user. If just enter is pressed the file will be /tmp/ca.crt...0
  #     ca_crt: ...<content of /tmp/ca.crt>...
  #     ca_crt_b64: ...<content of /tmp/ca.crt base64-encoded before uploading to vault>...
  - name: config-demo
    # This is the default and passes the -mount=secret option to the vault commands
    vaultMount: secret
    # These represent the paths inside the vault maint
    vaultPrefixes:
    - region-one
    - snowflake.blueprints.rhecoeng.com
    fields:
    - name: secret
      onMissingValue: generate # One of: error,generate,prompt (generate is only valid for normal secrets)
      # This override attribute is false by default. The attribute is only valid with 'generate'. If the secret already exists in the
      # vault it won't be changed unless override is set to true
      override: true
      vaultPolicy: basicPolicy
    - name: secretprompt
      value: null
      onMissingValue: prompt # when prompting for something you need to set either value: null or path: null as
                             # we need to know if it is a secret plaintext or a file path
      description: "Please specify the password for application ABC"
    - name: secretprompt2
      value: defaultvalue
      onMissingValue: prompt
      description: "Please specify the API key for XYZ"
    - name: secretprompt3
      onMissingValue: generate
      vaultPolicy: validatedPatternDefaultPolicy  # This is an always-existing hard-coded policy
    - name: secretfile
      path: /tmp/ca.crt
      onMissingValue: prompt
      description: "Insert path to Certificate Authority"
    - name: ca_crt
      path: /tmp/ca.crt
      onMissingValue: error # One of error, prompt (for path). generate makes no sense for file
    - name: ca_crt_b64
      path: /tmp/ca.crt
      base64: true # defaults to false
      onMissingValue: prompt # One of error, prompt (for path). generate makes no sense for file

  - name: config-demo2
    vaultPrefixes:
    - region-one
    - snowflake.blueprints.rhecoeng.com
    fields:
    - name: ca_crt2
      path: /tmp/ca.crt # this will be the default shown when prompted
      description: "Specify the path for ca_crt2"
      onMissingValue: prompt # One of error, prompt (for path). generate makes no sense for file
    - name: ca_crt
      path: /tmp/ca.crt
      onMissingValue: error # One of error, prompt (for path). generate makes no sense for file

  # The following will read the ini-file at ~/.aws/credentials and place the ini_key "[default]/aws_access_key_id"
  # in the aws_access_key_id_test vault attribute in the secret/hub/awsexample path
  - name: awsexample
    fields:
    - name: aws_access_key_id_test
      ini_file: ~/.aws/credentials
      ini_section: default
      ini_key: aws_access_key_id
    - name: aws_secret_access_key_test
      ini_file: ~/.aws/credentials
      ini_key: aws_secret_access_key
```

Internals
---------

Here is the rough high-level algorithm used to unseal the vault:

1. Check vault status. If vault is not initialized go to 2. If initialized go to 3.
2. Initialize vault and store unseal keys + login token inside a secret in k8s
3. Check vault status. If vault is unsealed go to 5. else to to 4.
4. Unseal the vault using the secrets read from the k8s secret
5. Configure the vault (should be idempotent)

## License

Apache

## Author Information

Michele Baldessari <michele@redhat.com>
