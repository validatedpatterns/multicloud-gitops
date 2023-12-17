# IIB Utilities

A set of ansible plays to fetch an IIB (Image Index Bundle, aka a container created by the operator sdk
that contains a bunch of references to operators that can be installed in an OpenShift cluster)

Run `ansible-playbook common/ansible/playbooks/iib-ci/lookup.yml` to see which IIBs are available (defaults to
openshift-gitops). If you want to look up IIBs for a different operator run:
`ansible-playbook -e operator=acm-operator common/ansible/playbooks/iib-ci/lookup.yml`

You can also try running curl manually via:
`curl -sSL "https://datagrepper.engineering.redhat.com/raw?topic=/topic/VirtualTopic.eng.ci.redhat-container-image.index.built&delta=15780000&contains=acm-operator" | jq ".raw_messages[].msg"`

Typically IIB are prerelease stuff that lives on some internal boxes. What these scripts do is fetch
the IIB internally, mirror it to the registry inside the cluster, parse all the needed images and mirror
those to the internal cluster registry and then set up the registries.conf files on all nodes so
that the images used are the ones pointing to the internal cluster.

## Usage

By default the operator to be installed from the IIB is `openshift-gitops-operator`. You can override this through the `OPERATOR` env variable.
For example, to mirror an operator into an existing cluster you would do the following:

```sh
export KUBECONFIG=/tmp/foo/kubeconfig
export OPERATOR=openshift-gitops-operator
export IIB=492329
export INDEX_IMAGES=registry-proxy.engineering.redhat.com/rh-osbs/iib:${IIB}
export KUBEADMINPASS="11111-22222-33333-44444"
# This will push the IIB and all the needed images for the default openshift-gitops-operator into the cluster
make load-iib
# This will install the pattern using the gitops operator from the IIB
```

***NOTE:*** When using an SNO without shared storage in a non-production environment, the enablement of the internal registry will fail. You need to run the following to enable it:

```sh
oc patch configs.imageregistry.operator.openshift.io cluster --type merge --patch '{"spec":{"managementState":"Managed"}}'
oc patch configs.imageregistry.operator.openshift.io cluster --type merge --patch '{"spec":{"storage":{"emptyDir":{}}}}'
```

Then in case of the `openshift-gitops-operator` we would install with:

```sh
export CHANNEL=$(oc get -n openshift-marketplace packagemanifests -l "catalog=iib-${IIB}" --field-selector "metadata.name=${OPERATOR}" -o jsonpath='{.items[0].status.defaultChannel}')
make EXTRA_HELM_OPTS="--set main.gitops.operatorSource=iib-${IIB} --set main.gitops.channel=${CHANNEL}" install
```

To install ACM (`export OPERATOR=advanced-cluster-management`) or any other
operator (except the gitops one) from an IIB we would call the following as a
final step:

```sh
export CHANNEL=$(oc get -n openshift-marketplace packagemanifests -l "catalog=iib-${IIB}" --field-selector "metadata.name=${OPERATOR}" -o jsonpath='{.items[0].status.defaultChannel}')
make EXTRA_HELM_OPTS="--set main.extraParameters[0].name=clusterGroup.subscriptions.acm.source --set main.extraParameters[0].value=iib-${IIB} --set main.extraParameters[1].name=clusterGroup.subscriptions.acm.channel --set main.extraParameters[1].value=${CHANNEL}" install
```

*Note*: In this case `acm` is the name of the subscription in `values-hub.yaml`

### OCP 4.13 and onwards

Since 4.13 supports an internal registry that can cope with v2 docker manifests, we
use that. Run `make iib` with the following environment variables set:

* `INDEX_IMAGES=registry-proxy.engineering.redhat.com/rh-osbs/iib:492329`
* `KUBEADMINPASS="11111-22222-33333-44444"`

### OCP 4.12 and previous versions

Due to the lack of v2 manifest support on the internal registry, we use an external
registry. Run `make iib` with the following environment variables set:

* `INDEX_IMAGES=registry-proxy.engineering.redhat.com/rh-osbs/iib:492329`
* `REGISTRY=quay.io/rhn_support_mbaldess/iib`
* `REGISTRY_TOKEN=<username>:<token>`

*Note*: For the REGISTRY_TOKEN go to your quay repository, add a robot with "Write" permissions. The robot created will have a "username" and "password" fields. Set the REGISTRY_TOKEN environment variable to that value.

## Useful commands

* List IIBs for an operator:

```sh
ansible-playbook common/ansible/playbooks/iib-ci/lookup.yml
...
ok: [localhost] => (item=v4.13) => {
    "msg": "v4.13 -> {'indeximage': 'registry-proxy.engineering.redhat.com/rh-osbs/iib:509435', 'bundleimage': 'registry-proxy.engineering.redhat.com/rh-osbs/openshift-gitops-1-gitops-operator-bundle:v99.9.0-106'}"
}
...
```

Override the `operator` value with the desired bundle name to figure out the last IIBs for it.

* List all images uploaded to the internal registry:

```sh
oc exec -it -n openshift-image-registry $(oc get pods -n openshift-image-registry -o json | jq -r '.items[].metadata.name | select(. | test("^image-registry-"))' | head -n1) -- bash -c "curl -k -u kubeadmin:$(oc whoami -t) https://localhost:5000/v2/_catalog"
```
