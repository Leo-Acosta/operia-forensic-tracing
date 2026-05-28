# Geo Proximity Module

Migrates `Old_geo-apple-demo` into OPERIA Forensic Tracing as a generic nearest-location service.

## Scope

- Stores reusable reference locations in the common database.
- Seeds the original Apple Store demo locations.
- Computes nearest reference location with the Haversine formula.
- Records proximity queries and optional `case_id`.
- Exports case-linked queries to PDF through the shared report/export pipeline.

