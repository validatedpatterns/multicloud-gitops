{{- define "ack-s3-controller.bucket_policy" -}}
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":"*","Action":"s3:GetObject","Resource":"arn:aws:s3:::{{ .Values.global.s3.bucketName }}/*"}]}
{{- end -}}

{{/* Example inline policy that can be included in chart 
{{- define "ack-s3-controller.custom_bucket_policy" -}}
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":"*","Action":"s3:GetObject","Resource":"arn:aws:s3:::{{ .Values.s3.bucketName }}/*"}]}
{{- end -}}
*/}}
