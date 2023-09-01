# ACM Backup Helm Chart

## Prerequisites

- Kubernetes 1.7+
- ACM 2.6+
- S3 bucket with appropriate IAM policy
- ClusterSecretStore for External Secrets Operator to reference S3 credentials

## Install the helm chart

```console
$ helm install acm-backup ./ -f values.yaml
```

## Upgrading the Chart

```console
$ helm upgrade acm-backup ./ -f values.yaml
```

## Configuration

Replace values in [values.yaml](values.yaml) as required.

The following table lists the configurable parameters of the cert-manager chart and their default values.

| Parameter | Description | Default |
| --------- | ----------- | ------- |
| `s3.profile` | S3 profile | `default` |
| `s3.region` | S3 region | `ap-southeast-2` |
| `s3.bucket` | S3 Bucket name | `acm-backup` |
| `oadp.key` | S3 Access Key & Secret location within your secretStore | `secret/data/hub/oadp` |
| `secretStore.name` | Name of the cluster secretStore | `vault-backend` |
| `secretStore.kind` | Kind of secretStore to be passed to ExternalSecret  | `ClusterSecretStore` |

## Defining and loading secrets

### Defining S3 credentials

Create a file with the S3 credentials like below (replace the dummy values):

```
[default]
aws_access_key_id=89c6HKohg5kVTTPtg7p5
aws_secret_access_key=G8N4AWX7KiAU6Lu3icqqQ77sBLtBM9RE
```

Then add the following to your `values-secret-multicloud-gitops.yaml` file:

```
 - name: oadp
    fields:
    - name: cloud
      path: /path/to/mysecret/s3.txt
```
### Loading secrets

Run `./common/scripts/pattern-util.sh make load-secrets` from the root of the `multicloud-gitops` repo  

Secrets will be loaded into Hashicorp Vault to be referenced by External Secrets within the Chart

For more information, see [Deploying HashiCorp Vault in a validated pattern](https://hybrid-cloud-patterns.io/learn/vault/)


## Installing disconnected

For a disconnected install, you must edit the MultiClusterHub object and add an annotation to override the source from which the OADP operator is installed.

E.g.

```
apiVersion: operator.open-cluster-management.io/v1
kind: MultiClusterHub
metadata:
  annotations:
    installer.open-cluster-management.io/oadp-subscription-spec: '{"source": "redhat-operator-index"}'
```

See [the docs](https://access.redhat.com/documentation/en-us/red_hat_advanced_cluster_management_for_kubernetes/2.7/html/backup_and_restore/backup-intro#prerequisites-backup-restore) for a full example

## Initiaing a restore

To start a restore you need to create a restore object within the cluster

E.g.

```
apiVersion: cluster.open-cluster-management.io/v1beta1
kind: Restore
metadata:
  name: restore-acm
  namespace: open-cluster-management-backup
spec:
  veleroManagedClustersBackupName: latest
  veleroCredentialsBackupName: latest
  veleroResourcesBackupName: latest
```

See this [link](https://access.redhat.com/documentation/en-us/red_hat_advanced_cluster_management_for_kubernetes/2.5/html/clusters/managing-your-clusters#restore-backup) for a full restore example


## Uninstalling the Chart

To uninstall/delete the `my-release` deployment:

```console
$ helm delete my-release
```

## Troubleshooting

We can use the `helm template` functionality to render values and troubleshoot problems with the Chart. 

From the directory containing [Chart.yaml](Chart.yaml), run:

```console
$ helm template ./ --name-template=acm-backup --dry-run --debug
```

The resulting objects will be rendered to stdout along with errors for troubleshooting.

## Reference
[How to Setup External Secrets Operator (ESO) as a Service](https://cloud.redhat.com/blog/how-to-setup-external-secrets-operator-eso-as-a-service)  
[Using Helm with Red Hat OpenShift](https://www.redhat.com/en/technologies/cloud-computing/openshift/helm)
