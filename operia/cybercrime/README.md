# Cybercrime Intelligence Analyst Module

This module migrates the operational parts of `Old_Operia Cybercrime Intelligence Analyst` into OPERIA Forensic Tracing.

## Integration Rules

- Shared cases come from the common `cases` table migrated with the Forensic Legal Report module.
- Shared evidence comes from the common `evidence` table.
- PDF generation delegates to the Forensic Legal Report export service.
- Database access uses `operia.core.database`.
- Configuration and storage come from `operia.core.config`.
- Hashing remains in `operia.shared.hashing`; this module does not define a duplicate hash service.

## Migrated Scope

- External tools.
- Forensic lab sessions.
- CTF events, challenges, and analysis steps.
- Deepfake analysis records.
- IoT/device records.
- Blockchain Investigation Lab transaction records.
- Proof matrix rows.
- Cybercrime dashboard metrics.
- PDF export through the shared report/export pipeline.

## Not Migrated Yet

- The old Cybercrime React screen has not been merged into the new web UI.
- CTF file attachment upload/writeup export is not migrated yet.
- The old bridge to the separate Forensic Legal Report API was removed because both modules now run in the same platform.
