# Changes

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
