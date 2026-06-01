# Rubrics

`operia/rubrics` is the rubric scoring engine for challenge-ready reports.

Implemented rubric:

- `Written Legal Evidence Report 2026`
- key: `written_legal_evidence_report_2026`
- maximum score: 20 weighted points

Sections:

- A. Technical Approach & Investigative Techniques Used: 3%.
- B. Evidence Identification, Categorization & Handling: 3%.
- C. Legal Authority & Investigative Requests: 4%.
- D. Summary Analysis of Evidence & Investigative Findings: 10%.
- Final Investigative Summary is evaluated inside section D.

Each section returns:

- weight;
- criteria;
- expected components;
- minimum fields;
- status: `incompleto`, `parcial` or `completo`;
- estimated score;
- missing items;
- recommendations.

The automatic evaluator checks:

- evidence loaded;
- SHA-256 hash registered;
- chain of custody;
- tools, techniques or commands used;
- legal mappings approved from the registered legal knowledge library;
- legal-probatory matrix and evidence links;
- technical findings;
- conclusion and report text;
- legal requests, authorizations or procedural next steps;
- annex availability;
- report review score.

API:

- `GET /api/rubrics`
- `GET /api/rubrics/report-2026`
- `GET /api/rubrics/case/{case_id}/score`
- `POST /api/rubrics/case/{case_id}/evaluate`

Integration:

- The frontend shows the rubric panel inside `Informes` as `Cumplimiento de Rúbrica`.
- The report/PDF includes `Cumplimiento de rúbrica del informe` only when a rubric evaluation exists for the case.
- The rubric does not invent legal content; it only evaluates whether registered evidence, report content and legal mappings are present and connected.
