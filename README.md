# Hosted Control Planes ( HyperShift )

# HyperShift docs under construction

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

[Live build status](https://validatedpatterns.io/ci/?pattern=mcgitops)

## Start Here

Official documentation for this pattern will soon be available on our docs site. Until then, here are a few helpful
hints to get you started. 

This pattern use the validated patterns gitops framework to deploy and configure the hosted control plane operator and
if you so choose, the AWS S3 Controller for Kubernetes to create the bucket needed for hypershift and OIDC. If not, you will
need to have provisioned a bucket with a public policy attached. 

## PreRequisites

1. You will need to have your own OpenShift cluster. The configuration for our team Hypershift environment 
is a 3 Node - `m5.4xl` cluster in AWS. The size of your machines depends solely on the workloads and number of hostedclusters
you intend to run on them.

2. For both hypershift and aws s3 controller we need to configure secrets that use your aws credentials. The default uses
`~/.aws/credentials` for parsing the credential. 

3. If you elect to not use ACK for creating your s3 bucket, please see the **NOTE** below. Some extra configuration is
necessary to ensure you don't deploy extra operators and configurations you don't need. 

## Actions

To get started you will need to fork & clone this repository:

- `git clone https://github.com/validatedpatterns-sandbox/hypershift`

- `cd hypershift`

- `vim values-hypershift.yaml`

- `git commit & push your changes`

- `run ./patterns.sh make install`

|Parameter | Default (if defined) | Purpose |
|----------|----------------------|---------|
|useExternalSecrets| true | When using the patterns framework this should be true. This will provision the necessary secrets for you using eso|
| createBucket | true | This provisions the s3 bucket to be used by hypershift |
| region | `<n/a>` | Define the region that you want your s3 bucket created in |
| bucketName | `<n/a>` | Define the name of your bucket - must be DNS compatible (no `_'s` or special characters) |
| additionalTags | `<n/a>` | Create a map of tags to be added to the bucket in `key: value` format|
| buildConfig.git.uri | `<n/a>` | This should be the url to your git repository |

An example `values-hypershift.yaml` that has been completed:

```yaml
global:
  useExternalSecrets: true
  s3:
    createBucket: true
    region: us-west-1
    bucketName: jrickard-hcp
    additionalTags:
      bucketOwner: jrickard
      lifecycle: keep
  
  buildconfig:
    git:
      uri: https://github.com/validatedpatterns-sandbox/hypershift
```

**NOTE** 
If you set `createBucket` to `false` you will also need to edit `values-hub.yaml` and either comment or remove references to ack-system / s3 in the following locations:
- namespaces
    - ack-system
- subscriptions
    - ```
        s3:
          name: ack-s3-controller
          namespace: ack-system
          channel: alpha
          source: community-operators
      ```
- projects:
    - s3

- applications:
    - ```
      s3:
        name: s3-controller
        namespace: ack-system
        project: s3
        path: charts/all/ack-s3  
      ```

If you've followed a link to this repository, but are not really sure what it contains
or how to use it, head over to [Multicloud GitOps](http://validatedpatterns.io/multicloud-gitops/)
for additional context and installation instructions
