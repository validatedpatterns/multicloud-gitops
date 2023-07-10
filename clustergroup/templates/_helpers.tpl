{{/*
Default always defined top-level variables for helm charts
*/}}
{{- define "clustergroup.app.globalvalues.helmparameters" -}}
- name: global.repoURL
  value: $ARGOCD_APP_SOURCE_REPO_URL
- name: global.targetRevision
  value: $ARGOCD_APP_SOURCE_TARGET_REVISION
- name: global.namespace
  value: $ARGOCD_APP_NAMESPACE
- name: global.pattern
  value: {{ $.Values.global.pattern }}
- name: global.clusterDomain
  value: {{ $.Values.global.clusterDomain }}
- name: global.clusterVersion
  value: "{{ $.Values.global.clusterVersion }}"
- name: global.clusterPlatform
  value: "{{ $.Values.global.clusterPlatform }}"
- name: global.hubClusterDomain
  value: {{ $.Values.global.hubClusterDomain }}
- name: global.localClusterDomain
  value: {{ coalesce $.Values.global.localClusterDomain $.Values.global.hubClusterDomain }}
{{- end }} {{/* clustergroup.globalvaluesparameters */}}


