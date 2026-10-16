# Entrega y dependencias

Fecha: 2026-10-16. Ningún documento sustituye validación de código.

| Tarea | Depende | Aceptación | Estado |
|---|---|---|---|
| P0 diagnóstico y retiro externo | Git/instrucción propietario | baseline, backup/restore, históricos intactos, sin ejecutar motor ajeno | implementado/probado |
| P1 contratos/preservación/ámbito | P0 | bytes/hash, manifiesto, rechazo de rutas, 401/403/404 entre ámbitos | implementado/probado |
| P2 lector iOS y Android | P1/especificación | tres formatos acotados, oráculo manual y negativos | implementado; validación sintética |
| P3 comparadores/reglas/cronología | P2 | fronteras exactas, demo explícita, fechas UTC justificadas y ambiguas excluidas, duplicados enlazados | implementado/probado |
| P4 cola/worker local | P1/P2 | persistencia, claim, cancelación, timeout, restart, cuota y estados separados | implementado/probado en Windows; sandbox SO pendiente |
| P5 revisión/UI/JSON/CSV | P3/P4 | revisión append-only, informes estables, ámbito y flujo real | implementado; ver VALIDATION |
| P5 evidencia/custodia/informes/PDF/Word | aislamiento transversal | referencias por caso, doble permiso, snapshot, revisión preservada y exportaciones | implementado; pruebas sintéticas |
| P5 hallazgos/Geo Trace | contrato específico | conectores acotados y revisión de datos | pendiente |
| P6 backup iOS/SQLite/WAL/bugreport completo | especificaciones y muestras autorizadas | lectura contrastada, conservación/copias, formatos/versiones precisos | pendiente; sin muestras reales |
| P6 validación de detección real | conjuntos etiquetados y revisión profesional | tamaño/origen/verdad de referencia documentados | bloqueada por falta de adquisiciones autorizadas |
| P7 IA | integridad + acceso mínimo + autorización de flujos | referencias verificables, no ejecución, separación hechos/hipótesis | pendiente, motor funciona sin IA |

Antes de servicio sensible: cuenta de mínimo privilegio, aislamiento efectivo de
red/archivos/memoria, kill-on-parent-death, cuotas físicas, protección de backups y
auditoría de identidad/aislamiento de toda la plataforma. No se declaran implementados.

Siguiente paso concreto: corregir accesos transversales y validar una adquisición
autorizada por plataforma en entorno aislado, registrando OS, método, hashes,
campos observados, exclusiones y discrepancias contra examen manual. No usar un
dominio sintético como métrica de detección de spyware.
