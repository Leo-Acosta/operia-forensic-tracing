# E0 y E1 — diagnóstico, preservación y configuración segura

Fecha: 2026-10-17. Punto de partida verificado: `92cea60`, rama
`feature/operia-native-mobile-engine`, sin cambios pendientes al iniciar.
El remoto configurado coincide con el repositorio informado; no se consultó ni
publicó su estado remoto. No se encontraron AGENTS.md en los ancestros locales.

## Alcance y diagnóstico E0

| Capacidad | Estado verificado y límite |
|---|---|
| Casos, evidencia, informes y exportaciones | Implementados; regresión con SQLite temporal y datos sintéticos |
| Motor móvil propio | Lectores de perfil iOS, inventario Android y logcat epoch; sin adquisición real validada |
| Integraciones del motor | Evidencia/custodia/informes, hallazgos/hipótesis/Geo Trace implementados; pruebas sintéticas |
| Workers y conectores | Backend Windows AppContainer/Job; sin fallback ni excepción de loopback; regresión local |
| IA local | Pasarela implementada; prueba real previa con Ollama y datos sintéticos documentada en OLLAMA_LOCAL_VALIDATION.md; no se repitió inferencia en esta etapa |
| Configuración y diagnóstico | E1 exige administrador y responde metadatos permitidos; sin URL de conexión, secretos o rutas internas |
| Custodia ordinaria | E2 pendiente: todavía admite edición/eliminación; protecciones especiales del motor no cubren todo el historial |
| Acceso individual a expedientes | E3 pendiente; aislamiento organizacional existente no equivale a ACL por expediente |
| Frontend premium | E4 pendiente; frontend actual compilable, sin shadcn/ui incorporado en esta etapa |
| Laboratorio de ingeniería inversa | E5 pendiente; REA no instalado ni ejecutado |
| Cobertura forense ampliada | E6 pendiente; adquisiciones autorizadas y examen de referencia son requisitos externos |
| Operación productiva | E7 pendiente: cuenta dedicada, firewall, recuperación programada, MFA, PostgreSQL/multiinstancia, Docker validado y observabilidad |

La línea base focalizada anterior a los cambios aprobó 50 pruebas de identidad,
seguridad e ingreso HTTP, con cuatro advertencias de deprecación, en 29,75 s.
El diagnóstico es de código y pruebas locales; no certifica un despliegue productivo.

## Preservación y recuperación

Respaldo SQLite creado con la API online de SQLite, sin copiar directamente una
base abierta: `storage/temp/pre-e0-e1-20261017.db`, con manifiesto SHA-256.
Además, un conjunto nuevo conserva evidencia, uploads, exports, maps, memory_vault
y los archivos de configuración/clave que existían al inicio. Son 116 archivos,
7.551.224 bytes, además de SQLite y su manifiesto. No se imprimieron contenidos.

Ubicaciones privadas, ignoradas por Git:

- `storage/temp/e0-e1-data-backup-20261017/`
- `storage/temp/e0-e1-data-restore-20261017/`

La restauración usa destinos nuevos y compara SHA-256 de cada archivo. El
manifiesto registra la inclusión exacta de archivos, sin sustituir sus bytes.
Se rechazaron enlaces/reparse points. Las copias se restringieron por ACL al
usuario actual, SYSTEM y administradores; no se cambiaron ACL de originales.
No se añadieron claves ni archivos .env al repositorio. Las copias no están
cifradas ni fuera del equipo: no constituyen recuperación ante pérdida del host.

Se excluyen runtimes derivados, temporales, ejecuciones de prueba y la instalación
de Ollama/modelos fuera del proyecto. No se eliminó ni modificó ese material.
La política de retención y las copias externas programadas quedan para E7.
La comparación por archivo y la copia online de SQLite no constituyen un snapshot
atómico entre base y archivos; la operación productiva debe coordinar las escrituras.

Verificar SQLite:

```powershell
.\.venv\Scripts\python.exe scripts/sqlite_backup.py verify storage/temp/pre-e0-e1-20261017.db
```

Para otra restauración, pasar un destino que todavía no exista:

```powershell
.\.venv\Scripts\python.exe scripts/sqlite_backup.py restore storage/temp/pre-e0-e1-20261017.db storage/temp/e0-e1-new-restore.db
```

La recuperación completa debe hacerse con API y workers detenidos, verificando
manifest.json y hashes antes de seleccionar qué restaurar. No reemplazar una
base en uso ni mezclar archivos de distintas fechas. Esta etapa ensayó recuperación
en paralelo; no reemplazó datos reales. No requiere migración de esquema.

## Contrato E1 y correcciones

`GET /api/settings/` y `GET /api/settings/readiness` requieren `settings:read`.
El catálogo vigente concede esa capacidad únicamente a `admin` por su permiso
administrativo. No se otorga a coordinador, analista, legal o lector. La validación
de sesión sigue comprobando usuario/organización activos y revocación.

- Sin sesión o token inválido: 401.
- Sesión sin permiso administrativo: 403.
- Administrador: metadatos globales sanitizados, sin datos de otros expedientes.
- Resumen: solo app_name, env y api_prefix.
- Diagnóstico: dialecto, versión declarada, revisiones encontradas, disponibilidad
  de Alembic, cantidad de registros de migración e indicadores existentes de estado.
  El almacenamiento muestra un modo genérico; no expone ubicaciones.
