{{/*
Expand the name of the chart.
*/}}
{{- define "ingestion-metrics.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "ingestion-metrics.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "ingestion-metrics.fullname" -}}
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
{{- define "ingestion-metrics.labels" -}}
helm.sh/chart: {{ include "ingestion-metrics.chart" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: {{ include "ingestion-metrics.name" . }}
{{ include "ingestion-metrics.selectorLabels" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "ingestion-metrics.selectorLabels" -}}
app.kubernetes.io/name: {{ include "ingestion-metrics.fullname" . }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "ingestion-metrics.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "ingestion-metrics.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}