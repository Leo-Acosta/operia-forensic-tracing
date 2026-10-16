# Forense móvil: diagnóstico y entrega incremental

Fecha: 2026-10-16. Base inspeccionada: `b2b7223`, checkout `new_unified_app`.
Rama de trabajo: `feature/mobile-forensics-mvt`. Sin publicación autorizada.

## Diagnóstico previo a cambios

- Git estaba limpio en main; origin coincide con el repositorio solicitado. No existe
  objeto 21bc0a4, rama local/remota MVT, paquete mobile_forensics, pantalla, documentación
  ni pruebas informadas. No se encontraron ZIP/patch en el proyecto ni adjuntos accesibles.
  No se recuperó ni certificó aquella integración. No hay AGENTS.md en los directorios
  de código inspeccionados ni en los ancestros del workspace.
  Consulta remota de cierre `git ls-remote --heads origin`: solo main en b2b7223;
  no se descargó código ni se publicaron cambios.
- FastAPI en apps/api/main.py, React/TypeScript en apps/web/src/App.tsx,
  SQLAlchemy compartido en operia/core/database.py; SQLite por defecto.
  Bootstrap create_all y adiciones SQLite en operia/core/bootstrap.py; Alembic tiene
  una baseline que NO crea el esquema completo (migrations/versions/20260528_0001*).
- Identidad: bearer persistente y roles en operia/identity; organización nullable.
  same_organization considera valores nulos accesibles: no sirve para este módulo.
  No hay ACL de asignación de analista a caso: los roles operan por organización.
- Casos/hallazgos/hipótesis: operia/cases; evidencia/custodia: operia/evidence;
  auditoría: operia/audit; trazado: operia/geo_trace; informes: operia/reports y
  operia/legal_report; exportaciones: operia/exports; IA: operia/ai_assistant y mind.
- Riesgo P0 preexistente: GET de casos/evidencia no exige sesión ni ámbito;
  varias escrituras validan rol pero no propiedad del caso. Informes, trazado e IA
  requieren auditoría integral de acceso antes de transferir datos móviles a ellos.
  El piloto no transfiere datos a esos módulos. No se declara aislamiento global.
- No hay adaptador MVT que revisar. MVT no es dependencia del proyecto.
  No se dispone de adquisición ni dispositivo autorizado de referencia.
- Baseline frontend: npm run build aprobado. Backend inicialmente bloqueado por
  Python WindowsApps inutilizable y pytest ausente; se prepara .venv aislado.

## Plan, dependencias y aceptación

| Prioridad / tarea | Depende de | Criterio verificable | Entrega |
|---|---|---|---|
| P0.1 diagnosticar y ejecutar regresión | acceso código/runtime | resultados reales documentados | actual |
| P0.2 frontera estricta móvil | identidad/caso | 401 sin sesión, 403 rol, 404 otro caso/org o sin org | actual |
| P0.3 preservación transaccional | P0.2 | bytes originales/hash, límites, duplicados, sin rutas de usuario | actual |
| P0.4 aislar plataforma completa | auditoría de TODOS los módulos | pruebas cruzadas en cada endpoint y exportador | pendiente; bloquea transferencias |
| P1.1 dispositivos y exámenes importados | P0.2/3 | persistencia, autorización, procedencia, cobertura separada | actual piloto |
| P1.2 revisión inmutable y JSON versionado | P1.1 | respaldo referenciado, revisor real, historial y hash verificado | actual piloto |
| P1.3 evidencia derivada e informes canónicos | P0.4/P1.2 | custodia y exports sin filtraciones | pendiente |
| P2.1 compatibilidad motor | instalación separada/fixtures autorizados | versión/comandos/opciones y salidas contrastadas | pendiente |
| P2.2 worker persistente/cancelación/recuperación | P2.1 | árbol terminado, reinicio y fallos probados; aislamiento efectivo | pendiente |
| P3 indicadores versionados | P2.1 | bytes/hash exactos y compatibilidad de cada ejecución | pendiente |
| P4 cronología/trazado | P1.3/P3 | esquema temporal conocido, cada evento remite al original | pendiente |
| P5 PDF/Word e informe final | P1.3/P4 | revisión versionada y referencias verificables | pendiente |
| P6 IA explicativa | P0.4/P5 | citas verificables, aislamiento, resistencia a instrucciones en evidencia | pendiente |