- El detalle libre de migraciones no se serializa. La función interna tampoco
  devuelve database_url, y el diagnóstico no crea tablas ni registros.

La revisión de rutas similares encontró que el listado de organizaciones devolvía
settings_json completo. Ahora los serializadores de identidad usan campos
permitidos por modelo y omiten la configuración de organización, incluso para
administradores. La configuración almacenada no se modifica. Contraseñas, hashes
y columnas futuras no se incorporan automáticamente a esas respuestas.

Los indicadores heredados de preparación no certifican PostgreSQL ni la correcta
aplicación de todas las migraciones. Esa validación operativa sigue pendiente.

Errores seguros:

- Diagnóstico fallido: 503, `settings_readiness_unavailable`.
- Entrada que no cumple el contrato: 422, `request_validation_failed`.
- Respuesta que no cumple el contrato: 500, `response_validation_failed`.
- Error SQLAlchemy no controlado por una ruta: 503, `database_operation_failed`.

Los handlers no serializan la excepción, SQL, parámetros, cuerpo rechazado ni
traceback. Los errores globales incluyen request_id y los logs propios solo código
y request_id; el diagnóstico registra un código fijo. La autenticación exitosa
sigue entregando su token al usuario: no se confunde ese flujo con exposición de
configuración. Se preservan las rutas de recuperación local deshabilitadas por
defecto y la administración acotada existentes.

Los tests usan contraseñas y URL ficticias para provocar errores sin registrar
su valor. No se introdujo una redacción universal de todo contenido del expediente:
los datos suministrados por analistas pueden contener información sensible y
siguen sujetos a sus permisos. Logs externos, proxy, debug SQL o herramientas del
host requieren configuración propia antes de producción.

## Sesiones y riesgos pendientes

La sesión del navegador sigue en localStorage; E1 no cambia ese protocolo ni
invalida sesiones existentes. Se conserva la revocación y verificación de rol y
organización del backend. La estrategia productiva de sesión, MFA y recuperación
requiere una etapa explícita, pruebas de CSRF/XSS y HTTPS; no habilitar cookies o
refresh tokens como cambio incidental.

La pantalla Configuración ahora puede devolver 403 a roles que antes accedían.
La navegación por rol y el rediseño de esa pantalla se completarán en E4; el
backend ya impide el acceso. No se habilitaron conectores ni se cambiaron
concesiones de organizaciones, modelos, custodia o permisos de casos.

## Pruebas y reversión

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_configuration_security.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

Las pruebas verifican 401/403 antes de ejecutar el diagnóstico, lista de campos
permitidos incluso para admin, rechazo de secretos ficticios en respuestas/logs,
errores de identidad y SQLAlchemy, validación de salida y diagnóstico sin escrituras.
El fixture de pruebas ahora dirige también el diagnóstico de migraciones a su
base temporal; no usa el engine de la base principal.

La regresión detectó una suposición temporal incorrecta en la sonda CPU existente:
exigía observar en seis segundos de reloj el corte por una cuota de un segundo
de CPU de usuario. Una medición independiente confirmó terminación del kernel con
`STATUS_QUOTA_EXCEEDED`. Windows comprueba estas cuotas periódicamente, conforme a
[la documentación oficial](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_limit_information).
Se corrigió exclusivamente la espera de esa prueba (máximo 20 s, presupuesto de
prueba 25 s) y se reforzó la aserción del código exacto de cuota. Un timeout o kill
del supervisor sigue siendo fallo. No se cambiaron cuotas ni tiempos de producción.

Reversión de código: usar el commit previo solo en una copia aislada para
diagnóstico, porque reinstalarlo vuelve a abrir la exposición corregida. No hace
falta revertir datos ni claves. Preservar los respaldos y auditorías anteriores.
La siguiente etapa autorizable es E2: custodia append-only, rectificaciones
versionadas y conservación de informes; luego E3, ACL por expediente.

## Aceptación final

Regresión completa final, ejecutada sin otra suite simultánea: **233 aprobadas**,
una omitida por requerir opt-in de Ollama real y cuatro advertencias preexistentes,
931,09 s de tiempo transcurrido. Las 33 pruebas focalizadas de configuración y
pentest también aprobaron. Los intentos anteriores fallaron en la sonda CPU con
la espera antigua; se conservan sus XML privados como evidencia del diagnóstico.
No se silenciaron fallos ni advertencias para obtener la aceptación.

Build TypeScript/Vite 6.4.4 aprobado, 1583 módulos. Bandit: cero altas/medias,
15 bajas revisadas y cero errores de análisis. Sin nuevas dependencias de aplicación.
No hubo inspección visual nueva del frontend ni inferencia real en esta etapa.

Después de la última suite, las **72 tablas y todos sus valores** coinciden con
el respaldo y la restauración. Los **116 archivos**, su inventario y sus bytes
coinciden entre originales, copia y restauración. SQLite integrity_check correcto.
SHA-256 de SQLite respaldado y restaurado:
`b2aaad233d98b5f11e2b9546c1cefe5f575d214bf6943eeea86f30e155a16371`.

[Registro técnico sanitizado](audits/e0-e1-20261017.json).
E0/E1 quedan implementadas y verificadas dentro del alcance local descrito.
E2 y E3 permanecen pendientes; no se declara preparación productiva.
