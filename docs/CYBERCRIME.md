# Cybercrime Module

The cybercrime workspace includes controlled indicator analysis, forensic lab sessions, proof-matrix rows and the Deepfake / Medios lab.

## Deepfake / Medios

Deepfake Lab registers preliminary media-authentication work for image, video, audio, document and screenshot evidence. It does not call external APIs by default and it does not assert that a file is a deepfake, authentic or attributable to a person without additional evidence.

Operational fields:

- case and optional evidence link;
- media type;
- source or publication origin;
- evidence hash;
- metadata summary;
- authenticity checklist;
- tool or technique used;
- findings, limitations and analyst name;
- preliminary classification: `auténtico preliminar`, `manipulado probable`, `indicios de edición`, `no concluyente` or `requiere pericia especializada`.

Minimum checklist:

- file origin;
- original preservation;
- hash;
- EXIF/media metadata;
- compression;
- visual inconsistencies;
- audio inconsistencies;
- lip synchronization;
- frame-by-frame analysis;
- comparison with known source;
- publication traceability;
- external tool used;
- limitations.

Canonical API:

- `POST /api/cybercrime/deepfake`
- `GET /api/cybercrime/deepfake/case/{case_id}`
- `POST /api/cybercrime/deepfake/{analysis_id}/finding`
- `POST /api/cybercrime/deepfake/{analysis_id}/apply-legal`

The generated finding uses cautious language and records the analysis as support for the final report. The legal application endpoint maps only registered legal-library articles and keeps human review required.

Report integration:

- the final markdown report includes `Autenticación de medios y análisis deepfake` when a case has analyses;
- the PDF export includes the same material in a dedicated section;
- both outputs include tools, evidence/hash, findings, limitations and a prudence note.

Required caution:

- a detector, metadata inconsistency, visual artifact or platform trace is not enough to prove authorship;
- classification is preliminary and must be corroborated with preserved originals, expert review and independent sources.