La primera entrega es un piloto local de preservación/importación y revisión, no
una certificación comercial ni la totalidad del alcance solicitado. No se habilitan
ejecución, IA, trazado ni exportación canónica antes de completar sus dependencias.

## Fuentes y compatibilidad

Consultadas el 2026-10-16:
- https://docs.mvt.re/en/latest/ (instalación, comandos y metodología).
- https://docs.mvt.re/en/latest/ios/records/ (salidas y archivos *_detected.json).
- https://github.com/mvt-project/mvt/releases/tag/v2026.10.12 (versión candidata).
- https://github.com/mvt-project/mvt/blob/main/LICENSE (MVT License 1.1).

MVT pertenece a sus autores, iniciado por Amnesty International Security Lab.
No se copia, modifica ni distribuye el motor. La licencia propia incluye restricciones
de consentimiento del dueño de los datos y obligaciones de distribución; revisar el
texto de la versión exacta y las condiciones aplicables antes de prestar servicio.

| Plataforma | Versión candidata | Entorno / adquisición | Comandos de referencia | Formato | Validación |
|---|---|---|---|---|---|
| iOS | 2026.10.12 | entorno separado; backup/filesystem | mvt-ios check-backup / check-fs | JSON por módulo, *_detected.json | documentación consultada; motor/adquisición NO validados |
| Android | 2026.10.12 | entorno separado; backup SMS | mvt-android check-backup | JSON por módulo | documentación consultada; motor/adquisición NO validados |

No se ofrecen banderas ejecutables desde OPERIA hasta contrastarlas con --help de
la instalación seleccionada. Un ejecutable presente no implica compatibilidad.
La importación funciona sin instalar MVT; su procedencia siempre es declarada por
el operador, nunca autenticada por el nombre de un JSON.

Windows nativo no tiene soporte oficial según la documentación consultada; MVT
recomienda WSL. En este host no se encontraron mvt-ios/mvt-android en PATH;
`wsl --list --quiet` (fuera de la restricción del sandbox) solo devolvió
docker-desktop. No se alteró esa distribución ni se instaló el motor sobre ella.
Preparación posterior, en Linux/WSL de propósito general, fuera de producción:

```bash
python3 -m venv ~/operia-mvt-2026.10.12
~/operia-mvt-2026.10.12/bin/python -m pip install 'mvt==2026.10.12'
~/operia-mvt-2026.10.12/bin/mvt-ios --version
~/operia-mvt-2026.10.12/bin/mvt-ios check-backup --help
~/operia-mvt-2026.10.12/bin/mvt-ios check-fs --help
~/operia-mvt-2026.10.12/bin/mvt-android --version
~/operia-mvt-2026.10.12/bin/mvt-android check-backup --help
```

Estos comandos son preparación documentada, **no ejecutada en esta entrega**.
Instalar dependencias del sistema indicadas por MVT en el entorno elegido,
archivar versión/licencia/help y contrastar las opciones antes del primer examen.
No hay configuración que habilite ejecución desde el servidor en este piloto.

## Lo implementado y cómo usarlo

1. Iniciar OPERIA según README; entrar con un usuario de una organización concreta,
   crear/seleccionar un caso de esa misma organización y abrir **Forense móvil**.
2. Registrar dispositivo iOS o Android. El identificador puede ser interno.
3. Importar un JSON de una sola ejecución, con autorización, consentimiento informado,
   alcance, procedencia, método/fecha de adquisición, política de retención,
   versión y ejecución declaradas e información disponible de indicadores.
