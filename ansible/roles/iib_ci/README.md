# IIB Utilities

A set of ansible plays to fetch an IIB (Image Index Bundle, aka a container created by the operator sdk
that contains a bunch of references to operators that can be installed in an OpenShift cluster)

Run `make lookup` to see which IIBs are available.

Typically IIB are prerelease stuff that lives on some internal boxes. What these scripts do is fetch
the IIB internally, mirror it to the registry inside the cluster, parse all the needed images and mirror
those to the internal cluster registry and then set up the registries.conf files on all nodes so
that the images used are the ones pointing to the internal cluster.

## Usage

By default the operator to be installed from the IIB is `openshift-gitops-operator`. You can override this through the `OPERATOR` env variable.
For example, to install openshift-gitops from an IIB on OCP 4.13 you would do the following:

```sh
export KUBECONFIG=/tmp/foo/kubeconfig
export INDEX_IMAGES=registry-proxy.engineering.redhat.com/rh-osbs/iib:iib-492329 
export KUBEADMINAPI=https://api.mcg-hub.blueprints.rhecoeng.com:6443
export KUBEADMINPASS="11111-22222-33333-44444"
# This will push the IIB and all the needed images for the default openshift-gitops-operator into the cluster
make load-iib
# This will install the pattern using the gitops operator from the IIB
export CHANNEL=$(oc get -n openshift-marketplace packagemanifests -l "catalog=iib-492329" --field-selector 'metadata.name=openshift-gitops-operator' -o jsonpath='{.items[0].status.defaultChannel}')
make EXTRA_HELM_OPTS="--set main.gitops.operatorSource=iib-492329 --set main.gitops.channel=${CHANNEL}" install 2>&1 | tee /tmp/install.log
```

*Note*: This needs VP operator version >= 0.0.14

### OCP 4.13 and onwards

Since 4.13 supports an internal registry that can cope with v2 docker manifests, we
use that. Run `make iib` with the following environment variables set:

* `INDEX_IMAGE=registry-proxy.engineering.redhat.com/rh-osbs/iib:492329`
* `KUBEADMINAPI=https://api.mcg-hub.blueprints.rhecoeng.com:6443`
* `KUBEADMINPASS="11111-22222-33333-44444"`

### OCP 4.12 and previous versions

Due to the lack of v2 manifest support on the internal registry, we use an external
registry. Run `make iib` with the following environment variables set:

* `INDEX_IMAGE=registry-proxy.engineering.redhat.com/rh-osbs/iib:492329`
* `REGISTRY=quay.io/rhn_support_mbaldess/iib`
* `REGISTRY_TOKEN=<username>:<token>`

## Useful commands

* List all images uploaded to the internal registry:

```sh
oc exec -it -n openshift-image-registry $(oc get pods -n openshift-image-registry -o json | jq -r '.items[].metadata.name | select(. | test("^image-registry-"))' | head -n1) -- bash -c "curl -k -u kubeadmin:$(oc whoami -t) https://localhost:5000/v2/_catalog"
```
