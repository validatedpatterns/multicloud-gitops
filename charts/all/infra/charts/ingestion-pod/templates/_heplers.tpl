{{/*
Expand the name of the chart.
*/}}
{{- define "ingestion-pod.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "ingestion-pod.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "ingestion-pod.fullname" -}}
{{- $name := default .Chart.Name }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}


{{/*
Common labels
*/}}
{{- define "ingestion-pod.labels" -}}
helm.sh/chart: {{ include "ingestion-pod.chart" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: {{ include "ingestion-pod.name" . }}
{{ include "ingestion-pod.selectorLabels" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "ingestion-pod.selectorLabels" -}}
app.kubernetes.io/name: {{ include "ingestion-pod.fullname" . }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "ingestion-pod.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "ingestion-pod.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}