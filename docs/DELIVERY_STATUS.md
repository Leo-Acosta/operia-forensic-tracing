# Matriz de continuidad del prompt maestro

Actualización: 2026-10-18. Esta matriz resume el estado actual; las auditorías
anteriores permanecen como registros históricos y no se reescriben.

| Etapa | Estado | Evidencia y límite |
| --- | --- | --- |
| E0/E1: diagnóstico, respaldo y secretos | Implementado y probado localmente | [Diagnóstico y restauración](E0_E1_SECURITY_BASELINE.md); no acredita operación productiva |
| E2: custodia | Implementado y probado localmente | [Append-only y rectificaciones](CUSTODY_APPEND_ONLY.md); no equivale a WORM externo |
| E3: permisos por expediente | Implementado y probado localmente | [Concesiones y revocaciones](CASE_ACCESS_CONTROL.md); roles y capacidades son límites independientes |
| E4: experiencia premium | Implementado con validación sintética | [Migración de módulos](E4_LEGACY_MODULES.md); falta validación física de tecnologías de asistencia |
| E4: NVDA, VoiceOver y TalkBack reales | Pendiente | [Matriz y criterios](ASSISTIVE_ACCESSIBILITY.md); las comprobaciones DOM/axe no son ejecución de esos lectores |
| E5: laboratorio estático | Parcial, importación probada con muestra benigna sintética | [Contrato y uso](STATIC_LAB.md); ningún proveedor ejecutado o validado |
| E6: ampliación del motor propio | Pendiente de esta etapa | El motor actual conserva su [cobertura documentada](forensic_engine/VALIDATION.md); no se agregaron lectores ni adquisiciones reales en E5 |
| E7: operación productiva | Pendiente de aceptación completa | Existen [capas de seguridad](SECURITY_LAYERS.md); faltan los requisitos productivos del prompt maestro |
| E8: cierre de versión/SaaS | Pendiente | Requiere alcance final, regresión, operación y pendientes resueltos; no se declara terminado |

La siguiente continuidad es completar E5: seleccionar un proveedor estático,
verificar procedencia/licencia/revisión y validar su perfil aislado con muestra
benigna; incorporar trabajos, revisión versionada y la interfaz del laboratorio.
No habilitar ejecución externa antes de cumplir esos controles. La validación
física E4 puede realizarse en paralelo, sin reducir permisos ni aislamiento.

El contador de horas mantiene su fuente independiente en [work_hours.json](work_hours.json).
No se convierte duración de pruebas o trabajo de IA en horas humanas.
