# Task 8.8 Report v2 Report

`GET /api/v1/analyses/{analysis_id}/report` now reads SQLite as source of truth and obtains only the validated derivative thumbnail through storage abstraction. It includes analysis ID, date, patient/anonymous metadata, sanitized filename, thumbnail, class/probabilities, model/KB versions, latency, provenance sources, disclaimer, logo and team information.

The report embeds local assets as data URIs, makes no network request, handles a missing thumbnail without crashing and provides A4 print CSS. Legacy POST preview remains deprecated for compatibility; the new UI exports only by `analysis_id`.
