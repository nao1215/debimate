{{- $year := path.Base (path.Dir (strings.TrimSuffix "/" .File.Dir)) -}}
{{- $date := printf "%s-%s" $year .File.ContentBaseName -}}
---
title: "{{ replace $date "-" "/" }}週"
date: {{ $date }}T00:00:00+09:00
---

