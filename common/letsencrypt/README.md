# Letsencrypt support for Validated patterns

This is an *EXPERIMENTAL* and *UNSUPPORTED* chart to enable letsencrypt support in the pattern.
Currently the only supported cloud for this is AWS.

In order to enable this chart in your patterns, please add and edit the following lines to `values-AWS.yaml`:

    letsencrypt:
      region: eu-central-1 # region of the cluster
      server: https://acme-v02.api.letsencrypt.org/directory
      # staging URL
      # server: https://acme-staging-v02.api.letsencrypt.org/directory
      email: foo@bar.it

    clusterGroup:
      applications:
        letsencrypt:
          name: letsencrypt
          namespace: letsencrypt
          project: default
          path: common/letsencrypt

Once the above is enabled in a pattern, a certain amount of time (~15/20 minutes or so) is needed for all the cluster operators to settle, all the HTTPS routes will have a wildcard certificate signed by letsencrypt. By default also the API endpoint will use a certificate signed by letsencrypt.

## Limitations

Please be aware of the following gotchas when using this chart:

1. Once the API certificate has been replaced with the letsencrypt one, the `oc` commands might fail with x509 unknown certificate authority errors.
   You need to remove the previous CA from the kubeconfig file. Run: `oc config set-cluster <clustername> --certificate-authority="/dev/null" --embed-certs`
2. When you switch to non-staging letsencrypt certificates, things might fail if you asked for too many certificates over the last few days.
3. The cluster takes ~20-30 mins to fully settle when both the API endpoint and the default ingress certificates are implemented

## Implementation

This chart creates a Cloud Credential that is allowed to write and read DNS entries via Route53 in AWS. That credential is then used by cert-manager to prove ownership of the DNS zone and answer the ACME DNS01 challenges.
We ask for a single wildcard certificate for the default Ingress *.apps.domain and one non-wildcard certificate for the API endpoint api.domain.
We use Argo's Server-Side Apply feature to patch in the Ingress Controller and the API endpoint certificates.
Currently we also patch the main cluster-wide Argo instance to set the tls route to `reencrypt` in order have a proper cert there. Once issue 297 in the gitops-operator repository is fixed, we can drop that.

## Parameters

### global parameters

This section contains the global parameters consumed by this chart

| Name                        | Description                                                                                          | Value              |
| --------------------------- | ---------------------------------------------------------------------------------------------------- | ------------------ |
| `global.localClusterDomain` | String containing the domain including the apps. prefix. Gets set by the Validated Pattern framework | `apps.example.com` |

### letsencrypt parameters

This section contains all the parameters for the letsencrypt
chart in order to request CA signed certificates in a Validated Pattern

| Name                             | Description                                                                                                           | Value                                                    |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| `letsencrypt.enabled`            | Boolean to enable this feature and request a wildcard cert for the default Infress (*.apps.domain) (defaults to True) | `true`                                                   |
| `letsencrypt.api_endpoint`       | Boolean to enable letsencrypt certs on the API endpoint too (defaults to True)                                        | `true`                                                   |
| `letsencrypt.region`             | String that defines the region used by the route53/dns01 resolver in cert-manager (required)                          | `eu-central-1`                                           |
| `letsencrypt.email`              | String containing the email used when requesting certificates to letsencrypt (required)                               | `test@example.com`                                       |
| `letsencrypt.server`             | String containing the letsencrypt ACME URL (Defaults to the staging server)                                           | `https://acme-staging-v02.api.letsencrypt.org/directory` |
| `letsencrypt.organizations`      | List of organization names to be put in a certificate (Defaults to [hybrid-cloud-patterns.io])                        | `["hybrid-cloud-patterns.io"]`                           |
| `letsencrypt.usages`             | List of certificate uses. See API cert-manager.io/v1.KeyUsage (Defaults to [server auth])                             | `["server auth"]`                                        |
| `letsencrypt.duration`           | Duration of the requested letsencrypt certificates (Defaults to 168h0m0s)                                             | `168h0m0s`                                               |
| `letsencrypt.renewBefore`        | How long before expiration date should the certs be renewed (Defaults to 28h0m0s)                                     | `28h0m0s`                                                |
| `letsencrypt.nameservers`        | List of DNS server (ip:port strings) to be used when doing DNS01 challenges (Defaults to [8.8.8.8:53, 1.1.1.1:53])    | `["8.8.8.8:53","1.1.1.1:53"]`                            |
| `letsencrypt.certmanagerChannel` | String the channel to install cert-manager from (Defaults to "stable-v1")                                             | `stable-v1`                                              |
