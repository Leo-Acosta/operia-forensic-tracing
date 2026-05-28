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
