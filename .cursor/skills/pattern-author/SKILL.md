---
name: pattern-author
description: >
  Author and modify Validated Patterns — GitOps-based deployment configurations
  for OpenShift. Use when creating new Patterns, adding applications/subscriptions/namespaces
  to existing Patterns, configuring secrets, setting up hub/spoke clusters, or working with
  clustergroup values files.
when_to_use: >
  When the user asks to create a new Validated Pattern, add a helm chart or application to a
  Pattern, configure secrets or vault, set up spoke clusters, modify clustergroup values,
  or work with values-global.yaml, values-*.yaml, or values-secret.yaml.template files.
  Also when the user mentions "Validated Patterns", "clustergroup", "pattern init", or
  "patternizer".
allowed-tools: Read Bash(pattern *) Bash(helm *) Bash(find *) Bash(ls *)
---

# Validated Patterns Author

You are helping author Validated Patterns — GitOps-based deployment configurations for OpenShift built on the [clustergroup helm chart](https://github.com/validatedpatterns/clustergroup-chart/). A Pattern is a git repo containing values files that define what namespaces, operators, and applications to deploy on one or more OpenShift clusters via ArgoCD.

For complete framework documentation, read [reference.md](reference.md) in this skill directory. Read it before your first Pattern authoring task in a session, or when you need details on a specific framework feature.

## Authoring Workflow

When creating a new Pattern:

1. **Initialize** — Determine the Pattern name and whether secrets are needed. Run `pattern init` or `pattern init --with-secrets` in the Pattern directory.
2. **Identify requirements** — What operators, applications, and custom helm charts does this Pattern need?
3. **Define namespaces** — Add all required namespaces to the clustergroup values file (`values-<clusterGroupName>.yaml`). Include OperatorGroup configuration for operator namespaces.
4. **Define subscriptions** — Add operator subscriptions with at minimum the operator `name`. Set `namespace`, `channel`, and `source` as needed.
5. **Define applications** — Wire in helm charts as applications:
   - Local charts: set `path` to the chart location in the repo
   - VP-published charts: set `chart` and `chartVersion`
   - External git charts: set `repoURL`, `path`, and `chartVersion` (git ref)
6. **Configure secrets** (if applicable) — Define secrets in `values-secret.yaml.template` and create corresponding ExternalSecret CRDs in chart templates.
7. **Set up hub/spoke** (if multi-cluster) — Add ACM subscription and `managedClusterGroups` to the hub. Create spoke values files.
8. **Add imperative jobs** (if needed) — Configure Ansible playbooks in the imperative framework for tasks that don't fit the declarative model.

When modifying an existing Pattern, read the current `values-global.yaml` and clustergroup values files first to understand the existing structure before making changes.

## Rules

These rules must always be followed:

- **Map form for namespaces** — Always define namespaces as a map, never a list. Maps merge across values files; lists override entirely.
- **No secrets in git** — Never put real secrets or credentials in the Pattern repo. Secrets belong in `~/values-secret-<pattern-name>.yaml` on the user's machine.
- **`singleArgoCD: true`** — Always set this for new Patterns.
- **`multiSourceConfig.enabled: true`** — Always set this for new Patterns.
- **Vault only on hub** — The Vault application and namespace belong only on the hub/main cluster. Spoke clusters need ESO only (no Vault). The VP `openshift-external-secrets` chart auto-configures spokes to use the hub's Vault.
- **Chart values stubs** — A chart's `values.yaml` must include default stubs for any `.Values.global.*` or `.Values.clusterGroup.*` values referenced in its templates, so `helm template` works standalone during development.
- **ESO backtick escaping** — In ExternalSecret templates, escape ESO template expressions with backticks to prevent Helm from interpreting them: `"{{ ` + "`" + `{{ .field_name }}` + "`" + ` }}"`.
- **Idempotent imperative jobs** — All imperative jobs run on a schedule (every 10 minutes by default) and must be idempotent.
- **Re-run `pattern init`** — After adding new local helm charts, re-run `pattern init` to wire them into the clustergroup values file. It is idempotent.

## Common Tasks

### Adding an Operator

Add three things to the clustergroup values file: a namespace, a subscription, and (if the operator needs its own chart for configuration) an application.

```yaml
clusterGroup:
  namespaces:
    my-operator:
      operatorGroup: true
      targetNamespaces: []

  subscriptions:
    my-operator:
      name: my-operator
      namespace: my-operator
      channel: stable

  applications:
    my-operator-config:
      name: my-operator-config
      namespace: my-operator
      path: charts/my-operator-config
```

Not every operator needs a local chart. If the operator requires no additional configuration beyond installation, the namespace and subscription are sufficient.

### Adding a Local Helm Chart

Place the chart anywhere in the repo (convention: `charts/`). Run `pattern init` to auto-discover it, or manually add it to the clustergroup values:

```yaml
clusterGroup:
  namespaces:
    my-app:

  applications:
    my-app:
      name: my-app
      namespace: my-app
      path: charts/my-app
```

### Adding a VP-Published Chart

```yaml
clusterGroup:
  applications:
    vault:
      name: vault
      namespace: vault
      chart: hashicorp-vault
      chartVersion: 0.1.*
```

### Adding a Chart from an External Git Repo

```yaml
clusterGroup:
  applications:
    external-app:
      name: external-app
      namespace: external-app
      repoURL: https://github.com/org/repo.git
      chartVersion: main
      path: charts/the-chart
```

### Adding a Secret

1. Define the secret in `values-secret.yaml.template`:

```yaml
version: "2.0"

secrets:
  - name: my-secret
    vaultPrefixes:
    - global
    fields:
    - name: api-key
      onMissingValue: prompt
    - name: password
      onMissingValue: generate
      vaultPolicy: validatedPatternDefaultPolicy
```

2. Add `secretStore` defaults to the chart's `values.yaml`:

```yaml
secretStore:
  name: vault-backend
  kind: ClusterSecretStore

mysecret:
  key: secret/data/global/my-secret
  refreshInterval: 2m0s
```

3. Create an ExternalSecret template in the chart:

```yaml
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: my-secret
spec:
  refreshInterval: {{ .Values.mysecret.refreshInterval }}
  secretStoreRef:
    name: {{ .Values.secretStore.name }}
    kind: {{ .Values.secretStore.kind }}
  target:
    name: my-secret
    template:
      type: Opaque
      data:
        api-key: "{{ `{{ .api_key }}` }}"
        password: "{{ `{{ .password }}` }}"
  data:
    - secretKey: api_key
      remoteRef:
        key: {{ .Values.mysecret.key }}
        property: api-key
    - secretKey: password
      remoteRef:
        key: {{ .Values.mysecret.key }}
        property: password
```

The Vault path is `secret/data/<vaultPrefix>/<secret-name>`. The `secretKey` values become the template variables in `target.template.data`.

### Adding a Spoke Cluster

1. Add ACM and `managedClusterGroups` to the hub clustergroup values:

```yaml
clusterGroup:
  name: hub

  namespaces:
    open-cluster-management:

  subscriptions:
    acm:
      name: advanced-cluster-management
      namespace: open-cluster-management
      channel: release-2.16

  applications:
    acm:
      name: acm
      namespace: open-cluster-management
      chart: acm
      chartVersion: 0.2.*

  managedClusterGroups:
    region-one:
      name: group-one
      acmlabels:
        - name: clusterGroup
          value: group-one
```

2. Create `values-group-one.yaml` with the spoke's namespaces, subscriptions, and applications.

3. If using secrets on the spoke, include ESO components (without Vault) in the spoke values.

### Adding Conditional Overrides

Define a custom global variable and use `sharedValueFiles`:

```yaml
# values-global.yaml
global:
  device: gpu

# values-<clustergroup>.yaml
clusterGroup:
  sharedValueFiles:
    - /overrides/values-{{ $.Values.global.device }}.yaml
```

Create the override file (e.g., `/overrides/values-gpu.yaml`) with the conditional namespaces, subscriptions, and applications.