4. Examinar los registros paginados (100 por página), cobertura, candidatos y hash.
   Descargar el original para cotejar los bytes. No se abren URLs de los registros.
5. Agregar revisión con fundamento, referencias por índice, alternativas y límites.
   Actividad actual, cronología y atribución tienen campos separados. Una revisión
   nueva conserva las anteriores. La identidad se toma de la sesión, no del formulario.
6. Crear una exportación JSON: snapshot inmutable con dispositivo, alcance,
   historial, última revisión usada y manifiesto. Cada exportación conserva sus bytes
   y hash aunque luego se agreguen revisiones. Es borrador experimental.

Permisos: evidence:read para consultar/descargar y evidence:write para registrar,
importar, revisar y crear exportaciones. El rol lector ve los controles de escritura
deshabilitados. El backend comprueba permisos independientemente de la interfaz.
Administradores tampoco pueden saltar de organización. Casos sin organización
no se admiten; deben asignarse mediante un proceso administrativo auditado posterior.
Dentro de una organización rigen los roles existentes: no hay ACL individual de casos.

Formularios pendientes bloquean la navegación lateral hasta guardar o descartar.
La recarga/cierre del navegador usa beforeunload. El componente se recrea al cambiar
caso o token y descarta respuestas tardías de consultas previas. No se persisten
borradores sensibles en localStorage. Los borradores no sobreviven a caída del proceso.

### Importación y preservación

API base: `/api/mobile-forensics`.
- GET /engine: presencia del ejecutable, ejecución deshabilitada y no validada.
- GET/POST /cases/{case}/devices; GET /cases/{case}/exams.
- POST /cases/{case}/devices/{device}/imports.
- GET /cases/{case}/exams/{exam}?offset=0 (100 registros por página).
- GET /cases/{case}/exams/{exam}/original.
- POST /cases/{case}/exams/{exam}/reviews.
- POST /cases/{case}/exams/{exam}/exports.
- GET /cases/{case}/exams/{exam}/exports/{export}.

El transporte de importación es JSON con exactamente metadata (ImportMetadata),
filename y content_base64. Base64 transporta los bytes sin normalizar espacios,
codificación ni saltos de línea. No es un formato de reporte nativo de MVT.
El servidor limita la lectura del transporte antes de parsearlo y luego el archivo
decodificado. `OPERIA_MOBILE_IMPORT_MAX_BYTES` configura 1 byte a 50 MiB (por defecto
5 MiB); la interfaz mantiene su máximo de 5 MiB. Profundidad máxima 32 y hasta 10000
registros. Rechaza claves duplicadas, números no finitos, rutas, archivos no JSON,
archivos comprimidos y módulos fuera de la lista. No extrae archivos ni usa shell.

Perfiles **estructurales experimentales**, contrastados solo con fixtures sintéticos:
- iOS safari_history(.json y _detected.json): lista de objetos con url no vacía.
- iOS/Android sms(.json y _detected.json): lista de objetos con body textual y algún
  campo address, phone_number, isodate, date o timestamp.

La estructura y el nombre NO prueban que el archivo provenga de MVT; se registran
como declaración del operador. Otras variantes reales pueden ser rechazadas hasta
incorporar fixtures autorizados y un perfil versionado. Una lista vacía se preserva
como sin_datos_analizables, jamás como ausencia de compromiso. Un archivo normal sin
_detected tiene cero candidatos declarados, pero no acredita haber buscado indicadores.
Un archivo _detected solo identifica candidatos declarados pendientes de corroboración.
No existe registro exacto de indicadores todavía: no se afirma reproducibilidad MVT.

