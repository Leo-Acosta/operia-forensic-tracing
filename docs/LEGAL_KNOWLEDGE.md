# Legal Knowledge

`operia/legal_knowledge` is the canonical legal library for OPERIA Forensic Tracing.

Responsibilities:

- store Argentine legal sources, articles, citations, mappings, and evaluations;
- keep source URLs, verification state, and update metadata;
- support structured mappings from case facts to legal hypotheses;
- prevent AI workflows from inventing unsupported legal references.

Current scope:

- `LegalSource`
- `LegalArticle`
- `LegalMapping`
- `LegalCitation`
- `LegalEvaluation`
- `LegalPrecedent`
- `LegalDoctrine`

Fase Operativa 6 adds legal attack profiles for:

- phishing / fraude digital;
- ransomware;
- acceso ilegitimo;
- fraude digital;
- dano informatico;
- filtracion de datos;
- extorsion;
- otros incidentes informaticos.

Each profile defines:

- legal theory;
- required evidence;
- recommended investigative measures;
- principal, connected, complementary and procedural norms;
- applicability to the case;
- probatory limits;
- confidence level.

Fase Operativa 6.1 adds analyst-approved legal mappings:

- every recommended article can be approved or discarded for a concrete case;
- the analyst name, rationale, legal role, applicability and probatory limits are stored;
- approved mappings are included in report legal framing;
- discarded mappings remain auditable but are excluded from report legal framing;
- every decision writes an audit log entry.

Fase Operativa 6.2 adds evidence-linked legal mappings:

- approved legal mappings can be linked to one or more evidence records;
- each link stores the legal element supported, probatory strength, analyst and rationale;
- linked evidence is visible in the legal mapping history;
- linked evidence is included in the final report legal framing;
- every link/unlink operation writes an audit log entry.

Fase Operativa 6.3 to 6.7 adds legal-probatory control:

- article-level checklists define the legal elements that must be supported;
- approved mappings are transformed into a matrix of norm, legal element, evidence, status, strength, contradiction risk and recommended measure;
- missing elements are detected instead of silently treating a norm as proven;
- legal quality control produces a score, risk level, conclusion impact and actionable issues;
- the PDF legal section includes a concise legal-probatory matrix instead of a loose list of references.

Initial seeded coverage:

- Argentine Penal Code article 172;
- Argentine Penal Code article 153 bis;
- Argentine Penal Code article 173 subsection 16;
- Argentine Penal Code article 153;
- Argentine Penal Code article 155;
- Argentine Penal Code article 157 bis;
- Argentine Penal Code article 168;
- Argentine Penal Code articles 183, 184 and 197;
- Argentine Civil and Commercial Code articles 1710, 1716, 1726, 1737 and 1740;
- Budapest Convention references through Law 27.411;
- Personal Data Protection Law 25.326 article 9;
- Personal Data Protection Law 25.326 articles 5, 9, 10 and 11;
- Consumer Protection Law 24.240 articles 4, 5 and 40;
- procedural reference seed for federal criminal evidence workflows.

This seed is a functional starting point, not a substitute for a full legal update pipeline. Every legal output must keep source, article, confidence, and human-review status.

Canonical API:

- `GET /api/legal-knowledge`
- `GET /api/legal-knowledge/sources`
- `POST /api/legal-knowledge/sources`
- `POST /api/legal-knowledge/sources/sync-official`
- `GET /api/legal-knowledge/articles`
- `GET /api/legal-knowledge/articles?q=phishing`
- `POST /api/legal-knowledge/articles/seed`
- `POST /api/legal-knowledge/articles/recommend`
- `GET /api/legal-knowledge/articles/{article_id}/context`
- `GET /api/legal-knowledge/articles/{article_id}/checklist`
- `GET /api/legal-knowledge/attack-types`
- `GET /api/legal-knowledge/attack-types/{attack_type}`
- `POST /api/legal-knowledge/sources/verify`
- `POST /api/legal-knowledge/sources/verify-url`
- `POST /api/legal-knowledge/mappings`
- `POST /api/legal-knowledge/mappings/decision`
- `POST /api/legal-knowledge/mappings/evidence`
- `GET /api/legal-knowledge/case/{case_id}/mapping-evidence`
- `GET /api/legal-knowledge/case/{case_id}/probatory-matrix`
- `GET /api/legal-knowledge/case/{case_id}/quality-control`
- `DELETE /api/legal-knowledge/mappings/evidence/{link_id}`
- `GET /api/legal-knowledge/case/{case_id}/mappings`
- `POST /api/legal-knowledge/precedents`
- `GET /api/legal-knowledge/precedents`
- `POST /api/legal-knowledge/doctrine`
- `GET /api/legal-knowledge/doctrine`

Update and verification policy:

- automatic recommendations are preliminary;
- source URLs must point to official or manually approved references;
- verification checks only URL reachability and does not certify legal interpretation;
- jurisprudence and doctrine are shown only when registered and verified;
- unregistered jurisprudence, doctrine, norms or articles must not be generated;
- every legal recommendation must remain subject to human review.
