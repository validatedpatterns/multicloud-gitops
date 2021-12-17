# Start Here

If you've followed a link to this repo, but are not really sure what it contains
or how to use it, head over to http://hybrid-cloud-patterns.io/multicloud-gitops/
for additional context before continuing.

# Prerequisites

1. An OpenShift cluster ( Go to https://console.redhat.com/openshift/create )
1. (Optional) A second OpenShift cluster
1. (Optional) A third OpenShift cluster
1. A github account
1. A quay account
1. The helm binary, see https://helm.sh/docs/intro/install/
1. (Optional) the argocd binary (for OpenShift Gitops), see https://argo-cd.readthedocs.io/en/stable/cli_installation/
1. (Optional) the tkn binary (for OpenShift Pipelines), see https://tekton.dev/docs/cli/

The use of this blueprint depends on having at least one running Red Hat
OpenShift cluster. It is desirable to have a cluster for deploying the data
center assets and a seperate cluster(s) for the factory assets.

If you do not have a running Red Hat OpenShift cluster you can start one on a
public or private cloud by using [Red Hat's cloud
service](https://console.redhat.com/openshift/create).

# How to deploy

1. Fork this repo on GitHub. It is necessary to fork because your fork will be updated as part of the GitOps and DevOps processes.

1. Clone the forked copy

   ```
   git clone git@github.com:your-username/multicloud-gitops.git
   ```

1. Create a local copy of the Helm values file that can safely include credentials

  DO NOT COMMIT THIS FILE

  You do not want to push personal credentials to GitHub.
   ```
   cp values-secret.yaml.template ~/values-secret.yaml
   vi ~/values-secret.yaml
   ```

1. Customize the deployment for your cluster

   ```
   vi values-global.yaml
   git commit values-global.yaml
   git push
   ```

1. Preview the changes
   ```
   make show
   ```

1. Login to your cluster using oc login or exporting the KUBECONFIG

   ```
   oc login
   ```

   or

   ```
   export KUBECONFIG=~/my-ocp-env/hub
   ```

1. Apply the changes to your cluster

   ```
   make install
   ```

1. Check the operators have been installed

   ```
   UI -> Installed Operators
   ```

1. Obtain the ArgoCD urls and passwords

   The URLs and login credentials for ArgoCD change depending on the pattern
   name and the site names they control.  Follow the instructions below to find
   them, however you choose to deploy the pattern.

   Display the fully qualified domain names, and matching login credentials, for
   all ArgoCD instances:

   ```
   ARGO_CMD=`oc get secrets -A -o jsonpath='{range .items[*]}{"oc get -n "}{.metadata.namespace}{" routes; oc -n "}{.metadata.namespace}{" extract secrets/"}{.metadata.name}{" --to=-\\n"}{end}' | grep gitops-cluster`
   eval $ARGO_CMD
   ```

   The result should look something like:

   ```
   NAME                       HOST/PORT                                                                                         PATH      SERVICES                   PORT    TERMINATION            WILDCARD
   hub-gitops-server   hub-gitops-server-industrial-edge-datacenter.apps.mycluster.mydomain.com          datacenter-gitops-server   https   passthrough/Redirect   None
   # admin.password
   2F6kgITU3DsparWyC

   NAME                      HOST/PORT                                                                              PATH   SERVICES                  PORT    TERMINATION            WILDCARD
   cluster                   cluster-openshift-gitops.apps.mycluster.mydomain.com                          cluster                   8080    reencrypt/Allow        None
   kam                       kam-openshift-gitops.apps.mycluster.mydomain.com                              kam                       8443    passthrough/None       None
   openshift-gitops-server   openshift-gitops-server-openshift-gitops.apps.mycluster.mydomain.com          openshift-gitops-server   https   passthrough/Redirect   None
   # admin.password
   WNklRCD8EFg2zK034
   ```
# Dealing with the Vault

This pattern uses the HashiCorp vault operator and helm chart as a mechanism for storing and retrieving secrets.  The
vault runs in regular mode, which requires some special handling, in the case of bootstrap and if the cluster is ever
completely shut down.

It is worth noting that in this pattern we deploy only a single instance of the vault per cluster - ordinarily there
would be multiple copies of the vault running, to support high availability.

For more info consult the [HashiCorp Vault Documentation](https://learn.hashicorp.com/tutorials/vault/kubernetes-raft-deployment-guide?in=vault/kubernetes#initialize-and-unseal-vault) which covers these and other issues in detail.

## Bootstrap: init and unseal
```
make vault-init
```

Note: the vault server does offer a "dev" mode which allows usage of the vault but disables storage of secrets and is
not suitable for use in any kind of production environment.

When the pattern is first installed on the cluster, the vault must be initialized.  The initialization process will
generate a series of unseal keys which must be sent to the vault server to allow access to it. The pattern provides some scripting and utilities to initialize and unseal the new vault, which is necessary in order to use it.  The necessary
commands are bundled into the Makefile, which calls an included shell script, `common/scripts/vault-utils.sh`.

Because there is not really a situation where you would want to initialize and unseal a vault separately, the
`vault-init` target does both operations together.  The provided script differentiates the actions, if you wish to run
them separately.

So `make vault-init` will run both the `vault operator init` and `vault operator unseal` operations on the new vault.
This only needs to be done when initially creating the vault - subsequently, the vault only needs to be unsealed to use it.

The `make vault-init` process will also create a file in the git repository common directory called `pattern-vault.init`
which will contain the output of the `vault operator init` command - this includes 5 Unseal Keys and a Root Token. It is
handy to keep that file for future reference (the Unseal Keys are required to re-open the vault if it goes down), but
the filename is included in the .gitignore file for the repo so it is intentionally difficult (and not recommended) to
commit it to git.

## Cluster Power-Off: unseal

```
make vault-unseal
```

If, operationally, all nodes serving the vault go offline, the vault needs to be unsealed again to use use it.  (This
would happen, for example, if the cluster running the pattern is entirely powered down.)  Unsealing a vault is designed
to be a manual process.  Assuming the vault was initialized according the directions above, the Unseal Keys
will be recorded in the file `common/pattern-vault.init`.  These keys are required to unseal the vault for use again,
which can be done by running `make vault-unseal` in the project root directory.

# Pattern Layout and Structure

https://slides.com/beekhof/hybrid-cloud-patterns

# Uninstalling

**Probably wont work**

1. Turn off auto-sync

   `helm upgrade multicloud-gitops . --values ~/values-secret.yaml --set global.options.syncPolicy=Manual`

1. Remove the ArgoCD applications (except for hub)

   a. Browse to ArgoCD
   a. Go to Applications
   a. Click delete
   a. Type the application name to confirm
   a. Chose "Foreground" as the propagation policy
   a. Repeat

1. Wait until the deletions succeed

   `manuela-datacenter` should be the only remaining application

1. Complete the uninstall

   `helm delete multicloud-gitops`

1. Check all namespaces and operators have been removed

# Diagrams

The following diagrams show the different components deployed on the datacenter and the factory.

## Logical

## Schematic with Networks

## Schematic with Dataflows

## Editing the diagrams.
