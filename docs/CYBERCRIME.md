# Cybercrime Module

The cybercrime workspace includes controlled indicator analysis, forensic lab sessions, proof-matrix rows, Deepfake / Medios and Blockchain Forensics.

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

## Blockchain Forensics

Blockchain Forensics registers cryptoasset evidence without using external APIs by default. OPERIA does not query explorers automatically; an explorer URL is stored only when the analyst provides it manually.

Operational fields:

- case and optional evidence link;
- source wallet and destination wallet;
- transaction hash;
- blockchain network;
- token, amount and approximate value;
- date/time;
- manually supplied explorer URL;
- route hypothesis;
- wallet classification;
- evidence hash;
- tool used;
- limitations, recommended measures and analyst name.

Wallet classification:

- `wallet personal no verificada`;
- `exchange`;
- `mixer`;
- `bridge`;
- `contrato inteligente`;
- `wallet receptora`;
- `wallet intermediaria`;
- `desconocido`.

Canonical API:

- `POST /api/cybercrime/blockchain`
- `GET /api/cybercrime/blockchain/case/{case_id}`
- `POST /api/cybercrime/blockchain/{transaction_id}/finding`
- `POST /api/cybercrime/blockchain/{transaction_id}/apply-legal`

Recommended measures:

- preserve explorer capture;
- register date/time of consultation;
- store URL if manually used;
- identify exchange or platform when applicable;
- request platform information through legal process;
- correlate with communications, payments, accounts and IPs;
- avoid personal attribution based only on a wallet.

Legal integration is limited to registered legal-library articles. The current blockchain flow maps CP 172, CP 173 subsection 16, CP 168, CP 169 and Law 25.326 articles 5/9 only when the facts entered by the analyst support those links. Other norms must exist in the legal library before they can be applied.

## IoT Forensics

IoT Forensics registers connected devices inside a case without executing real scans automatically and without using the external network by default. The module avoids dangerous command recommendations; active probing must be handled outside OPERIA with authorization, preservation and methodology.

Operational fields:

- case and optional evidence link;
- device type;
- manufacturer, model and firmware;
- internal IP, external IP and MAC;
- observed or declared open ports;
- known vulnerabilities;
- available logs;
- evidence hash;
- checklist;
- tool or methodology used;
- limitations and recommended measures.

Minimum checklist:

- physical identification;
- photo or capture;
- evidence hash;
- firmware;
- configuration;
- logs;
- ports;
- default credentials;
- network connection;
- timeline;
- state preservation;
- alteration risk.

Canonical API:

- `POST /api/cybercrime/iot`
- `GET /api/cybercrime/iot/case/{case_id}`
- `POST /api/cybercrime/iot/{device_id}/finding`
- `POST /api/cybercrime/iot/{device_id}/apply-legal`

Legal integration:

- CP article 153 bis when unauthorized access is supported by facts;
- CP article 183 when data, programs or systems were damaged or altered;
- CP article 184 when public systems, services or critical infrastructure are affected;
- CP article 197 when communications were interrupted or obstructed;
- Law 25.326 articles 5 and 9 when personal data is involved.

Required caution:

- IP, MAC, hostname, firmware or open port does not identify a person by itself;
- preserve device state before manipulation;
- correlate with logs, authorization records, network evidence, accounts and timeline.
