# Entrega y dependencias

Fecha: 2026-10-16. Ningún documento sustituye validación de código.

| Tarea | Depende | Aceptación | Estado |
|---|---|---|---|
| P0 diagnóstico y retiro externo | Git/instrucción propietario | baseline, backup/restore, históricos intactos, sin ejecutar motor ajeno | implementado/probado |
| P1 contratos/preservación/ámbito | P0 | bytes/hash, manifiesto, rechazo de rutas, 401/403/404 entre ámbitos | implementado/probado |
| P2 lector iOS y Android | P1/especificación | tres formatos acotados, oráculo manual y negativos | implementado; validación sintética |
| P3 comparadores/reglas/cronología | P2 | fronteras exactas, demo explícita, fechas UTC justificadas y ambiguas excluidas, duplicados enlazados | implementado/probado |
| P4 cola/worker local | P1/P2 | persistencia, claim, cancelación, timeout, restart, cuota y estados separados | implementado/probado: AppContainer y Job Object Windows |
| P5 revisión/UI/JSON/CSV | P3/P4 | revisión append-only, informes estables, ámbito y flujo real | implementado; ver VALIDATION |
| P5 evidencia/custodia/informes/PDF/Word | aislamiento transversal | referencias por caso, doble permiso, snapshot, revisión preservada y exportaciones | implementado; pruebas sintéticas |
| P5 hallazgos/hipotesis/Geo Trace | incorporacion revisada | seleccion explicita, referencias y snapshots, Geo pasivo | implementado; validacion sintetica |
| P6 backup iOS/SQLite/WAL/bugreport completo | especificaciones y muestras autorizadas | lectura contrastada, conservación/copias, formatos/versiones precisos | pendiente; sin muestras reales |
| P6 validación de detección real | conjuntos etiquetados y revisión profesional | tamaño/origen/verdad de referencia documentados | bloqueada por falta de adquisiciones autorizadas |
| P7 IA | integridad + acceso mínimo + autorización de flujos | referencias verificables, no ejecución, separación hechos/hipótesis | pendiente, motor funciona sin IA |

Antes de servicio sensible: cuenta de minimo privilegio del supervisor, firewall
de egreso por proveedor, cuotas fisicas, proteccion de backups y evaluacion del
despliegue completo. AppContainer, memoria/CPU, Job y kill-on-parent-death fueron
verificados localmente; ver [pentest](../LOCAL_PENTEST.md).

Siguiente paso concreto: corregir accesos transversales y validar una adquisición
autorizada por plataforma en entorno aislado, registrando OS, método, hashes,
campos observados, exclusiones y discrepancias contra examen manual. No usar un
dominio sintético como métrica de detección de spyware.

Continuidad E6 del 2026-10-18: [motor 0.2.0](E6_BACKUP_METADATA.md), con dos
lectores de metadatos de backup iOS y validación sintética. La fila P6 anterior
describe el alcance más amplio: Manifest.db/SQLite/WAL, archivos lógicos y
bugreport siguen pendientes. Se conservan el roadmap y las evidencias históricas;
la extracción de metadatos no se presenta como validación de adquisiciones reales.

Siguiente tramo E6: [motor 0.3.0 y lectores SQLite acotados](E6_MANIFEST_SQLITE.md).
Files de Manifest.db y catálogo de tablas/índices están implementados y probados
con datos sintéticos; la fila P6 sigue pendiente para WAL/SHM, archivos lógicos,
otras variantes y adquisiciones reales. La referencia anterior a Manifest.db
pendiente corresponde al estado histórico 0.2.0.
