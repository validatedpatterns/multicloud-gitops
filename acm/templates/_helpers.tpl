{{/*
Default always defined valueFiles to be included when pushing the cluster wide argo application via acm
*/}}
{{- define "acm.app.policies.valuefiles" -}}
- "/values-global.yaml"
- "/values-{{ .name }}.yaml"
- '/values-{{ `{{ (lookup "config.openshift.io/v1" "Infrastructure" "" "cluster").spec.platformSpec.type }}` }}.yaml'
- '/values-{{ `{{ (lookup "config.openshift.io/v1" "Infrastructure" "" "cluster").spec.platformSpec.type }}` }}-{{ `{{ printf "%d.%d" ((semver (index (lookup "config.openshift.io/v1" "ClusterVersion" "" "version").status.history 0).version).Major) ((semver (index (lookup "config.openshift.io/v1" "ClusterVersion" "" "version").status.history 0).version).Minor) }}` }}.yaml'
- '/values-{{ `{{ (lookup "config.openshift.io/v1" "Infrastructure" "" "cluster").spec.platformSpec.type }}` }}-{{ .name }}.yaml'
# We cannot use $.Values.global.clusterVersion because that gets resolved to the
# hub's cluster version, whereas we want to include the spoke cluster version
- '/values-{{ `{{ printf "%d.%d" ((semver (index (lookup "config.openshift.io/v1" "ClusterVersion" "" "version").status.history 0).version).Major) ((semver (index (lookup "config.openshift.io/v1" "ClusterVersion" "" "version").status.history 0).version).Minor) }}` }}.yaml'
{{- end }} {{- /*acm.app.policies.valuefiles */}}
