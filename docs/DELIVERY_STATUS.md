# Matriz de continuidad del prompt maestro

Actualización: 2026-10-19. Esta matriz resume el estado actual; las auditorías
anteriores permanecen como registros históricos y no se reescriben.

| Etapa | Estado | Evidencia y límite |
| --- | --- | --- |
| E0/E1: diagnóstico, respaldo y secretos | Implementado y probado localmente | [Diagnóstico y restauración](E0_E1_SECURITY_BASELINE.md); no acredita operación productiva |
| E2: custodia | Implementado y probado localmente | [Append-only y rectificaciones](CUSTODY_APPEND_ONLY.md); no equivale a WORM externo |
| E3: permisos por expediente | Implementado y probado localmente | [Concesiones y revocaciones](CASE_ACCESS_CONTROL.md); roles y capacidades son límites independientes |
| E4: experiencia premium | Implementado con validación sintética | [Migración de módulos](E4_LEGACY_MODULES.md); falta validación física de tecnologías de asistencia |
| E4: NVDA, VoiceOver y TalkBack reales | Pendiente | [Matriz y criterios](ASSISTIVE_ACCESSIBILITY.md); las comprobaciones DOM/axe no son ejecución de esos lectores |
| E5: laboratorio estático | CPython AST real, trabajos, revisión, interfaz premium e incorporación a hallazgos e informes implementados localmente | [Interfaz e incorporación revisada](STATIC_LAB_INTERFACE.md); alcance Python; otros proveedores pendientes |
| E6: ampliación del motor propio | Cierre técnico acotado 0.7.0: 13 lectores / 11 formatos, regresión completa y demostración de perfil público externo | [Acta de cierre](forensic_engine/E6_CLOSURE_0_7_0.md), [matriz final](forensic_engine/COVERAGE_MATRIX.md); adquisiciones de dispositivos pendientes por falta de muestras confirmada por el usuario |
| E7: operación productiva | Refuerzo parcial implementado; aceptación productiva pendiente | [Privilegios, secretos y recuperación cifrada](E7_PRODUCTION_HARDENING.md); faltan identidad dedicada, recuperación independiente y despliegue real |
| E8: cierre de versión/SaaS | Pendiente | Requiere alcance final, regresión, operación y pendientes resueltos; no se declara terminado |

E5 incorpora selección explícita de observaciones de la última revisión aceptada,
hallazgos e informes borrador nuevos con procedencia preservada. Nuevos proveedores
(APK o ejecutables) requieren procedencia, licencia, revisión y perfil de aislamiento
propios, con validación benigna antes de habilitarse. La validación física E4
permanece pendiente y puede realizarse sin reducir permisos ni aislamiento.

El contador de horas mantiene su fuente independiente en [work_hours.json](work_hours.json).
No se convierte duración de pruebas o trabajo de IA en horas humanas.
