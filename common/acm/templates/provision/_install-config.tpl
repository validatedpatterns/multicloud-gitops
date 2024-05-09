{{- define "cluster.install-config" -}}

{{- $type := "None" }}
{{- $cloud := "None" }}
{{- $region := "None" }}

{{- if .platform.aws }}
{{- $cloud = "aws" }}
{{- $region = .platform.aws.region }}
{{- $type = "m5.xlarge" }}
{{- else if .platform.azure }}
{{- $cloud = "azure" }}
{{- $region = .platform.azure.region }}
{{- $type = "Standard_D8s_v3" }}
{{- end }}

apiVersion: v1
metadata:
  name: '{{ .name }}' 
baseDomain: {{ .baseDomain }}
controlPlane:
  architecture: amd64
  hyperthreading: Enabled
  name: controlPlane
  {{- if .controlPlane }}
  replicas: {{ default 3 .controlPlane.count }}
  {{- if .controlPlane.platform }}
  platform:
    {{- toYaml .controlPlane.platform | nindent 4 }}
  {{- end }}
  {{- else }}
  replicas: 3
  platform:
    {{ $cloud }}:
      type: {{ $type }}
  {{- end }}
compute:
- hyperthreading: Enabled
  architecture: amd64
  name: 'worker'
  {{- if .workers }}
  replicas: {{ default 0 .workers.count }}
  {{- if .workers.platform }}
  platform:
    {{- toYaml .workers.platform | nindent 4 }}
  {{- end }}
  {{- else }}
  replicas: 3
  platform:
    {{ $cloud }}:
      type: {{ $type }}
  {{- end }}
networking:
  clusterNetwork:
  - cidr: 10.128.0.0/14
    hostPrefix: 23
  machineNetwork:
  - cidr: 10.0.0.0/16
  networkType: OVNKubernetes
  serviceNetwork:
  - 172.30.0.0/16
platform:
{{- toYaml .platform | nindent 2 }}
pullSecret: "" # skip, hive will inject based on it's secrets
sshKey: ""     # skip, hive will inject based on it's secrets
{{- end -}}
