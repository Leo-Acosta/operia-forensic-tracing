# Geo Trace Module

Migrates the useful backend logic from `Old_geo-trace-desktop` without the PySide6 desktop UI.

## Scope

- Extract IPs and URLs from text.
- Resolve URLs and handle `.onion` targets safely.
- Geolocate public IPs with the original `ip-api` / `ipinfo` fallback behavior.
- Classify network category and forensic risk.
- Estimate fraud probability, expected cost, and economic impact.
- Persist analyses and targets in the common database.
- Generate Folium HTML maps in shared storage.
- Export PDF through the shared Forensic Legal Report export service.

