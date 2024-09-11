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

{{- define "acm.app.policies.multisourcevaluefiles" -}}
- "$patternref/values-global.yaml"
- "$patternref/values-{{ .name }}.yaml"
- '$patternref/values-{{ `{{ (lookup "config.openshift.io/v1" "Infrastructure" "" "cluster").spec.platformSpec.type }}` }}.yaml'
- '$patternref/values-{{ `{{ (lookup "config.openshift.io/v1" "Infrastructure" "" "cluster").spec.platformSpec.type }}` }}-{{ `{{ printf "%d.%d" ((semver (index (lookup "config.openshift.io/v1" "ClusterVersion" "" "version").status.history 0).version).Major) ((semver (index (lookup "config.openshift.io/v1" "ClusterVersion" "" "version").status.history 0).version).Minor) }}` }}.yaml'
- '$patternref/values-{{ `{{ (lookup "config.openshift.io/v1" "Infrastructure" "" "cluster").spec.platformSpec.type }}` }}-{{ .name }}.yaml'
# We cannot use $.Values.global.clusterVersion because that gets resolved to the
# hub's cluster version, whereas we want to include the spoke cluster version
- '$patternref/values-{{ `{{ printf "%d.%d" ((semver (index (lookup "config.openshift.io/v1" "ClusterVersion" "" "version").status.history 0).version).Major) ((semver (index (lookup "config.openshift.io/v1" "ClusterVersion" "" "version").status.history 0).version).Minor) }}` }}.yaml'
{{- end }} {{- /*acm.app.policies.multisourcevaluefiles */}}

{{- define "acm.app.policies.helmparameters" -}}
- name: global.repoURL
  value: {{ $.Values.global.repoURL }}
- name: global.originURL
  value: {{ $.Values.global.originURL }}
- name: global.targetRevision
  value: {{ $.Values.global.targetRevision }}
- name: global.namespace
  value: $ARGOCD_APP_NAMESPACE
- name: global.pattern
  value: {{ $.Values.global.pattern }}
- name: global.hubClusterDomain
  value: {{ $.Values.global.hubClusterDomain }}
- name: global.localClusterDomain
  value: '{{ `{{ (lookup "config.openshift.io/v1" "Ingress" "" "cluster").spec.domain }}` }}'
- name: global.clusterDomain
  value: '{{ `{{ (lookup "config.openshift.io/v1" "Ingress" "" "cluster").spec.domain | replace "apps." "" }}` }}'
- name: global.clusterVersion
  value: '{{ `{{ printf "%d.%d" ((semver (index (lookup "config.openshift.io/v1" "ClusterVersion" "" "version").status.history 0).version).Major) ((semver (index (lookup "config.openshift.io/v1" "ClusterVersion" "" "version").status.history 0).version).Minor) }}` }}'
- name: global.localClusterName
  value: '{{ `{{ (split "." (lookup "config.openshift.io/v1" "Ingress" "" "cluster").spec.domain)._1 }}` }}'
- name: global.clusterPlatform
  value: {{ $.Values.global.clusterPlatform }}
- name: global.multiSourceSupport
  value: {{ $.Values.global.multiSourceSupport | quote }}
- name: global.multiSourceRepoUrl
  value: {{ $.Values.global.multiSourceRepoUrl }}
- name: global.multiSourceTargetRevision
  value: {{ $.Values.global.multiSourceTargetRevision }}
- name: global.privateRepo
  value: {{ $.Values.global.privateRepo | quote }}
- name: global.experimentalCapabilities
  value: {{ $.Values.global.experimentalCapabilities }}
{{- end }} {{- /*acm.app.policies.helmparameters */}}
