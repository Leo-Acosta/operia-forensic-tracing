# Operación local del motor propio

1. Instalar dependencias existentes de OPERIA en .venv e iniciar API/frontend según
   README. No instalar otro motor. Para pruebas, requirements-dev.txt.
2. Iniciar un worker separado desde raíz del repositorio:
   `.\.venv\Scripts\python.exe -m operia.forensic_jobs.worker`.
   `--once` procesa como máximo un pendiente y termina. Si no está iniciado, los
   trabajos siguen pendientes: la UI no inventa progreso ni ejecuta en la API.
3. Iniciar sesión, elegir caso propio y abrir Forense móvil. Registrar dispositivo
   con datos declarados. Preservar una fuente autorizada, elegir formato soportado
   y documentar alcance/procedencia/fecha/método/autorización/retención/restricciones.
4. Opcionalmente registrar indicadores JSON según DETECTION_RULES.md. Identificar
   fuente/condiciones/versión/límites. No hay feeds automáticos.
5. Crear examen sobre una adquisición. Reglas de demostración son opcionales y
   sintéticas. El worker produce observaciones, cobertura, alertas y tiempos
   normalizables, con hashes y localizadores. Cancelar/reintentar cuando corresponda.
6. Revisar IDs de respaldo y agregar revisión. No atribuir personas por una URL,
   IP, perfil o nombre de paquete. Confirmación de compromiso requiere un flujo de
   corroboración adicional no implementado. No usar el número de alertas como certeza.
7. Exportar informe JSON versionado o CSV temporal. El JSON conserva revisiones,
   configuración, hashes, resultado canónico y bytes exactos de indicadores en base64.
   El CSV conserva columnas temporales y neutraliza fórmulas; su relación con revisión
   y hash se registra en ExportRecord. Los informes anteriores no cambian.
8. Consultar históricos externos en su sección separada y descargar sus originales
   e informes previos. No se aceptan nuevos imports mediante el flujo retirado.

Configuración: OPERIA_MOBILE_JOB_TIMEOUT_SECONDS (30),
OPERIA_MOBILE_STORAGE_QUOTA_BYTES (134217728), OPERIA_DATABASE_URL y STORAGE_DIR.
Usar el mismo almacenamiento/base para API y worker. La cola local admite un worker
por almacenamiento; no es un servicio distribuido. Reinicio marca activos interrumpidos.

CLI independiente (solo stdlib, sin API/BD):
```powershell
python -S -m operia.forensic_engine tests/fixtures/native_mobile/profile.plist --platform ios --format apple-profile-plist --output storage/temp/profile-native.json --demo-rules
```
No sobrescribe salida. Fixture sintético, no instalar en un dispositivo. Los nombres
de archivo recibidos por la API no admiten rutas ni caracteres especiales.

Límites: no adquiere dispositivos, no descifra, no interpreta backups completos,
SQLite/WAL, CMS ni archivos comprimidos. Geo Trace e IA no son conectores del motor. PDF/Word disponibles mediante
la incorporación revisada al módulo de informes. No modifica dispositivos,
abre enlaces o envía datos a servicios externos. Contención/recuperación son separadas.

## Incorporar al expediente

Con una revisión profesional guardada, pulsar «Incorporar revisión a evidencia,
custodia e informe». Requiere permisos de escritura de evidencia e informes.
La pantalla conserva los IDs de evidencia/informe y permite descargar la
instantánea JSON con hash. Repetir la misma revisión devuelve el mismo vínculo.
Los módulos Evidencia e Informes permiten consultar el original y exportar el
informe técnico en PDF, Word y Markdown con los mecanismos existentes.

La incorporación es un registro preservado: no admite edición, borrado ni
transición a informe final por esas rutas. Corregir mediante una nueva revisión
del examen y una nueva incorporación. La custodia registra recepción/incorporación
en OPERIA y no inventa actos anteriores. Los históricos externos mantienen su
origen, bytes y descargas. Un caso con datos móviles se conserva, no se elimina.

## Hallazgos, hipotesis y Geo Trace

Despues de incorporar evidencia, completar la seccion 7 del motor: elegir la
incorporacion, seleccionar IDs de artefactos respaldados por esa revision y redactar
una hipotesis y los hechos que necesitan corroboracion. Se requieren evidence:write
y cases:write. Geo Trace es opcional y pasivo: solo referencias URL contenidas en
los artefactos. No abre enlaces ni sitúa al dispositivo o a una persona.

El resultado entrega IDs de hallazgo, hipotesis y analisis Geo, y descarga JSON con
hash. Repetir exactamente la solicitud devuelve los mismos registros. Para corregir,
crear otra proyeccion; no editar los registros preservados. La revision profesional
no equivale a confirmacion tecnica. Los historicos e informes anteriores no cambian.

Las consultas de red y la IA local estan apagadas por defecto y la ejecucion shell
fue retirada. Ver [capas de seguridad](../SECURITY_LAYERS.md) para configuracion,
limites y el contrato para futuros conectores.
