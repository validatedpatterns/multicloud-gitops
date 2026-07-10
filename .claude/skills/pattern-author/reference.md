# What are Validated Patterns

[Validated Patterns](https://validatedpatterns.io/) are an advanced form of reference architectures that offer a streamlined approach to deploying complex business solutions.

Validated Patterns are GitOps-based. A Validated Pattern is a git repo containing the values files for the [clustergroup helm chart](https://github.com/validatedpatterns/clustergroup-chart/).

Validated Patterns are installed via the [Validated Patterns Operator](https://github.com/validatedpatterns/patterns-operator) (available as a community operator in OpenShift's operator catalog). The operator creates and manages a subscription for OpenShift GitOps (ArgoCD) and creates the app-of-apps Application in ArgoCD — the clustergroup chart with values taken from the Pattern repo (as a multi-source ArgoCD Application).

# Creating a New Pattern

1. Create an empty directory (or create a new repo on GitHub/GitLab and clone it). The directory name becomes the Pattern name.
2. Run `podman run --pull=newer -v "$PWD:$PWD:z" -w "$PWD" quay.io/validatedpatterns/patternizer init` to create the new Pattern. Add `--with-secrets` to include the necessary components for the Validated Patterns secret framework:
   `podman run --pull=newer -v "$PWD:$PWD:z" -w "$PWD" quay.io/validatedpatterns/patternizer init --with-secrets`

[The patternizer source is available on GitHub.](https://github.com/validatedpatterns/patternizer)

You can shorten the patternizer command by adding a shell function to your shell's startup:

```bash
pattern() {
  podman run --pull=newer \
    -v "$PWD:$PWD:z" \
    -w "$PWD" \
    quay.io/validatedpatterns/patternizer "$@"
}
```

Then run `pattern init` or `pattern init --with-secrets`.

`pattern init` is idempotent. You can add secrets to a Pattern initialized without them by running `pattern init --with-secrets` later. You can also re-run `pattern init` as you add helm charts to the repo and it will wire them into the clustergroup values file.

# Pattern File Structure

Given a fresh Pattern directory with a user-defined helm chart:

```bash
mkdir -p fresh-pattern/charts
cd fresh-pattern/charts
helm create user-defined-chart
cd ..
pattern init --with-secrets
```

The resulting structure:

```
fresh-pattern
├── ansible.cfg
├── charts
│   └── user-defined-chart
├── Makefile
├── Makefile-common
├── pattern.sh
├── values-global.yaml
├── values-prod.yaml
└── values-secret.yaml.template
```

## File Descriptions

`ansible.cfg` contains defaults for the ansible playbooks invoked via the Makefile (e.g., `make install`). These playbooks are defined in the [rhvp.cluster_utils collection](https://github.com/validatedpatterns/rhvp.cluster_utils).

`charts/` is the recommended location for local helm charts. `pattern init` discovers charts anywhere in the repo, but `charts/` is the convention.

`Makefile` includes `Makefile-common` and provides a place for Pattern-specific make targets or overrides. Most Patterns never need to override the common targets, but it's useful for custom tests, linting, or convenience functions.

`Makefile-common` provides the core make targets for the Patterns framework. Documented more fully on the [VP blog](https://validatedpatterns.io/blog/2025-08-29-new-common-makefile-structure/). The primary targets are `make install`, `make uninstall`, and `make load-secrets`. These targets are run via the `./pattern.sh` wrapper script, which executes them inside the [VP Utility Container](https://github.com/validatedpatterns/utility-container). The utility container includes make, oc, helm, aws, and other CLIs, so the only local dependency is podman. A user can run `./pattern.sh make install` to install a Pattern (assuming they are logged into an OpenShift cluster).

`pattern.sh` is the wrapper script that runs make targets inside the utility container.

`values-secret.yaml.template` is a template showing how the Pattern's secrets should be formatted for the [secrets framework](#the-secrets-framework). This file should never contain real secrets. Copy it to your home directory (`cp values-secret.yaml.template ~/values-secret-fresh-pattern.yaml`) so secrets stay on your local machine, not in your git repo.

## values-global.yaml

```yaml
global:
  pattern: fresh-pattern
  singleArgoCD: true
  secretLoader:
    disabled: false
main:
  clusterGroupName: prod
  multiSourceConfig:
    enabled: true
    clusterGroupChartVersion: 0.9.*
```

### Field Reference

`global.pattern` — The Pattern name, taken from the directory name by patternizer. Used as a label on ArgoCD Applications and as part of the ArgoCD namespace name.

`global.singleArgoCD` — When `true` (the patternizer default), each cluster uses a single ArgoCD instance for both the app-of-apps and all child applications. When `false` (legacy behavior), each cluster runs two ArgoCD instances: one for the clustergroup chart (app-of-apps) and a separate one for the applications it defines. A hub/spoke Pattern with `singleArgoCD: false` would have two ArgoCD instances on the hub and two on the spoke. With `singleArgoCD: true`, there is one ArgoCD instance on the hub and one on the spoke. New Patterns should always use `true`.

`global.secretLoader.disabled` — When `true`, skip loading secrets. Useful for Patterns that don't use the secrets framework.

`main.clusterGroupName` — The name of the primary clustergroup. Determines which `values-<name>.yaml` file defines the main cluster. If you change this value, the next `pattern init` run creates the corresponding values file (you would need to manually delete the old unused one).

`main.multiSourceConfig.enabled` — Enable ArgoCD multi-source applications. Should always be `true` for modern Patterns.

`main.multiSourceConfig.clusterGroupChartVersion` — Semver constraint for the clustergroup chart version from the VP chart repository.

There are also some global options that can be set in `values-global.yaml` but are not included by default:

`global.options.syncPolicy` — Controls the ArgoCD sync policy for all applications. `"Automatic"` (the default) enables auto-sync with retry. `"Manual"` disables auto-sync. Per-application `syncPolicy` overrides this global default.

`global.options.installPlanApproval` — Default `installPlanApproval` for all subscriptions. `"Automatic"` (the default) allows operators to auto-upgrade when new updates are available in their channel. Set to `"Manual"` to prevent auto-upgrades. Per-subscription values override this.

`global.options.useCSV` — When `True` (the default), subscriptions include a `startingCSV` field if their `.csv` value is set.

## values-prod.yaml

`values-prod.yaml` is the values file that defines the main clustergroup of the Pattern. In hub/spoke Patterns (see [Spoke clusters](#spoke-clusters)) this would be the hub cluster. In single cluster Patterns this defines the solitary cluster. If there is one file to look at which defines the Pattern, it is this one. Its contents are explored in [The clustergroup values](#the-clustergroup-values) section.

## The Pattern CR

When you run `./pattern.sh make install` to deploy the Pattern, the values in `values-global.yaml` are passed to the [pattern-install chart](https://github.com/validatedpatterns/pattern-install-chart) by the [rhvp.cluster_utils.install](https://github.com/validatedpatterns/rhvp.cluster_utils/blob/main/playbooks/install.yml) playbook. This chart creates a subscription for the Validated Patterns Operator, a configmap with default operator configuration, and the Pattern CR:

```yaml
apiVersion: gitops.hybrid-cloud-patterns.io/v1alpha1
kind: Pattern
metadata:
  name: fresh-pattern
  namespace: openshift-operators
spec:
  clusterGroupName: prod
  gitSpec:
    targetRepo: https://github.com/validatedpatterns/fresh-pattern.git
    targetRevision: main
  multiSourceConfig:
    enabled: true
    clusterGroupChartVersion: 0.9.*
```

Your branch (`main` in this example) must have an upstream remote set and be pushed to that remote.

# Values File Hierarchy

When the Patterns Operator creates the app-of-apps representing the Pattern, it renders the [clustergroup chart](https://github.com/validatedpatterns/clustergroup-chart/) and automatically includes certain values files (if they exist) to customize resources for a given clustergroup, OCP version, and platform.

The following values files are automatically included for each application, in this order:

1. `values-global.yaml` — included for all clustergroups
2. `values-<clusterGroupName>.yaml` — values specific to the clustergroup
3. `values-<clusterPlatform>.yaml` — values specific to the platform (e.g., `values-AWS.yaml`)
4. `values-<clusterPlatform>-<clusterVersion>.yaml` — platform and version specific (e.g., `values-AWS-4.21.yaml`)
5. `values-<clusterPlatform>-<clusterGroupName>.yaml` — platform and clustergroup specific (e.g., `values-AWS-hub.yaml`)
6. `values-<clusterVersion>-<clusterGroupName>.yaml` — version and clustergroup specific (e.g., `values-4.21-hub.yaml`)
7. `values-<localClusterName>.yaml` — values for a specifically named cluster (e.g., `values-test-cluster.yaml`)
8. Files from `global.extraValueFiles` — additional global value files
9. Per-clustergroup `sharedValueFiles` — from `clusterGroup.sharedValueFiles`
10. Per-application `extraValueFiles` — from the application's `extraValueFiles` field

ArgoCD is configured with `ignoreMissingValueFiles: true`, so it silently skips any of these files that do not exist. Only create the files you actually need.

In multi-source mode (the default), values files from the Pattern repo are prefixed with `$patternref/` to tell ArgoCD which source they come from. This is handled automatically by the clustergroup chart.

Some of these values files are cross-clustergroup. For example, `values-AWS.yaml` would apply to both hub and spoke clustergroups running on AWS.

## Shared Value Files

The clustergroup provides a `sharedValueFiles` field for including additional overrides for all applications in that clustergroup:

```yaml
clusterGroup:
  sharedValueFiles:
    - '/overrides/values-{{ $.Values.global.clusterPlatform }}.yaml'
    - '/overrides/values-{{ $.Values.global.clusterPlatform }}-{{ $.Values.global.clusterVersion }}.yaml'
    - '/overrides/values-{{ $.Values.global.clusterPlatform }}-{{ $.Values.clusterGroup.name }}.yaml'
    - '/overrides/values-{{ $.Values.global.clusterVersion }}-{{ $.Values.clusterGroup.name }}.yaml'
    - '/overrides/values-{{ $.Values.global.localClusterName }}.yaml'
```

These paths support Helm template interpolation. The Validated Patterns operator handles resolving the global variables. As with the auto-included files, any that do not exist are silently skipped.

By convention, extra value files are placed in an `overrides/` directory in the Pattern repo, but any location works.

## Custom Globals for Conditional Overrides

You can define your own global variables in `values-global.yaml` and use them in `sharedValueFiles` to enable conditional configuration. Consider this example:

```yaml
# values-global.yaml
global:
  pattern: ai-quickstart-rag
  device: cpu # one of 'cpu' (no GPU) or 'gpu' (NVIDIA GPU)
main:
  clusterGroupName: prod
  multiSourceConfig:
    enabled: true
    clusterGroupChartVersion: 0.9.*
```

This enables conditional value file inclusion:

```yaml
clusterGroup:
  sharedValueFiles:
    - /overrides/values-{{ $.Values.global.device }}.yaml
    - /overrides/values-{{ $.Values.global.device }}-{{ $.Values.global.clusterPlatform }}.yaml
```

```yaml
# /overrides/values-gpu.yaml
global:
  models:
    llama-3-2-3b-instruct:
      enabled: true

llm-service:
  device: gpu

clusterGroup:
  namespaces:
    openshift-nfd:
    nvidia-gpu-operator:

  subscriptions:
    nfd:
      name: nfd
      namespace: openshift-nfd
    nvidia:
      name: gpu-operator-certified
      namespace: nvidia-gpu-operator
      source: certified-operators

  applications:
    nfd:
      name: nfd
      namespace: openshift-nfd
      path: charts/nfd
    nvidia-config:
      name: nvidia-config
      namespace: nvidia-gpu-operator
      path: charts/nvidia-config
```

```yaml
# /overrides/values-gpu-AWS.yaml
clusterGroup:
  imperative:
    jobs:
      - name: deploy-nvidia-gpu
        playbook: rhvp.cluster_utils.create_machineset
        verbosity: -vvv
        extravars:
          - max_machineset_count=1
          - machineset_replicas=1
          - ensure_two_machine_minimum=false
          - machineset_name=nvidia-gpu
          - machineset_labels=
          - machineset_instance_type=g6.2xlarge
          - 'machineset_taints=[{"effect":"NoSchedule","key":"nvidia.com/gpu","value":"true"}]'
          - 'machineset_node_labels={"node-role.kubernetes.io/nvidia-gpu":""}'
          - machineset_api_version=machine.openshift.io/v1beta1
    clusterRoleYaml:
      - apiGroups:
          - "*"
        resources:
          - machinesets
          - persistentvolumeclaims
          - datavolumes
          - dataimportcrons
          - datasources
        verbs:
          - "*"
      - apiGroups:
          - "*"
        resources:
          - "*"
        verbs:
          - get
          - list
          - watch
```

This example leverages the `global.device` value to install GPU-specific subscriptions and create an additional machineset when deployed to AWS with a GPU.

# The Clustergroup Values

A Pattern IS a clustergroup. The git repo containing a Validated Pattern contains the values files for the [clustergroup helm chart](https://github.com/validatedpatterns/clustergroup-chart/). The clustergroup values file (`values-<clusterGroupName>.yaml`) is the central definition of what a Pattern deploys — which namespaces to create, which operators to install, and which applications (helm charts) to run.

Here is the `values-prod.yaml` generated by `pattern init --with-secrets` for our example Pattern. It defines a single clustergroup named `prod` with the namespaces, operator subscriptions, and applications needed for the secrets framework alongside the user's own chart:

```yaml
clusterGroup:
  name: prod
  namespaces:
    fresh-pattern:
    vault:
    external-secrets-operator:
      operatorGroup: true
      targetNamespaces: []
    external-secrets:
  subscriptions:
    eso:
      name: openshift-external-secrets-operator
      namespace: external-secrets-operator
      channel: stable-v1
  applications:
    openshift-external-secrets:
      name: openshift-external-secrets
      namespace: external-secrets
      chart: openshift-external-secrets
      chartVersion: 0.0.*
    user-defined-chart:
      name: user-defined-chart
      namespace: fresh-pattern
      path: charts/user-defined-chart
    vault:
      name: vault
      namespace: vault
      chart: hashicorp-vault
      chartVersion: 0.1.*
```

These three sections — `namespaces`, `subscriptions`, and `applications` — are the core building blocks of every clustergroup. Each is detailed below.

## Namespaces

The namespace section accepts simple strings or more complex mappings:

```yaml
clusterGroup:
  namespaces:
    fresh-pattern:
    external-secrets-operator:
      operatorGroup: true
      targetNamespaces: []
```

Setting `operatorGroup: true` creates an OperatorGroup with the same name as the namespace using the specified `targetNamespaces`.

Labels and annotations can also be set:

```yaml
clusterGroup:
  namespaces:
    rag-llm:
      labels:
        opendatahub.io/dashboard: "true"
        modelmesh-enabled: "false"
```

Namespaces can also be defined as a list:

```yaml
clusterGroup:
  namespaces:
    - fresh-pattern
    - vault
    - external-secrets-operator:
        operatorGroup: true
        targetNamespaces: []
    - external-secrets
```

The map form is recommended over the list form. When merging values files, lists are overridden entirely whereas maps are merged.

## Subscriptions

Subscriptions define operators that should be installed on the cluster.

The only required field is the name of the subscription:

```yaml
clusterGroup:
  subscriptions:
    servicemesh-console:
      name: kiali-ossm
```

The clustergroup chart provides defaults for the other fields, making this equivalent to:

```yaml
clusterGroup:
  subscriptions:
    servicemesh-console:
      name: kiali-ossm
      namespace: openshift-operators
      source: redhat-operators
      sourceNamespace: openshift-marketplace
      channel: stable
      installPlanApproval: Automatic
```

You can also specify `.csv` for the `startingCSV` of the subscription if needed.

The `name` must be the operator's name in the `source` catalog. The default source is `redhat-operators`, but some operators are in `certified-operators`, `community-operators`, or `redhat-marketplace`.

`namespace` is where the operator is installed. For operators like ESO, this is an OperatorGroup namespace.

`source` and `sourceNamespace` only need updating in disconnected or custom install scenarios where the standard catalog sources are unavailable.

`channel` is operator-specific. Some operators publish on multiple channels (e.g., `fast`, `stable-3.x`).

Set `installPlanApproval` to `Manual` to prevent the operator from upgrading automatically when new updates are available in its channel. The default is `Automatic`.

## Applications

### Local Helm Charts

If `path` is provided (and `repoURL` and `chartVersion` are not), the helm chart is sourced from the Pattern repo:

```yaml
clusterGroup:
  applications:
    user-defined-chart:
      name: user-defined-chart
      namespace: fresh-pattern
      path: charts/user-defined-chart
```

### VP-Published Helm Charts

If neither `repoURL` nor `path` are provided, charts are sourced from the [Validated Patterns chart repository](https://charts.validatedpatterns.io/). Specify a version with `chartVersion`:

```yaml
clusterGroup:
  applications:
    vault:
      name: vault
      namespace: vault
      chart: hashicorp-vault
      chartVersion: 0.1.*
```

### Helm Charts from External Git Repositories

Helm charts from external git repos can be referenced with `repoURL` (the publicly reachable git URL), `path` (the path within the repo), and `chartVersion` (the git revision to use):

```yaml
clusterGroup:
  applications:
    maas-quickstart:
      name: maas-quickstart
      repoURL: https://github.com/dminnear-rh/maas-code-assistant.git
      chartVersion: main
      path: charts/maas-code-assistant
```

### Additional Application Fields

Several additional fields are available for any application type:

`extraValueFiles` — Paths (relative to the Pattern repo root) to additional values files passed to the helm chart:

```yaml
extraValueFiles:
  - /overrides/maas-quickstart.yaml
```

`overrides` — Direct helm value overrides:

```yaml
overrides:
  - name: grafana.namespace
    value: grafana
```

`ignoreDifferences` — Instructs ArgoCD to ignore certain differences when computing the sync diff:

```yaml
ignoreDifferences:
  - kind: Secret
    name: grafana-proxy
    namespace: grafana
    jsonPointers:
      - /data/session_secret
```

A full example combining these:

```yaml
clusterGroup:
  applications:
    maas-quickstart:
      name: maas-quickstart
      repoURL: https://github.com/dminnear-rh/maas-code-assistant.git
      chartVersion: main
      path: charts/maas-code-assistant
      extraValueFiles:
        - /overrides/maas-quickstart.yaml
      overrides:
        - name: grafana.namespace
          value: grafana
      ignoreDifferences:
        - kind: Secret
          name: grafana-proxy
          namespace: grafana
          jsonPointers:
            - /data/session_secret
```

# Using Helm Charts in VP

This section covers what the VP framework provides to your charts, not helm chart authoring in general.

## Where Charts Live

The default location is `charts/` in the Pattern repo. `patternizer init` auto-discovers charts anywhere in the repo, so you can organize them however you like.

Charts can also live in separate git repositories and be referenced via `repoURL` in the application definition. VP-published charts are available from [charts.validatedpatterns.io](https://charts.validatedpatterns.io/) (referenced with `chart:` and `chartVersion:`).

## How Values Flow into Charts

Every ArgoCD Application created by the clustergroup chart receives the full merged tree of values files described in [Values File Hierarchy](#values-file-hierarchy). This means every chart sees:

- `.Values.global.*` — global Pattern values
- `.Values.clusterGroup.*` — clustergroup configuration
- Chart-specific values from the chart's own `values.yaml`

In addition to the values files, the clustergroup chart injects helm parameters for cluster-specific values that are known at deploy time:

- `global.repoURL` — Pattern repository URL
- `global.targetRevision` — git branch/commit/ref
- `global.namespace` — the ArgoCD app namespace
- `global.pattern` — Pattern name
- `global.clusterDomain` — cluster FQDN
- `global.localClusterName` — local cluster identifier
- `global.clusterVersion` — OpenShift version
- `global.clusterPlatform` — platform type (e.g., AWS, Azure, GCP)
- `global.hubClusterDomain` — hub cluster FQDN
- `global.localClusterDomain` — local cluster FQDN

These are available in templates as `.Values.global.<fieldName>`.

A chart's `values.yaml` should include default stubs for any `global.*` or `clusterGroup.*` values referenced in its templates. These defaults enable standalone `helm template` to work during development and are overridden at deploy time by the merged values tree.

## Example: config-demo Chart

The [config-demo chart](https://github.com/validatedpatterns/multicloud-gitops/tree/main/charts/all/config-demo) from multicloud-gitops is a minimal working example. Its `values.yaml`:

```yaml
secretStore:
  name: vault-backend
  kind: ClusterSecretStore

configdemosecret:
  key: secret/data/global/config-demo
  refreshInterval: 2m0s

global:
  hubClusterDomain: hub.example.com
  localClusterDomain: region-one.example.com

clusterGroup:
  isHubCluster: true

image:
  repository: registry.access.redhat.com/ubi10/httpd-24
  tag: "10.0-1755779646"
  pullPolicy: IfNotPresent
```

The `global` and `clusterGroup` stubs provide defaults for development. The `secretStore` and `configdemosecret` sections are chart-specific values used by the ExternalSecret template (see [Consuming Secrets in Charts](#consuming-secrets-in-charts)).

The deployment template uses chart-specific values:

```yaml
containers:
- name: apache
  image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
  imagePullPolicy: {{ .Values.image.pullPolicy }}
```

The ConfigMap template uses global values injected by the framework, demonstrating how charts can reference cluster-specific information without hardcoding it:

```yaml
data:
  "index.html": |-
    <h1>
    Hub Cluster domain is '{{ .Values.global.hubClusterDomain }}' <br>
    Pod is running on Local Cluster Domain '{{ .Values.global.localClusterDomain }}' <br>
    </h1>
```

# The Secrets Framework

Secrets in the VP framework are stored in Vault and consumed in charts via External Secrets Operator (ESO). The workflow is: define secrets in `values-secret.yaml.template`, load them into Vault with `./pattern.sh make install` or `./pattern.sh make load-secrets`, and consume them in charts using ExternalSecret CRDs.

## Defining Secrets

The `values-secret.yaml.template` file defines the secrets a Pattern needs. The install/load-secrets command looks for secrets in `~/values-secret-<pattern-name>.yaml` and falls back to the template in the Pattern repo. This encourages users to copy the template to their home directory and keep secrets out of the git repo.

Example from [multicloud-gitops](https://github.com/validatedpatterns/multicloud-gitops/blob/main/values-secret.yaml.template):

```yaml
version: "2.0"

secrets:
  - name: config-demo
    vaultPrefixes:
    - global
    fields:
    - name: secret
      onMissingValue: generate
      vaultPolicy: validatedPatternDefaultPolicy
```

### Secret Field Reference

Each secret entry supports these fields:

- `name` — secret name (becomes the Vault path segment)
- `vaultPrefixes` — list of Vault path prefixes controlling which clustergroups can read the secret
- `fields[].name` — field name within the secret
- `fields[].value` — literal value
- `fields[].path` — path to a file containing the value
- `fields[].ini_file`, `ini_section`, `ini_key` — read a value from an INI file
- `fields[].onMissingValue` — set to `generate` to auto-generate the value
- `fields[].vaultPolicy` — policy name for generation (either `validatedPatternDefaultPolicy` or a custom policy)

Example with various field types:

```yaml
secrets:
  # AWS credentials from INI file
  - name: aws
    fields:
    - name: aws_access_key_id
      ini_file: ~/.aws/credentials
      ini_section: default
      ini_key: aws_access_key_id
    - name: aws_secret_access_key
      ini_file: ~/.aws/credentials
      ini_key: aws_secret_access_key

  # SSH keys from files
  - name: publickey
    fields:
    - name: content
      path: ~/.ssh/id_rsa.pub
  - name: privatekey
    fields:
    - name: content
      path: ~/.ssh/id_rsa

  # OpenShift pull secret from file
  - name: openshiftPullSecret
    fields:
    - name: content
      path: ~/.pullsecret.json
```

## Vault Prefixes and Access Control

The `vaultPrefixes` field controls which clustergroups can access a secret. The Vault path convention is `secret/data/<prefix>/<secret-name>`.

- `global` — readable by all clustergroups (hub and spoke)
- A clustergroup name (e.g., `hub`) — readable only by that clustergroup
- Multiple prefixes write the secret to multiple paths, making it accessible from multiple clustergroups

## Secret Generation and Policies

Secrets can be auto-generated if no value is provided by setting `onMissingValue: generate`. The generation is controlled by a vault policy:

```yaml
version: "2.0"

vaultPolicies:
  basicPolicy: |
    length=16
    rule "charset" { charset = "abcdefghijklmnopqrstuvwxyz" min-chars = 1 }
    rule "charset" { charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" min-chars = 1 }
    rule "charset" { charset = "0123456789" min-chars = 1 }

secrets:
  - name: pgvector
    fields:
    - name: user
      value: postgres
    - name: password
      onMissingValue: generate
      vaultPolicy: basicPolicy
    - name: dbname
      value: rag_blueprint
    - name: host
      value: pgvector
    - name: port
      value: "5432"
```

## Consuming Secrets in Charts

Secrets stored in Vault are consumed in charts using ESO ExternalSecret CRDs. The VP `openshift-external-secrets` chart sets up a `ClusterSecretStore` named `vault-backend` that points to the Vault instance.

A chart that needs secrets should include `secretStore` defaults in its `values.yaml`:

```yaml
secretStore:
  name: vault-backend
  kind: ClusterSecretStore

configdemosecret:
  key: secret/data/global/config-demo
  refreshInterval: 2m0s
```

The ExternalSecret template maps secrets from Vault into Kubernetes Secrets:

```yaml
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: config-demo-secret
  namespace: config-demo
spec:
  refreshInterval: {{ .Values.configdemosecret.refreshInterval }}
  secretStoreRef:
    name: {{ .Values.secretStore.name }}
    kind: {{ .Values.secretStore.kind }}
  target:
    name: config-demo-secret
    template:
      type: Opaque
      data:
        secret: "{{ `{{ .configdemo_secret }}` }}"
  data:
    - secretKey: configdemo_secret
      remoteRef:
        key: {{ .Values.configdemosecret.key }}
        property: secret
```

### How the Mapping Works

Given a secret defined in `values-secret.yaml.template` as:

```yaml
secrets:
  - name: config-demo
    vaultPrefixes:
    - global
    fields:
    - name: secret
```

The Vault path is: `secret/data/global/config-demo` (constructed as `secret/data/<vaultPrefix>/<secret-name>`).

In the ExternalSecret:
- `remoteRef.key` is set to this Vault path (`secret/data/global/config-demo`)
- `remoteRef.property` is the field name (`secret`)
- `data[].secretKey` (`configdemo_secret`) is the local key used to reference the fetched value in the `target.template`

### Backtick Escaping for ESO Templates

The `target.template.data` section uses ESO's own template syntax (`{{ .fieldname }}`) to map fetched values into the Kubernetes Secret. Since the ExternalSecret is itself rendered by Helm, the ESO template expressions must be escaped to prevent Helm from interpreting them. The pattern is:

```
"{{ `{{ .configdemo_secret }}` }}"
```

The backticks create a Go raw string literal that Helm passes through unchanged. ESO then processes `{{ .configdemo_secret }}` at runtime.

## Hub vs. Spoke Secret Infrastructure

The Vault/ESO components should only be defined on the hub/main cluster:

```yaml
# Hub cluster needs both Vault and ESO
clusterGroup:
  namespaces:
    vault:
    external-secrets-operator:
      operatorGroup: true
      targetNamespaces: []
    external-secrets:
  subscriptions:
    eso:
      name: openshift-external-secrets-operator
      namespace: external-secrets-operator
      channel: stable-v1
  applications:
    openshift-external-secrets:
      name: openshift-external-secrets
      namespace: external-secrets
      chart: openshift-external-secrets
      chartVersion: 0.0.*
    vault:
      name: vault
      namespace: vault
      chart: hashicorp-vault
      chartVersion: 0.1.*
```

Spoke clusters only need ESO — no Vault:

```yaml
# Spoke cluster needs ESO only
clusterGroup:
  namespaces:
    external-secrets-operator:
      operatorGroup: true
      targetNamespaces: []
    external-secrets:
  subscriptions:
    eso:
      name: openshift-external-secrets-operator
      namespace: external-secrets-operator
      channel: stable-v1
  applications:
    openshift-external-secrets:
      name: openshift-external-secrets
      namespace: external-secrets
      chart: openshift-external-secrets
      chartVersion: 0.0.*
```

The VP `openshift-external-secrets` chart automatically configures spoke clusters to use the Vault instance on the hub cluster as the external secret store.

For more information, see [Secrets management in the Validated Patterns framework](https://validatedpatterns.io/learn/secrets-management-in-the-validated-patterns-framework/).

# Spoke Clusters

Hub/spoke cluster support uses ACM (Advanced Cluster Management). Include the ACM components in your hub clustergroup:

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
    exampleRegion:
      name: group-one
      acmlabels:
        - name: clusterGroup
          value: group-one
```

This installs ACM on the hub cluster via the Validated Patterns ACM chart. The `managedClusterGroups` defines the mapping the framework uses to determine which clusters imported into ACM correspond to which clustergroup values files.

To create a spoke clustergroup, create `values-group-one.yaml` with its own namespaces, subscriptions, and applications. For secrets, include the ESO components (without Vault) as described in [Hub vs. Spoke Secret Infrastructure](#hub-vs-spoke-secret-infrastructure).

```yaml
clusterGroup:
  name: group-one

  namespaces:
    config-demo:
    hello-world:
    external-secrets-operator:
      operatorGroup: true
      targetNamespaces: []
    external-secrets:

  subscriptions:
    eso:
      name: openshift-external-secrets-operator
      namespace: external-secrets-operator
      channel: stable-v1

  applications:
    openshift-external-secrets:
      name: openshift-external-secrets
      namespace: external-secrets
      chart: openshift-external-secrets
      chartVersion: 0.0.*
    config-demo:
      name: config-demo
      namespace: config-demo
      path: charts/all/config-demo
    hello-world:
      name: hello-world
      namespace: hello-world
      path: charts/all/hello-world
```

Any cluster imported into ACM with the label `clusterGroup: group-one` will have the clustergroup chart applied using `values-global.yaml` and `values-group-one.yaml` (plus all the other automatically included platform/version values files).

In short, spoke and hub clusters are both just clustergroups. The difference is that the hub cluster includes ACM and the Vault components. While the Patterns Operator installs the Pattern via the clustergroup chart in ArgoCD on the hub cluster, the ACM chart pushes policies to spoke clusters for installing OpenShift GitOps (ArgoCD) and the clustergroup chart for that spoke cluster.

# The Imperative Framework

Sometimes tasks don't fit neatly into a declarative framework. The imperative framework runs Ansible playbooks on a schedule against the cluster.

```yaml
clusterGroup:
  imperative:
    jobs:
      - name: trilio-enable-cr
        playbook: ansible/playbooks/imperative-enable-cr.yaml
        timeout: 900

      - name: trilio-cr-backup
        playbook: ansible/playbooks/imperative-cr-backup.yaml
        timeout: 1200

      - name: trilio-backup
        playbook: ansible/playbooks/imperative-backup.yaml
        timeout: 1200

      - name: trilio-restore-standard
        playbook: ansible/playbooks/imperative-restore-standard.yaml
        timeout: 1800

      - name: trilio-e2e-status
        playbook: ansible/playbooks/imperative-e2e-status.yaml
        timeout: 120
```

Imperative jobs typically reference playbooks stored in the `ansible/` directory of the Pattern repo, or playbooks from the `rhvp.cluster_utils` ansible collection. Jobs are defined as a list since they run in order — if one fails, the imperative job fails and remaining jobs are aborted. Jobs must be idempotent since they run on a schedule (every 10 minutes by default).

The full set of imperative framework defaults:

```yaml
imperative:
  jobs: []
  image: quay.io/validatedpatterns/imperative-container:v1
  ansibleDevMode:
    enabled: false
    requirementsFile: "requirements.yml"
    requirementsContent: ""
    ansibleCfgFile: "ansible.cfg"
    ansibleCfgContent: ""
  namespace: "imperative"
  valuesConfigMap: "helm-values-configmap"
  cronJobName: "imperative-cronjob"
  jobName: "imperative-job"
  imagePullPolicy: Always
  activeDeadlineSeconds: 3600
  schedule: "*/10 * * * *"
  insecureUnsealVaultInsideClusterSchedule: "*/5 * * * *"
  verbosity: ""
  extraPlaybookArgs: []
  serviceAccountCreate: true
  serviceAccountName: imperative-sa
  clusterRoleName: imperative-cluster-role
  clusterRoleYaml: ""
  roleName: imperative-role
  roleYaml: ""
  adminServiceAccountCreate: true
  adminServiceAccountName: imperative-admin-sa
  adminClusterRoleName: imperative-admin-cluster-role
  vaultNamespace: "vault"
```
