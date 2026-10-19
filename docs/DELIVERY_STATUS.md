# Matriz de continuidad del prompt maestro

ActualizaciÃƒÂ³n: 2026-10-19. Esta matriz resume el estado actual; las auditorÃƒÂ­as
anteriores permanecen como registros histÃƒÂ³ricos y no se reescriben.

| Etapa | Estado | Evidencia y lÃƒÂ­mite |
| --- | --- | --- |
| E0/E1: diagnÃƒÂ³stico, respaldo y secretos | Implementado y probado localmente | [DiagnÃƒÂ³stico y restauraciÃƒÂ³n](E0_E1_SECURITY_BASELINE.md); no acredita operaciÃƒÂ³n productiva |
| E2: custodia | Implementado y probado localmente | [Append-only y rectificaciones](CUSTODY_APPEND_ONLY.md); no equivale a WORM externo |
| E3: permisos por expediente | Implementado y probado localmente | [Concesiones y revocaciones](CASE_ACCESS_CONTROL.md); roles y capacidades son lÃƒÂ­mites independientes |
| E4: experiencia premium | Implementado con validaciÃƒÂ³n sintÃƒÂ©tica | [MigraciÃƒÂ³n de mÃƒÂ³dulos](E4_LEGACY_MODULES.md); falta validaciÃƒÂ³n fÃƒÂ­sica de tecnologÃƒÂ­as de asistencia |
| E4: NVDA, VoiceOver y TalkBack reales | Pendiente | [Matriz y criterios](ASSISTIVE_ACCESSIBILITY.md); las comprobaciones DOM/axe no son ejecuciÃƒÂ³n de esos lectores |
| E5: laboratorio estÃƒÂ¡tico | CPython AST real, trabajos, revisiÃƒÂ³n, interfaz premium e incorporaciÃƒÂ³n a hallazgos e informes implementados localmente | [Interfaz e incorporaciÃƒÂ³n revisada](STATIC_LAB_INTERFACE.md); alcance Python; otros proveedores pendientes |
| E6: ampliaciÃƒÂ³n del motor propio | Cierre tÃƒÂ©cnico acotado 0.7.0: 13 lectores / 11 formatos, regresiÃƒÂ³n completa y demostraciÃƒÂ³n de perfil pÃƒÂºblico externo | [Acta de cierre](forensic_engine/E6_CLOSURE_0_7_0.md), [matriz final](forensic_engine/COVERAGE_MATRIX.md); adquisiciones de dispositivos pendientes por falta de muestras confirmada por el usuario |
| E7: operación productiva | Rotación DPAPI y recuperación SCM aceptadas localmente con datos sintéticos; preparación productiva aún parcial | [Auditoría DPAPI y recuperación](audits/e7-dpapi-recovery-20261019.json): mismo canario preservado, v2 histórico recuperado, rollback de credenciales/actualizaciones y restauración cifrada probados. Servicio manual/detenido, cuenta deshabilitada, sin pendientes. TLS y recuperación independiente aún pendientes |
| E8: cierre de versiÃƒÂ³n/SaaS | Pendiente | Requiere alcance final, regresiÃƒÂ³n, operaciÃƒÂ³n y pendientes resueltos; no se declara terminado |

E5 incorpora selecciÃƒÂ³n explÃƒÂ­cita de observaciones de la ÃƒÂºltima revisiÃƒÂ³n aceptada,
hallazgos e informes borrador nuevos con procedencia preservada. Nuevos proveedores
(APK o ejecutables) requieren procedencia, licencia, revisiÃƒÂ³n y perfil de aislamiento
propios, con validaciÃƒÂ³n benigna antes de habilitarse. La validaciÃƒÂ³n fÃƒÂ­sica E4
permanece pendiente y puede realizarse sin reducir permisos ni aislamiento.

El contador de horas mantiene su fuente independiente en [work_hours.json](work_hours.json).
No se convierte duraciÃƒÂ³n de pruebas o trabajo de IA en horas humanas.
