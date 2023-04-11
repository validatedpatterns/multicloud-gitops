# Changes

## Apr 11, 2023

* Apply the ACM ocp-gitops-policy everywhere but the hub

## Apr 7, 2023

* Moved to gitops-1.8 channel by default (stable is unmaintained and will be dropped starting with ocp-4.13)

## March 20, 2023

* Upgraded ESO to 0.8.1

## February 9, 2023

* Add support for /values-<platform>.yaml and for /values-<platform>-<clusterversion>.yaml

## January 29, 2023

* Stop extracting the HUB's CA via an imperative job running on the imported cluster.
  Just use ACM to push the HUB's CA out to the managed clusters.

## January 23, 2023

* Add initial support for running ESO on ACM-imported clusters

## January 18, 2023

* Add validate-schema target

## January 13, 2023

* Simplify the secrets paths when using argo hosted sites

## January 10, 2023

* vaultPrefixes is now optional in the v2 secret spec and defaults to ["hub"]

## December 9, 2022

* Dropped insecureUnsealVaultInsideCluster (and file_unseal) entirely. Now
  vault is always unsealed via a cronjob in the cluster. It is recommended to
  store the imperative/vaultkeys secret offline securely and then delete it.

## December 8, 2022

* Removed the legacy installation targets:
  `deploy upgrade legacy-deploy legacy-upgrade`
  Patterns must now use the operator-based installation

## November 29, 2022

* Upgraded vault-helm to 0.23.0
* Enable vault-ssl by default

## November 22, 2022

* Implemented a new format for the values-secret.yaml. Example can be found in examples/ folder
* Now the order of values-secret file lookup is the following:
  1. ~/values-secret-<patternname>.yaml
  2. ~/values-secret.yaml
  3. <patterngitrepo>/values-secret.yaml.template
* Add support for ansible vault encrypted values-secret files. You can now encrypt your values-secret file
  at rest with `ansible-vault encrypt ~/values-secret.yaml`. When running `make load-secrets` if an encrypted
  file is encountered the user will be prompted automatically for the password to decrypt it.

## November 6, 2022

* Add support for /values-<CloudPlatform>-<clusterGroup>.yaml (e.g. /values-AWS-group-one.yaml)

## October 28, 2022

* Updated vault helm chart to v0.22.1 and vault containers to 1.12.0

## October 25, 2022

* Updated External Secrets Operator to v0.6.0
* Moved to -UBI based ESO containers

## October 13, 2022

* Added global.clusterVersion as a new helm variable which represents the OCP
  Major.Minor cluster version. By default now a user can add a
  values-<ocpversion>-<clustergroup>.yaml file to have specific cluster version
  overrides (e.g. values-4.10-hub.yaml). Will need Validated Patterns Operator >= 0.0.6
  when deploying with the operator. Note: When using the ArgoCD Hub and spoke model,
  you cannot have spokes with a different version of OCP than the hub.

## October 4, 2022

* Extended the values-secret.yaml file to support multiple vault paths and re-wrote
  the push_secrets feature as python module plugin. This requires the following line
  in a pattern's ansible.cfg's '[defaults]' stanza:

  `library=~/.ansible/plugins/modules:./ansible/plugins/modules:./common/ansible/plugins/modules:/usr/share/ansible/plugins/modules`

## October 3, 2022

* Restore the ability to install a non-default site: `make TARGET_SITE=mysite install`
* Revised tests (new output and filenames, requires adding new result files to git)
* ACM 2.6 required for ACM-based managed sites
* Introduced global.clusterDomain template variable (without the `apps.` prefix)
* Removed the ability to send specific charts to another cluster, use hosted argo sites instead
* Added the ability to have the hub host `values-{site}.yaml` for spoke clusters.

  The following example would deploy the namespaces, subscriptions, and
  applications defined in `values-group-one.yaml` to the `perth` cluster
  directly from ArgoCD on the hub.

  ```yaml
  managedClusterGroups:
  - name: group-one
    hostedArgoSites:
    - name: perth
      domain: perth1.beekhof.net
      bearerKeyPath: secret/data/hub/cluster_perth
      caKeyPath: secret/data/hub/cluster_perth_ca
  ```
