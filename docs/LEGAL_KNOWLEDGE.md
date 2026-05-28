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
- `POST /api/legal-knowledge/sources/verify`
- `POST /api/legal-knowledge/sources/verify-url`
- `POST /api/legal-knowledge/mappings`
- `GET /api/legal-knowledge/case/{case_id}/mappings`

Update and verification policy:

- automatic recommendations are preliminary;
- source URLs must point to official or manually approved references;
- verification checks only URL reachability and does not certify legal interpretation;
- every legal recommendation must remain subject to human review.
