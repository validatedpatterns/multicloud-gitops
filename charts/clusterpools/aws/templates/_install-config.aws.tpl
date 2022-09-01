{{- define "cluster.install-config" -}}
apiVersion: v1
metadata:
  name: '{{ .name }}' 
baseDomain: {{ .provider.baseDomain }}
controlPlane:
  architecture: amd64
  hyperthreading: Enabled
  name: controlPlane
  replicas: {{ default 3 .controlPlane.count }}
  platform:
    aws:
      type: {{ .controlPlane.machineType }}
compute:
- hyperthreading: Enabled
  architecture: amd64
  name: 'worker'
  replicas: {{ default 3 .workers.count }}
  platform:
    aws:
      type: {{ .workers.machineType }}
networking:
  clusterNetwork:
  - cidr: 10.128.0.0/14
    hostPrefix: 23
  machineNetwork:
  - cidr: 10.0.0.0/16
  networkType: OpenShiftSDN
  serviceNetwork:
  - 172.30.0.0/16
platform:
  aws:
    region: {{ .provider.region }}
pullSecret: "" # skip, hive will inject based on it's secrets
sshKey: |-
    {{ .provider.sshPublickey }}
{{- end -}}