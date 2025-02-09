{{/* _helpers.tpl */}}
{{- define "health-dashboard.name" -}}
{{- print .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end }}

{{- define "health-dashboard.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else if .Values.nameOverride }}
{{- .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- else }}
{{- include "health-dashboard.name" . }}-{{ .Release.Name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{- define "health-dashboard.chart" -}}
{{- print .Chart.Name "-" .Chart.Version | trunc 63 | trimSuffix "-" -}}
{{- end }}

{{- define "health-dashboard.labels" -}}
app.kubernetes.io/name: {{ include "health-dashboard.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "health-dashboard.selectorLabels" -}}
app: {{ include "health-dashboard.name" . }}
{{- end }}