MobileExam conserva los bytes originales en BLOB en SQLite; no copia una adquisición
completa ni certifica su integridad. Hash SHA-256 sobre los bytes recibidos, calculado
antes del parseo, verificado antes de lectura, descarga, revisión y exportación.
El hash prueba identidad de esos bytes, no autenticidad del origen, exactitud de la
adquisición, limpieza del dispositivo ni cobertura. Solo los archivos aceptados se
guardan; importaciones rechazadas no ingresan al repositorio de evidencia del piloto.
Restricción única por dispositivo/hash evita duplicados incluso en carreras concurrentes.
Original y examen se confirman en una sola transacción SQL con el evento de auditoría.

Se agregan cuatro tablas: mobile_devices, mobile_exams, mobile_reviews, mobile_exports.
Adquisición/ejecución externa se registran por ahora como metadatos del examen; no son
entidades administradas. Cada archivo genera un examen independiente; no hay fusión
de archivos de distintas ejecuciones ni validación automática del run_id declarado.
No hay historial de borrado ni retención automática; la política queda registrada y
su cumplimiento requiere gestión administrativa. No se expone eliminación por API.

### Conclusiones habilitadas

Solo inconcluso, actividad_sospechosa e indicios_compatibles_con_compromiso.
Las dos últimas requieren índices de respaldo válidos en el original preservado.
No se habilitan compromiso confirmado ni sin indicios: este piloto de un archivo
carece de cobertura e indicadores exactos para sostener esas conclusiones.
No normaliza fechas ambiguas ni inventa cronologías; el registro original se conserva.

## Respaldo, restauración y reversión

Antes de abrir la nueva versión contra una base existente:

1. Detener API y cualquier escritor; inventariar permisos y ubicación de storage.
2. Respaldar SQLite con el script incluido (no copiar un .db en uso sin su WAL).
   Copiar además storage completo a un destino protegido, fuera de Git, conservando
   permisos. La base contiene originales móviles, pero la evidencia previa puede estar
   en archivos externos. Conservar configuración/secretos por un canal protegido.
3. Verificar el hash/manifiesto y restaurar a una ubicación nueva de prueba.
4. Ejecutar migración y comprobar casos/evidencias en la copia antes de cambiar producción.

```powershell
.\.venv\Scripts\python.exe scripts/sqlite_backup.py backup storage/operia_forensic_tracing.db storage/temp/pre-mobile.db
.\.venv\Scripts\python.exe scripts/sqlite_backup.py verify storage/temp/pre-mobile.db
.\.venv\Scripts\python.exe scripts/sqlite_backup.py restore storage/temp/pre-mobile.db storage/temp/restore-check.db
```

El script nunca sobrescribe destinos. Su manifiesto es de integridad, no una firma
ni prueba contra un atacante con escritura simultánea sobre respaldo y manifiesto.
Mover el respaldo verificado a un destino cifrado con política de acceso/retención.
No dejar respaldos como única copia en el mismo disco. Nunca subirlos a Git.

Migración Alembic `20261016_0002`, dependiente de la baseline `20260528_0001`:
crea exclusivamente las tablas móviles si faltan. El bootstrap local también las
crea al arrancar. No aplica alteraciones destructivas a tablas existentes. La baseline
histórica no permite construir toda la plataforma desde una base vacía con Alembic
solo: inicializarla por el mecanismo existente antes de usar su historial.
El downgrade conserva las tablas para no destruir originales; una reversión de código
puede volver a b2b7223 conservando los datos. Una reversión íntegra de datos exige
restaurar la copia verificada, junto con storage correspondiente, en una ubicación
nueva; apuntar OPERIA_DATABASE_URL y OPERIA_STORAGE_DIR a ella con API detenida.
No restaurar encima de una base activa. No se probó PostgreSQL.

## Matriz de estado y verificación

