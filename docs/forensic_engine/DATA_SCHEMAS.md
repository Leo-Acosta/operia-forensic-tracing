# Esquemas y persistencia

`operia.forensic/1` usa JSON canónico UTF-8, claves ordenadas, sin NaN/Infinity.
`operia.mobile-report/1` es un snapshot con metadatos variables fuera del resultado
determinista. SQLite local es el backend admitido para esta entrega.

| Entidad / tabla | Vínculo y contenido |
|---|---|
| Device / mobile_devices | caso y organización; etiqueta, plataforma e identificador declarados. No se inventan datos técnicos observados |
| Acquisition / native_mobile_acquisitions | caso/org/device/operador, método/autorización/procedencia, fecha original sin asumir zona, alcance, retención/restricciones, OS declarado, formato, bytes BLOB y SHA-256 |
| ExaminationJob / native_mobile_jobs | adquisición/caso/org/creador, configuración exacta/hash, indicadores, estado, claim, heartbeat/inicio/fin, cancelación, error y resultado/hash |
| JobEvent / native_mobile_job_events | historial de estados/razones y fecha; ámbito heredado del job |
| IndicatorSet / native_mobile_indicator_sets | caso/org, fuente/condiciones/versión, bytes exactos/hash y fecha de incorporación; publicación/vigencia no verificadas |
| ReviewRevision / native_mobile_reviews | job, hash revisado, revisor real/fecha y contenido versionado por filas acumulativas |
| ExportRecord / native_mobile_exports | job/revisión/formato, creador/fecha, bytes invariables y hash |

ArtifactRecord: ID derivado de hash fuente + localizador + lector; fuente/hash,
lector/versión, tipo, campos originales interpretados, normalizados, tiempo y
duplicate_of. Cada registro hereda caso/org/adquisición/ejecución del job que lo
contiene. Los IDs de contenido no conceden acceso: toda consulta usa el ámbito.

Observation referencia artefactos y separa extracción de interpretación. Alert
contiene regla/versión, indicador/conjunto/hash cuando corresponde, artefactos,
gravedad informativa, explicación y estado pendiente. Gravedad no es confianza.
TimelineEvent: referencia, texto/valor temporal original, formato/unidad, zona,
UTC normalizado, precisión e incertidumbre. No mezcla fecha de adquisición con evento.
CoverageReport mantiene estados por fuente, exclusiones, avisos y límites.

ReviewRevision registra conclusión, IDs válidos, fundamentos, alternativas/
contradicciones, límites y evaluaciones separadas de actividad, cronología y
atribución. Justificación de cobertura obligatoria. Confirmación de compromiso
no disponible sin corroboración independiente. Ausencia de indicios exige datos,
indicadores registrados (DEMO sola no basta), reglas aplicadas, cero alertas, cero
exclusiones y justificación expresa del alcance.

No hay API de modificación/borrado de originales, conjuntos, revisiones o exports.
Eso no equivale a almacenamiento inmutable frente a un administrador de la base.


EvidenceIntegration enlaza organización/caso, examen, revisión, evidencia original,
acto de custodia, informe y actor/fecha de incorporación. Conserva snapshot_bytes y
snapshot_sha256; review_id es único. El snapshot usa operia.evidence-integration/1,
con adquisición/metadatos, resultado completo y revisión seleccionada. Su descarga
verifica SHA-256. La evidencia canónica referencia el original BLOB por el vínculo,
sin ruta recibida del usuario ni duplicación de la fuente. El informe y su primera
versión conservan sus hashes; las correcciones se incorporan como otro registro.
