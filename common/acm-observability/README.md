# ACM Observability Helm Chart

## Prerequisites

- Kubernetes 1.7+
- ACM 2.6+
- S3 bucket with appropriate IAM policy
- Default storageClass configured to store metrics
- ClusterSecretStore for External Secrets Operator to reference S3 credentials

## Install the helm chart

```console
$ helm install acm-observability ./ -f values.yaml
```

## Upgrading the Chart

```console
$ helm upgrade acm-observability ./ -f values.yaml
```

## Configuration

Replace values in [values.yaml](values.yaml) as required.

The following table lists the configurable parameters of the cert-manager chart and their default values.

| Parameter | Description | Default |
| --------- | ----------- | ------- |
| `observabilityStorage.path` | Location of S3 bucket secret within secretStore | `hub/observabilityStorage` |
| `pullSecret.key` | Location of pull-secret within secretStore | `secret/data/hub/openshiftPullSecret` |
| `storageClass.name` | Name of storageClass for PV | `ClusterSecretStore` |
| `secretStore.name` | Name of the cluster secretStore | `vault-backend` |
| `secretStore.kind` | Kind of secretStore to be passed to ExternalSecret  | `ClusterSecretStore` |

## Defining and loading secrets

### Defining pull-secret

If you deployed the cluster with the [multicloud-gitops pattern](https://hybrid-cloud-patterns.io/patterns/multicloud-gitops/) the pullSecret will already exist. Otherwise you will need to load one to the secretStore as per below.

Create a file that holds the pull-secret (this can either be [downloaded](https://access.redhat.com/solutions/4844461) from Red Hat, or extracted from the cluster)

To extract the pull-secret:

```console
$ oc get secret pull-secret -n openshift-config --template='{{index .data ".dockerconfigjson" | base64decode}}' > pull-secret.txt
```

Then add the following to your `values-secret-multicloud-gitops.yaml` file

```
- name: openshiftPullSecret
    fields:
    - name: content
      path: ~/path/to/pull-secret.txt
```

### Defining S3 credentials

Create an .ini file like below:

```
[default]
access_key: UiKXW2T4op3NZbtRM9y8
secret_key: YLedsd3NW3WDThdz8TGMmHQ4g9yNnL6d
bucket: observability-bucket
endpoint: myOnPremiseS3Provider:9000
insecure: false
```

Then add the following to your `values-secret-multicloud-gitops.yaml` file:

```
- name: observabilityStorage
    fields:
    - name: access_key
      ini_file: ~/path/to/s3-thanos.ini
      ini_section: default
      ini_key: access_key
    - name: secret_key
      ini_file: ~/path/to/s3-thanos.ini
      ini_section: default
      ini_key: secret_key
    - name: bucket
      ini_file: ~/path/to/s3-thanos.ini
      ini_section: default
      ini_key: bucket
    - name: endpoint
      ini_file: ~/path/to/s3-thanos.ini
      ini_section: default
      ini_key: endpoint
    - name: insecure
      ini_file: ~/path/to/s3-thanos.ini
      ini_section: default
      ini_key: insecure
```
### Loading secrets

Run `./common/scripts/pattern-util.sh make load-secrets` from the root of the `multicloud-gitops` repo  

Secrets will be loaded into Hashicorp Vault to be referenced by External Secrets within the Chart

For more information, see [Deploying HashiCorp Vault in a validated pattern](https://hybrid-cloud-patterns.io/learn/vault/)


## Uninstalling the Chart

To uninstall/delete the `my-release` deployment:

```console
$ helm delete my-release
```

## Troubleshooting

We can use the `helm template` functionality to render values and troubleshoot problems with the Chart. 

From the directory containing [Chart.yaml](Chart.yaml), run:

```console
$ helm template ./ --name-template=acm-observability --dry-run --debug
```

The resulting objects will be rendered to stdout along with errors for troubleshooting.

## References
[Enabling the backup and restore operator](https://access.redhat.com/documentation/en-us/red_hat_advanced_cluster_management_for_kubernetes/2.7/html/backup_and_restore/backup-intro#enabling-backup-restore)  
[Installing and configuring the OpenShift API for Data Protection with Multicloud Object Gateway](https://docs.openshift.com/container-platform/4.9/backup_and_restore/application_backup_and_restore/installing/installing-oadp-mcg.html)