| Capacidad | Estado / evidencia |
|---|---|
| API móvil, roles y ámbito estricto | implementado, probado con tokens locales y usuarios sintéticos de otros ámbitos |
| Preservación/hash, duplicados y errores | implementado, probado con bytes sintéticos y alteración deliberada |
| Dispositivos, revisión acumulativa y snapshot JSON | implementado, probado por API y recorrido de navegador sintético |
| Migración aditiva, respaldo/restauración | probado sobre SQLite sintético con caso y evidencia previos; no sobre base del usuario |
| Interfaz: importación/revisión/descarga/persistencia | recorrido manual automatizado en navegador con servidor y base separados |
| Navegación pendiente y descarte | comprobados en navegador; no hay suite automatizada de frontend |
| MVT real, perfiles de salida y calidad de detección | implementado solo el reconocimiento estructural experimental; sin validación real |
| Worker, cancelación, recuperación, sandbox de ejecución | pendiente; no hay ejecución expuesta |
| Indicadores exactos, cronología normalizada y trazado | pendiente |
| Evidencia derivada, informes canónicos, PDF/Word e IA | pendiente; transferencia deshabilitada hasta completar controles transversales |
| Seguridad multiempresa de toda la plataforma | pendiente/crítica; no certificada por las pruebas del módulo |

Pruebas: instalar requirements-dev.txt en .venv, ejecutar
`python -m pytest -q -p no:cacheprovider`. En este entorno Windows, TestClient quedó
bloqueado creando su socketpair de asyncio dentro del sandbox; fuera de esa restricción
las pruebas se ejecutan. Suite previa disponible: **52 aprobadas**, no las 57 informadas.
Pruebas móviles: cubren entradas sintéticas, ámbitos, roles, integridad, historial,
snapshots, migración y recuperación. Ver sección de resultados de cierre para cifras finales.
Advertencias preexistentes: on_event/Starlette/ReportLab deprecados y combinación de
dependencias requests/chardet no recomendada. No se ocultaron ni corrigieron en este cambio.

Próximo paso: cerrar P0 transversal (incluida recuperación de administrador local),
preparar Linux/WSL aislado y obtener adquisiciones de referencia autorizadas por su
dueño. Por separado para Android/iOS, registrar versiones/comandos/help/licencia,
hashes de entradas y de indicadores; contrastar salidas directas con la importación,
documentar falsos positivos/omisiones y someter resultados a revisión profesional.
No usar evidencia de clientes para esta validación sin un flujo específico autorizado.

## Resultados de cierre — 2026-10-16

- Regresión final: **70 aprobadas**, 5 advertencias preexistentes, 108.95 s.
  Incluye 52 pruebas anteriores y 18 casos nuevos (parametrizados incluidos).
- Frontend: `npm run build` aprobado (TypeScript + Vite, 1582 módulos).
- `git diff --check` sin errores de contenido; Git avisa normalización LF/CRLF.
- Navegador, base sintética separada: login, caso, dispositivo, carga original,
  SHA-256, registro/cobertura, revisión con autor, exportación y persistencia al
  reabrir. Comprobados bloqueo de navegación y descarte de borrador pendiente.
- Herramienta CLI de respaldo ejecutada sobre esa base sintética: backup, verify
  y restore a un destino nuevo. Restaurados 1 examen, 1 revisión y 1 exportación;
  hash del original coincidente e integrity_check = ok. Sin tocar la base del usuario.
- Servidores locales de QA y pruebas bloqueadas por sandbox cerrados al terminar.
- No hubo motor simulado que emitiera resultados: se usaron JSON sintéticos
  etiquetados como tales. **MVT real ejecutado: ninguno. Dispositivos reales: ninguno.**
- Implementación en operia/mobile_forensics, pantalla MobileForensics.tsx,
  migración aditiva 20261016_0002, registro de router/modelos/configuración,
  estilos locales, requirements-dev y scripts/sqlite_backup.py. El resto de los
  módulos conserva su comportamiento; los riesgos previos documentados continúan.
- Entrega en rama local feature/mobile-forensics-mvt; sin push, PR ni despliegue.
  Identificar el commit mediante `git log -1 --oneline` en esa rama.
