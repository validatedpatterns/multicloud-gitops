# VP hashicorp-vault

**IMPORTANT**: Due to the fact that 'null' values do not work in helm charts
([GH#9136](https://github.com/helm/helm/issues/9136)), we need to patch the
chart to skip setting the host.

Make sure to run "./update-helm-dependency.sh" after you updated the subchart
(by calling helm dependency update .)

We can drop this local patch when any one the two conditions is true:

- [1] is fixed in helm and we can require the version that for installs
- [PR#779](https://github.com/hashicorp/vault-helm/pull/779) is merged in vault-helm *and* our minimum supported OCP version
  is OCP 4.11 (route subdomain is broken in OCP < 4.11 due to missing [commit](https://github.com/openshift/router/commit/6f730c7cae966f0ed8def50c81d1bf10fe9eb77b)
