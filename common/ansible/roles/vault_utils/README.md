Role Name
=========

Bunch of utilities to manage the vault inside k8s imperatively

Requirements
------------

ansible-galaxy collection install kubernetes.core (formerly known as community.kubernetes)

Role Variables
--------------

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
```

Use the local file system (output_file variable) to store the vault's unseal keys.
If set to false they will be stored inside a secret defined by `unseal_secret`
in the `unseal_namespace` namespace:

```yaml
file_unseal: true
# token inside a secret in the cluster.
# *Note* that this is fundamentally unsafe
output_file: "common/pattern-vault.init"
unseal_secret: "vaultkeys"
unseal_namespace: "imperative"
```

Dependencies
------------

This relies on [kubernetes.core](https://docs.ansible.com/ansible/latest/collections/kubernetes/core/k8s_module.html)

Internals
---------

Here is the rough high-level algorithm used to unseal the vault:

1. Check vault status. If vault is not initialized go to 2. If initialized go to 3.
2. Initialize vault and store unseal keys + login token either on a local file
   or inside a secret in k8s (file_unseal var controls this)
3. Check vault status. If vault is unsealed go to 5. else to to 4.
4. Unseal the vault using the secrets read from the file or the secret
   (file_unseal controls this)
5. Configure the vault (should be idempotent)

License
-------

Apache

Author Information
------------------

Michele Baldessari <michele@redhat.com>
