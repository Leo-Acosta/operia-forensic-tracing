# Modules

## Forensic Legal Report

Path:

```text
operia/legal_report
```

Responsibilities:

- Legal sources
- Legal mappings
- Report review
- Case evaluation
- Presentation generation
- DOCX/PDF/HTML/Markdown export compatibility

Current API prefix:

```text
/api/legal-report
```

## Cybercrime Intelligence Analyst

Path:

```text
operia/cybercrime
```

Responsibilities:

- External forensic tools
- Lab sessions
- CTF events and challenges
- Deepfake analysis records
- IoT records
- Blockchain transactions
- Proof matrix rows

Current API prefix:

```text
/api/cybercrime
```

## Geo Trace

Path:

```text
operia/geo_trace
```

Responsibilities:

- Extract IPs and URLs from text
- Resolve URLs
- Handle `.onion` targets safely
- Geolocate IPs
- Score forensic risk
- Estimate economic impact
- Generate HTML maps
- Export PDF through shared reports

Current API prefix:

```text
/api/geo-trace
```

## Geo Proximity

Path:

```text
operia/geo_proximity
```

Responsibilities:

- Store reference locations
- Compute nearest location
- Record proximity queries
- Export case-linked proximity reports

Current API prefix:

```text
/api/geo-proximity
```

## Dashboard

Path:

```text
operia/dashboard
```

Responsibilities:

- Global metrics
- Cross-module status
- Operational alerts

## Cases

Path:

```text
operia/cases
```

Responsibilities:

- Case creation and lifecycle
- Case participants: physical persons, legal entities, witnesses, victims, harmed parties, suspects, public bodies, digital platforms and other relevant actors
- Technical data
- Findings
- Hypotheses
- Damage items
- Case closure readiness and controlled closure
- Advanced case detail view: participants, evidence, custody, reports, manifests and audit trail
- Controlled edit/delete operations for participants, evidence and custody records

Current API prefix:

```text
/api/cases
```

Operational flow:

1. Create case.
2. Register persons and entities.
3. Upload evidence and calculate hash.
4. Register chain of custody.
5. Analyze IP/URL/cybercrime indicator.
6. Query Argentine legal knowledge.
7. Request local AI assistance.
8. Generate report.
9. Review report.
10. Export PDF.
11. Review operational summary.
12. Close case.

Closure requirements:

- at least one evidence item;
- at least one custody action;
- at least one report;
- reviewed report score/status;
- PDF export manifest.

## Fase Operativa 2 - Advanced Case Management

The frontend includes a professional case detail view under `Detalle del Caso`.

It provides:

- active case overview;
- participants and entities list;
- evidence list with hashes;
- custody action timeline;
- reports and PDF export links;
- export manifests;
- case audit logs;
- edit/delete actions for participants, evidence and custody records.

Closed cases are shown as closed and should be treated as read-only operationally unless a future reopening workflow is implemented.

## Fase Operativa 3 - Professional Forensic Report

Canonical report PDF export now uses `operia/exports/report_exporters.py`.

The professional report includes:

- cover page and case metadata;
- case metrics;
- participants and entities;
- evidence integrity table with hashes;
- chain-of-custody table;
- findings, hypotheses and limitations;
- Argentine legal mapping section;
- generated report content;
- prudent conclusions;
- export annex explaining manifest/hash traceability.

## Fase Operativa 5 - Final Report and Attribution Engine

The final report engine now treats the PDF as a professional forensic-legal document prepared by the analyst/operator.

It provides:

- visible analyst/author attribution instead of platform authorship;
- professional case/report states instead of internal workflow values;
- non-attribution text when no person, group or entity can be technically linked;
- unified Argentine legal framing from the registered legal knowledge library;
- controlled support for registered jurisprudence and doctrine without invented sources;
- attribution assessment based on convergent technical signals;
- separate conclusion templates for attribution and non-attribution scenarios;
- export annex metadata with case id, report version, generation date, author, state and evidence/custody counts;
- PDF filtering of internal assistant/provider details.
