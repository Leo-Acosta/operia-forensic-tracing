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

Fase CTF 1 completes the Argentine legal library for the Cybercrime Investigation Challenge 2026 rubric. The module keeps every recommendation tied to registered sources only, with article, summarized text, objective elements, subjective elements, evidence needed, probatory limits, incident relation and human-review status.

CTF legal incident profiles:

- phishing / fraude digital;
- deepfake / autenticación de medios;
- blockchain / criptoactivos;
- IoT / dispositivos conectados;
- ransomware / extorsión;
- filtración de datos;
- acceso ilegítimo;
- falsedad documental digital;
- daño informático;
- otros incidentes informáticos.

Each profile defines:

- legal theory;
- required evidence;
- recommended investigative measures;
- principal, connected, complementary and procedural norms;
- applicability to the case;
- probatory limits;
- confidence level.
- explicit warning not to attribute authorship without sufficient evidence.

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

Fase Operativa 6.8 turns the matrix into an editable decision tool:

- analysts can edit a legal-evidence link status, strength, contradiction risk, missing evidence and recommended measure;
- analysts can unlink evidence from a legal article without deleting the evidence record;
- analysts can remove an approved article from the active legal framing and reactivate discarded articles;
- the frontend shows a legal sufficiency traffic light based on quality-control scoring;
- visible legal-library labels are normalized to professional Spanish.

Initial seeded coverage:

- Argentine Penal Code article 172;
- Argentine Penal Code article 153 bis;
- Argentine Penal Code article 173 subsection 16;
- Argentine Penal Code article 153;
- Argentine Penal Code article 155;
- Argentine Penal Code article 157 bis;
- Argentine Penal Code article 168;
- Argentine Penal Code article 169;
- Argentine Penal Code article 149 bis;
- Argentine Penal Code articles 128 and 131 as sensitive norms with handling warnings;
- Argentine Penal Code articles 293 and 296;
- Argentine Penal Code articles 109 and 110;
- Argentine Penal Code articles 183, 184 and 197;
- Argentine Civil and Commercial Code articles 51 to 53 for image, voice, identity and dignity;
- Argentine Civil and Commercial Code articles 1710, 1716, 1726, 1737 and 1740;
- Law 11.723 on intellectual property;
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
- `PUT /api/legal-knowledge/mappings/evidence/{link_id}`
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
- CP articles 128 and 131 are shown only as sensitive references with minimal-preservation warnings; the frontend must not expose or request sensitive material.

Deepfake / media-authentication integration:

- `POST /api/cybercrime/deepfake/{analysis_id}/apply-legal` applies only articles already registered in this library;
- CCCN articles 51 to 53 are the main civil reference for image, voice, identity and dignity;
- Law 11.723 articles 1 and 71 are applied only when protected works or intellectual-property use is relevant;
- CP articles 172, 293, 296, 109 and 110 are applied as connected norms only when fraud, document falsity or honor-affectation facts are present;
- Law 25.326 articles 5 and 9 are applied when personal data processing, consent or security may be involved;
- the mapping keeps probatory limits and warns that media analysis does not prove authorship or conclusively prove deepfake status by itself.
