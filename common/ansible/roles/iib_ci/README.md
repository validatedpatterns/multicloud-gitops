# IIB Utilities

A set of ansible plays to fetch an IIB (Image Index Bundle, aka a container created by the operator SDK
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

### Gitops operator

Then in case of the `openshift-gitops-operator` we would install with:

```sh
export CHANNEL=$(oc get -n openshift-marketplace packagemanifests -l "catalog=iib-${IIB}" --field-selector "metadata.name=${OPERATOR}" -o jsonpath='{.items[0].status.defaultChannel}')
make EXTRA_HELM_OPTS="--set main.gitops.operatorSource=iib-${IIB} --set main.gitops.channel=${CHANNEL}" install
```

### ACM operator

The advanced-cluster-management operator is a little bit more complex than the others because it
also installes another operator called MCE multicluster-engine. So to install ACM you typically
need two IIBs (one for acm and one for mce). With those two at hand, do the following (the ordering must be
consistent: the first IIB corresponds to the first OPERATOR, etc). The following operation needs to be done
on both hub *and* spokes:

```sh
for i in hub-kubeconfig-file spoke-kubeconfig-file; do
  export KUBECONFIG="${i}"
  export KUBEADMINPASS="11111-22222-33333-44444"
  export OPERATOR=advanced-cluster-management,multicluster-engine
  export INDEX_IMAGES=registry-proxy.engineering.redhat.com/rh-osbs/iib:713808,registry-proxy.engineering.redhat.com/rh-osbs/iib:718034
  make load-iib
done
```

Once the IIBs are loaded into the cluster we need to run the following steps:

```sh
export ACM_CHANNEL=$(oc get -n openshift-marketplace packagemanifests -l "catalog=iib-713808" --field-selector "metadata.name=advanced-cluster-management" -o jsonpath='{.items[0].status.defaultChannel}')
export MCE_CHANNEL=$(oc get -n openshift-margetplace packagemanifests -l "catalog=iib-718034" --field-selector "metadata.name=multicluster-engine" -o jsonpath='{.items[0].status.defaultChannel}')
make EXTRA_HELM_OPTS="--set main.extraParameters[0].name=clusterGroup.subscriptions.acm.source --set main.extraParameters[0].value=iib-713808 \
                      --set main.extraParameters[1].name=clusterGroup.subscriptions.acm.channel --set main.extraParameters[1].value=${ACM_CHANNEL} \
                      --set main.extraParameters[2].name=acm.mce_operator.source --set main.extraParameters[2].value="iib-718034" \
                      --set main.extraParameters[3].name=acm.mce_operator.channel --set main.extraParameters[3].value=${MCE_CHANNEL}" install
```

*Note*: In this case the `acm` in `clusterGroup.subscriptions.acm.*` is the name of the key in the subscriptions in `values-hub.yaml`

### Other operators

To install operators other than gitops and acm do the following:

```sh
export CHANNEL=$(oc get -n openshift-marketplace packagemanifests -l "catalog=iib-${IIB}" --field-selector "metadata.name=${OPERATOR}" -o jsonpath='{.items[0].status.defaultChannel}')
make EXTRA_HELM_OPTS="--set main.extraParameters[0].name=clusterGroup.subscriptions.<subname>.source --set main.extraParameters[0].value=iib-${IIB} --set main.extraParameters[1].name=clusterGroup.subscriptions.<subname>.channel --set main.extraParameters[1].value=${CHANNEL}" install
```

*Note*: Replace `<subname>` with the actual name of the subscription dictionary in `values-hub.yaml`

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
