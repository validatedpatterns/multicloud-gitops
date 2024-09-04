{{/*
Expand the name of the chart.
*/}}
{{- define "query.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "query.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "query.fullname" -}}
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
{{- define "query.labels" -}}
helm.sh/chart: {{ include "query.chart" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: {{ include "query.name" . }}
{{ include "query.selectorLabels" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "query.selectorLabels" -}}
app.kubernetes.io/name: {{ include "query.fullname" . }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "query.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "query.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}