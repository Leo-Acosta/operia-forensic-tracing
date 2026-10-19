# Validación verificable

## E6: registros SQLite Safari iOS, 2026-10-18

Motor **0.7.0**, lector `operia.ios.safari-history` **1.0.0**, formato
`ios-safari-history-sqlite`: [contrato, límites y exclusiones](E6_IOS_APP_SQLITE.md).
Trece lectores y once formatos. Consultas fijas de columnas permitidas en
history_items/history_visits sobre copia privada deserializada, hasta 500 filas
por tabla, sin época de fechas inferida ni eventos de cronología. El formato de
catálogo previo sigue sin leer filas de aplicaciones.

**42 pruebas específicas aprobadas**, incluido un worker real AppContainer/Job:
oráculo de dos visitas, referencia huérfana, elemento sin visita, BLOB/columnas/tabla
privados no publicados, fechas desconocidas, IDs separados para valores iguales,
límite 500/501, controles/tipos/URLs inválidos, esquemas activos, presupuesto VM,
CLI `-S` sin descubrimiento de WAL señuelo, autorizador y copia intacta.
Original/evidencia íntegros, evento de custodia, informe/exportación estables tras
otra revisión, solo lectura, falta de concesión, revocación, otro expediente y
organización ajena. El autorizador de Manifest/catálogo no obtuvo permisos Safari.

Regresión de módulos afectados y pentest local: **296 aprobadas y 1 timeout HTTP**
al crear un caso sintético por loopback; esa prueba **aprobó aislada**, sin cambiar
código, permisos, timeout ni aserciones. Su causa no quedó determinada; no se
reprodujo en esa repetición. Por tanto, **297 pruebas backend distintas con último
resultado aprobado**, no una ejecución completa sin fallos. Las 42 específicas
están incluidas; no se suman otra vez. Incluye motor, lectores anteriores,
incorporaciones/proyecciones, permisos, custodia y controles de aislamiento OS.
**No se ejecutó toda la suite backend** en este tramo. Cuatro advertencias de
deprecación conocidas. Frontend: **52 aprobadas** y compilación TypeScript/Vite
correcta, con ayuda accesible del perfil nuevo.

Intentos previos: el primer unitario tuvo 22 aprobadas y 12 fallos en el control
positivo del test que consultaba solo id; se cambió por la proyección permitida
id,url, conservando el autorizador estricto. Las ejecuciones dentro del sandbox
del comando dejaron de avanzar durante el recorrido API/worker y se interrumpieron;
se repitieron fuera de ese sandbox, manteniendo AppContainer en los workers.
No se declaran esos intentos como regresiones definitivas aprobadas.

Comparación posterior a las pruebas: **74 tablas y todos sus valores, esquema,
9 triggers y 116 archivos persistentes intactos**, SQLite integrity_check correcto,
respaldo/restauración con SHA-256 idéntico. Sin migraciones ni recálculo de históricos.
Runtime `1717d297499151af78ec5640`: **694 archivos** verificados en runtime operativo,
archivo privado y copia restaurada; anteriores retenidos. Se ejecutó el runtime
preparado con AppContainer, no el archivo privado restaurado.

[Auditoría de entrega](../audits/e6-ios-app-sqlite-20261018.json).
Validación sintética; pendientes corpus real autorizado por OS/esquema, asociación
física, época de fechas, WAL/SHM del perfil, otras aplicaciones y validación física
de accesibilidad. Los registros de entregas anteriores se conservan abajo.

## E6: JSON en archivos lógicos iOS preservados, 2026-10-18

Motor **0.6.0**, lector lógico **1.1.0**: [cobertura y exclusiones](E6_IOS_LOGICAL_JSON.md).
Agrega escalares JSON/null con tipo, fileID, SHA-256 y posición escapada, sin
interpretar esquemas de aplicaciones ni producir cronología. Contenedores vacíos
como exclusiones localizadas. Rechazo completo de contenido inválido o excesivo,
con declaración/hash de archivo preservados; sin publicación de prefijos.

**239 pruebas backend distintas aprobadas**, sin fallos, errores ni omisiones:
58 específicas iniciales (incluyen cuatro workers reales, dos con JSON), y 200 de
regresión de módulos afectados. Se superponen 19 pruebas JSON; no sumar recuentos
como si fueran pruebas diferentes. La regresión incluye las dos comprobaciones
JSON finales de nodos y límites exactos, para 21 pruebas JSON en total. Incluye
motor, plist, Manifest/SQLite/WAL, flujo nativo, incorporaciones/proyecciones,
permisos por expediente y custodia. **No se ejecutó toda la suite backend** en
este tramo. Cuatro advertencias de deprecación conocidas. Frontend: **52 aprobadas**
y compilación TypeScript/Vite correcta, incluida la ayuda accesible actualizada.

Oráculos sintéticos: tipos JSON, BOM, null, posiciones iguales, claves escapadas,
contenedores vacíos, fecha/URL tratadas como texto. Negativos de claves duplicadas,
números no finitos, Unicode/controles, encoding, raíz, profundidad, nodos, bytes,
claves/strings y cantidad de valores. Workers AppContainer/Job para Files principal
y WAL: permisos solo lectura, revocación y organización ajena; original preservado,
informe y exportación sin cambios tras otra revisión.

El primer intento tuvo 52 aprobadas y 6 errores de setup al crear temporales de
pytest dentro del sandbox del comando. La repetición fuera de ese sandbox, con
temporales explícitos, aprobó las 58. El aislamiento AppContainer de los workers
se mantuvo activo. No se interpreta ese intento como fallo del lector ni como
validación definitiva.

Respaldo/restauración privados nuevos: **74 tablas con todos sus valores, esquema,
9 triggers y 116 archivos persistentes intactos**, integridad SQLite correcta y
hash idéntico de respaldo/restauración. Sin migraciones ni recálculo de históricos.
Runtime `38aabf7ea9926a525201a6a5`: **693 archivos** verificados en runtime preparado,
archivo privado y copia restaurada, con runtimes anteriores retenidos. Se ejecutó
el runtime preparado mediante workers reales; no el archivo privado restaurado.

[Auditoría de entrega](../audits/e6-ios-logical-json-20261018.json).
Pendientes: corpus autorizado real por OS/método, lectores de aplicaciones,
asociación física, cifrado y validación física de tecnologías de asistencia.
Los apartados siguientes conservan los resultados históricos anteriores.

## E6: selección lógica iOS preservada, 2026-10-18

Motor **0.5.0**, [contrato, cobertura y límites](E6_IOS_LOGICAL_FILES.md): manifiesto
Files principal o WAL y hasta 32 copias explícitas, sin recorrer rutas del backup.
Escalares plist XML/binario, líneas UTF-8, catálogo SQLite y hashes; omisiones,
directorios y contenido no compatible conservan exclusiones con localizador.

**37 pruebas específicas finales aprobadas**, con dos workers AppContainer reales.
Oráculo original: cuatro archivos, uno omitido y un directorio, once artefactos y
cuatro exclusiones; canarios BLOB/filas no exportados. Manifiesto principal/WAL,
errores de asociación e integridad, cuotas, entidades/duplicados/XML desconocido,
NSKeyedArchiver excluido, CLI `-S`, copias intactas y salida sin sobrescritura.
Cada observación incluye fileID, hash y posición lógica: archivos distintos con
contenido idéntico y claves/líneas distintas con valores iguales no se confunden
como un mismo registro. Permisos de lectura, escritura denegada, revocación y otra
organización; revisión posterior con informe y exportación anteriores estables.

Se corrigieron nombres excesivos de casos pytest que provocaban errores de setup
en Windows. La primera regresión general se interrumpió tras superar 70% para
reforzar contexto de archivo/posición; sus resultados no se declaran definitivos.
Los runtimes y comprobaciones preliminares permanecen separados en la auditoría.

Regresión completa definitiva: **410 aprobadas, 1 omitida, 0 fallos/errores y 4
advertencias de deprecación conocidas**. Ollama real requiere opt-in explícito.
Frontend: **52 aprobadas** y TypeScript/Vite correcto; ayuda accesible de selección
actualizada. Los recuentos específicos están incluidos en la regresión.

Comparación final: **74 tablas con todos sus valores, esquema, 9 triggers y 116
archivos persistentes sin cambios**. Respaldo/restauración con SHA-256 idéntico e
`integrity_check` correcto; no hubo migración ni recálculo de históricos.
Runtime definitivo `3059e493788c5c2a0b59de75`: 693 archivos verificados en runtime
operativo, archivo privado y copia restaurada. Se conservaron runtimes anteriores
y preliminares; el archivo privado no se ejecutó. Python 3.12.14/SQLite 3.53.1/Windows.

[Auditoría de entrega](../audits/e6-ios-logical-20261018.json). Sin corpus real por
OS, autenticación de asociación física, descifrado, NSKeyedArchiver, registros
específicos de aplicaciones ni validación física de accesibilidad. La selección
no equivale a un backup completo o a detección certificada. Los apartados siguientes
conservan la historia de las entregas anteriores.

## E6: WAL/SHM sobre conjuntos preservados, 2026-10-18

Motor **0.4.0**, [contrato y límites](E6_WAL_SHM.md). Dos formatos nuevos y tres
lectores registrados entre iOS y Android; once lectores y nueve formatos totales. Paquete preservado
con bytes y SHA-256 de DB/WAL/SHM, instantánea del último commit y cabeceras SHM
contrastadas; imagen derivada identificada por hash y transformaciones expresas.

Pruebas específicas: **32 de lector/CLI y 3 recorridos con workers reales aprobados**.
SQLite nativo como oráculo con datos sintéticos, dos filas/commits y flags 2/1;
WAL de checksums little/big y SHM de cabecera little/big, sin hardware big-endian.
Crecimiento/truncamiento, cola sin commit excluida, corrupción y esquemas activos
rechazados, cuotas, empaquetado y salida sin sobrescritura. Workers AppContainer:
revisión posterior, informe/exportación estables, concesión/revocación, solo lectura
y organización ajena. El intento inicial conjunto aprobó 81 y falló en 3 expectativas
HTTP: el sistema denegaba correctamente con 404 y el test esperaba 403. Se corrigió
el test y se comprobó que la denegación no agrega revisiones, sin cambiar autorización.

Regresión completa final: **373 aprobadas, 1 omitida, 0 fallos/errores y 4 advertencias
de deprecación conocidas**. Ollama real requiere opt-in explícito. Frontend:
**52 aprobadas** y compilación TypeScript/Vite correcta, con extensiones SQLite/JSON
y ayuda accesible para seleccionar el paquete. Los recuentos se superponen con la
regresión; no se suman como pruebas diferentes.

Preservación final: **74 tablas con todos sus valores, esquema, 9 triggers y 116
archivos persistentes sin cambios**. Respaldo y copia restaurada con SHA-256 idéntico
e `integrity_check` correcto. Sin migración ni reescritura de históricos.
Runtime `c2db06bdd16ee6a05b5cce87`: 692 archivos verificados en runtime operativo,
archivo privado y restauración; se conservaron los anteriores. El archivo privado
no se ejecutó. Python 3.12.14/SQLite 3.53.1/Windows; sin dependencias nuevas.

[Auditoría](../audits/e6-wal-shm-20261018.json). No acredita adquisición simultánea
ni asociación auténtica DB/WAL, capturas concurrentes, otras variantes/VFS,
SHM multibloque/índices/locks, archivos lógicos, muestras reales o validación física
de accesibilidad. Los registros siguientes conservan la historia de sus entregas.

## E6: Manifest.db y SQLite acotados, 2026-10-18

Motor 0.3.0: [contrato y cobertura](E6_MANIFEST_SQLITE.md). Dos perfiles nuevos,
tres registros de lector por plataforma y ocho lectores totales. Imágenes SQLite
sintéticas generadas en pruebas originales; oráculo manual de campos y localizadores.
No hay corpus real ni validación por versión de iOS/Android.

Suite focalizada: **49 aprobadas**, incluyendo los lectores anteriores, CLI real
con Python `-S` y tres workers AppContainer/Job Object reales. Pruebas de consulta
fija, bloqueo de SQL/funciones/adjuntos/BLOB, esquemas activos, WAL/truncamiento,
encoding, exclusiones y cuotas; revisión, incorporación, informe preservado,
concesión/revocación y descarga exacta del original.

Regresión completa: **338 aprobadas, 1 omitida, 0 fallos/errores y 4 advertencias
de deprecación conocidas**. La omitida es Ollama real, que exige opt-in explícito.
Frontend: **52 aprobadas**, compilación TypeScript/Vite correcta. Los recuentos
focalizados están incluidos en la regresión, no se suman como pruebas distintas.
El primer intento de pruebas unitarias tuvo dos errores de temporales del sandbox;
la repetición con permisos del entorno de prueba aprobó las 27 seleccionadas.

Comparación final contra respaldo de esta entrega: **74 tablas y todos sus valores,
esquema, 9 triggers y 116 archivos persistentes sin cambios**. `integrity_check`
correcto; respaldo/restauración con SHA-256 idéntico. No hay migración de datos.
Runtime `6032ff7dbb559eaa65685660`: 691 archivos verificados en runtime operativo,
archivo privado y copia restaurada; runtimes previos conservados. El archivo privado
restaurado no se ejecutó. Pruebas en Python 3.12.14/SQLite 3.53.1/Windows.

[Auditoría de entrega](../audits/e6-manifest-sqlite-20261018.json), con ubicación de
artefactos de prueba privados. Siguen pendientes corpus real, WAL/SHM, archivos
lógicos, otras variantes y validación física de accesibilidad. Los registros que
siguen conservan los resultados históricos de sus respectivas versiones.

## Baseline e historia

Baseline antes de modificar componentes existentes: 70 pruebas aprobadas y
TypeScript/Vite compilados sobre 11a6761. La cifra previa de 57 no es evidencia de
este motor. Los checks se ejecutan con requirements-dev y fixtures propios.

Corpus: tests/fixtures/native_mobile/README.md, XML/plist original, inventario de
dos paquetes y log epoch de tres eventos con oráculo temporal manual. La variante
binaria se genera con plistlib. No son salidas de un motor externo ni dispositivos.

Pruebas de núcleo: lecturas positivas/negativas, bytes/hash, referencias, igualdad
con límites de dominio, IPv6/URL, rechazo de expresiones ejecutables, estructuras
inválidas/profundas, datos vacíos/ambiguos, catálogo/ciclos y reproducibilidad.
CLI con Python -S comprueba independencia de paquetes web/IA/motor ajeno.

Pruebas de integración: API autenticada y roles, ámbitos no nulos, IDs de otro caso,
originales, encolado idempotente, subproceso real del núcleo, indicadores exactos,
revisión/historial, JSON/CSV, snapshots previos, cancelación pendiente y en ejecución,
timeout, recuperación/reintento, scope cambiado, corrupción y cuota lógica/de salida.
No se simula el motor: cancelación se inyecta mediante API al crearse el hijo real;
cuotas/timeouts pequeños fuerzan caminos de fallo con fixtures sintéticos.

Migración: base previa de SQLite con exportación externa conserva sus bytes después
de upgrade repetido y downgrade no destructivo. El script de backup/restore anterior
sigue probado. No se aplicaron pruebas destructivas a datos de clientes.

No validado: adquisiciones reales de iOS/Android, calidad de detección de amenazas,
falsos positivos/negativos representativos, SQLite/WAL o cifrado, POSIX, crash forzado
del worker con hijos vivos, PostgreSQL, sandbox de SO, SaaS integral y UX móvil con
tecnología asistiva. No hay porcentajes de precisión, equivalencia ni certificación.

Recorrido de navegador sobre una copia de la base sintética anterior: login,
dispositivo Android, preservación de logcat-epoch.txt, encolado real, worker
independiente, 3 artefactos y 3 tiempos UTC, revisión con ID de respaldo y descarga
de informe JSON. La ausencia de indicadores apareció expresamente como tal.
Se comprobó el histórico externo con su revisión/archivo y origen separado.
Cerrar sesión en una segunda pestaña retiró los datos del examen de la primera.
No hay suite de frontend automatizada incorporada al repositorio.

El arranque independiente detectó una dependencia de registro del grafo ORM que no
aparecía en el proceso de API. Fue corregida y tiene prueba propia en un proceso
limpio. También se prueba la modificación de entrada durante el análisis: nunca
publica un resultado completado. No se simula un motor externo ni su salida.

Respaldo/restauración de la base de ese recorrido: conservó 1 adquisición, 1 job,
1 revisión y 1 exportación nuevos, junto con el snapshot externo previo byte por
byte. Hashes de adquisición/resultado correctos e integrity_check=ok. Servidores
de QA cerrados al terminar. Los artefactos sensibles/sintéticos de ejecución siguen
fuera de Git, bajo storage/test_runs; la documentación y fixtures públicos no los incluyen.

Verificación focalizada final: 46 pruebas aprobadas (núcleo y flujo de worker/API),
incluyendo conjuntos vacíos, comparadores, agrupación de hashes y prohibición de
ausencia de indicios basada solo en DEMO. Frontend TypeScript/Vite compilado, 1582
módulos. Persisten las 5 advertencias de dependencias/deprecaciones preexistentes;
no se ocultaron ni se ampliaron dependencias para resolverlas en este cambio.

Inventario: 47 componentes Python del entorno (incluido desarrollo) y 119 entradas
del lockfile de frontend; cero dependencias nuevas del núcleo. Estos números no
certifican condiciones jurídicas ni sustituyen revisión de avisos antes de distribuir.

**Cierre 2026-10-16:** regresión completa definitiva, **114 aprobadas**, 5
advertencias preexistentes, 114.71 s. `git diff --check` sin errores (avisos de
normalización LF/CRLF). No se ejecutaron MVT ni adquisiciones reales. Cambios
solo locales en feature/operia-native-mobile-engine; sin push, PR ni despliegue.
El commit de entrega se obtiene con `git log -1 --oneline` en esa rama.


## Etapa de aislamiento e incorporación (2026-10-16)

Pruebas nuevas en test_native_integration.py: dos organizaciones con tokens reales,
lectura de hijos históricos NULL solo por su caso, listas/dashboard/usuarios sin
filtración, referencias cruzadas rechazadas, doble permiso de incorporación,
idempotencia por revisión, fuente original por hash, informe/versión/custodia
preservados y prohibición de borrado del caso móvil. Migración 0004 repetida y
no destructiva sobre copia restaurada, con comparación exacta de bytes externos.

PDF y Word se abren con pypdf/python-docx para comprobar el hash de la instantánea
y el contenido de revisión. HTML escapa texto activo. Las exportaciones repetidas
usan archivos distintos y conservan el primero; se rechazan rutas y referencias
ajenas antes de escribir. El frontend compila con TypeScript/Vite, 1582 módulos.
No se hizo una nueva verificación visual del navegador en esta etapa.

Regresión de transición: 120 pruebas aprobadas (215.23 s). Después del último
refuerzo de exportadores y validación previa: 21 pruebas focalizadas aprobadas
(83.89 s). Sin dependencias nuevas. Persisten las cinco advertencias anteriores.
La suite completa final se registra al cierre de esta sección.

Respaldo y restauración local verificados con SQLite integrity_check y manifiesto
SHA-256; comparación de las tablas de originales, revisiones y exports móviles
contra el respaldo sin diferencias. Los backups no incluyen archivos externos.
La validación sigue siendo sintética, sin dispositivos reales ni ejecución MVT.


Cierre definitivo de esta etapa: **121 pruebas aprobadas**, 5 advertencias
preexistentes, 199.67 s. Comando: `.venv/Scripts/python.exe -m pytest -q -p
no:cacheprovider`. Compilacion frontend aprobada; `git diff --check` sin errores.
Cambios locales en feature/operia-native-mobile-engine, sin push ni despliegue.


## Proyecciones y capas de seguridad (2026-10-16)

33 pruebas nuevas: proyeccion de artefactos revisados, hipotesis separada, referencias
Geo pasivas sin red/ubicacion inferida, idempotencia, correcciones independientes,
mutaciones/borrados rechazados, permisos y accesos cruzados, hashes y migracion
0005 repetible. Seguridad: bloqueo antes de DNS, respuestas DNS mixtas/internas y
especiales, destino fijado, redirects y respuesta excesiva, JSON hostil, limites de
cuerpo/rate/concurrencia, origen, recuperacion apagada, shell retirado, IA no
habilitada, mapas inertes, rutas Geo acotadas y prueba de arquitectura de red.
Todas las respuestas de proveedor se simularon; no se enviaron evidencias a red.

Regresion completa final: **154 aprobadas**, cinco advertencias preexistentes,
173.34 s. TypeScript/Vite aprobado (1582 modulos); diff sin errores. No hubo una
nueva inspeccion visual del navegador, adquisiciones reales, pentest ni auditoria
CVE. Sin nuevas dependencias del motor ni instalacion/ejecucion de MVT.

La copia restaurada de SQLite recibio upgrade/downgrade de 0005: 71 tablas anteriores
con valores identicos, una tabla agregada y integrity_check ok. El snapshot externo
historico y las revisiones/exportaciones previas siguen cubiertos por la regresion.
Los respaldos y resultados de ejecucion permanecen fuera de Git.


## Auditoría de dependencias y aislamiento de conectores (2026-10-16)

Instalación nueva de las 50 distribuciones en Windows x64 CPython 3.12.14,
fuera del entorno original, con ruedas descargadas y SHA-256 comprobados mediante
requirements-win-py312.lock; instalación offline y pip check aprobados.
Regresión completa: **164 pruebas aprobadas, 4 advertencias, 216.16 s**.
Además, la prueba de administración entre organizaciones se repitió tras añadir
los límites al restablecimiento de contraseña: 1 aprobada, 2.70 s.
Las advertencias corresponden a TestClient/httpx, ast de ReportLab y dos usos
de FastAPI on_event; no se silenciaron.

pip-audit 2.10.1 sobre el entorno reconstruido: cero vulnerabilidades conocidas;
npm 11.6.2 audit: cero. Bandit 1.9.4: cero altas/medias, 13 bajas revisadas,
sin exclusiones de reglas. npm ci --ignore-scripts y TypeScript/Vite 6.4.4
aprobados (1582 módulos); git diff --check sin errores.

Restauración del respaldo a un destino nuevo: integrity_check ok y mismo SHA-256.
Las 72 tablas preexistentes conservan todos sus valores. Los tests cubren
contexto por organización/finalidad, acceso cruzado, historial, claves persistentes,
contraseñas antiguas, colisiones Mind, SSRF, entorno sin secretos y terminación
real del hijo al vencer el plazo. No se contactaron proveedores reales.
Alcance, avisos y límites en ../SECURITY_AUDIT.md; el proceso hijo no es un sandbox
del SO. Sin nuevas dependencias del motor, ejecución MVT ni despliegue.


## Aislamiento Windows y pentest local controlado (2026-10-16)

AppContainer por ejecución y Job Object: cuotas de CPU/memoria/procesos, sin red
para el analizador, entorno sin secretos, runtime stdlib RX e integridad previa,
creación suspendida, cierre/timeout sin fallback. Comprobación en el entrypoint
y JobEvent nuevo, sin modificar eventos ni resultados históricos.

**180 pruebas aprobadas**, cuatro advertencias de deprecación, 251.49 s sobre
el entorno reconstruido con requirements-win-py312.lock. Incluye 16 casos locales
con control positivo fuera del sandbox, canarios privados bloqueados, memoria
del padre, descendientes, loopback, recursos, salida excesiva, caída abrupta del
supervisor, corrupción del runtime, falta de configuración y preservación de un
trabajo completado ante fallo nuevo del sandbox. Pentest HTTP en 127.0.0.1 con
SQLite desechable: IDOR, inyección, origen, JSON, volumen, SSRF, cuotas, traversal,
exportaciones y framing ambiguo por socket. Sin proveedores ni evidencia real.

TypeScript/Vite aprobado (1582 módulos), pip check correcto, auditorías Python/npm
sin vulnerabilidades conocidas. Bandit ampliado a scripts: cero altas/medias,
14 bajas revisadas, sin suprimir reglas. diff sin errores.

Respaldo/restore con SHA-256 e integrity_check correctos; 72 tablas anteriores
comparadas por todos sus valores sin diferencias. No hay migración destructiva
ni motor externo. IA directa a localhost permanece bloqueada hasta una pasarela
separada. Windows es el único backend validado, no un pentest productivo.
Detalle en [pentest local](../LOCAL_PENTEST.md).

## E6: metadatos iOS, 2026-10-18

Motor 0.2.0: [Info.plist y Manifest.plist](E6_BACKUP_METADATA.md), lectores propios
1.0.0 con fixtures originales XML y variantes binarias. Oráculo manual de campos,
localizadores y fecha declarada; fuentes preservadas por hash. Pruebas de vacío,
corrupción, entidades XML sobre estructuras válidas, duplicados, tipos y cuotas.
CLI real con Python -S y catálogo de formatos compartido. Worker real aislado,
revisión e incorporación a informe/custodia, exportaciones estables tras otra
revisión, permisos de solo lectura y revocación. Un pendiente sintético 0.1.0 se
conserva y rechaza por versión; un examen 0.2.0 separado procesa la misma adquisición.

Regresión completa definitiva: **308 aprobadas, 1 omitida, 4 advertencias conocidas**.
Ollama real necesita activación explícita; no se modificó la IA. Suite focalizada
final reforzada: **19 aprobadas**, superpuestas con la regresión. Frontend: **52
aprobadas**, TypeScript/Vite correcto; no se hizo nueva inspección visual.

Comparación final: 74 tablas, esquema, 9 triggers y 116 archivos persistentes sin
diferencias; respaldo y restauración verificados con SQLite integrity_check y SHA-256.
Runtime nuevo `7e74dc7978ba3135545e208c`: 690 archivos comprobados en archivo y copia
restaurada, sin ejecutar el archivo privado ni reemplazar runtimes previos. No hubo
migración de datos ni dependencias nuevas. No se validaron adquisiciones reales,
SQLite/WAL/SHM, Manifest.db, archivos lógicos ni calidad de detección de spyware.
Se conserva la evidencia histórica de las etapas anteriores.


## Pasarela de IA local (2026-10-17)

Broker interno del supervisor con destino fijo y validación en dos AppContainers
sin red, sin excepciones de loopback. Autorización de organización/modelo/caso,
contexto opt-in y extractos SQL acotados. No ejecuta herramientas ni reusa
contextos del proveedor; toda salida requiere revisión humana. El motor propio
y los conectores conservan sus límites del SO.

**213 pruebas aprobadas**, cuatro advertencias de deprecación, 287.62 s desde
el entorno reconstruido con hashes. Incluye 33 pruebas nuevas de pasarela con
proveedor HTTP sintético, respuestas hostiles, goteo, volumen, manipulación de
validador, permisos, organizaciones/casos, Unicode y preservación. TypeScript/Vite
aprobado (1583 módulos), pip check correcto y auditorías Python/npm sin CVE conocidas.
Bandit: cero altas/medias, 15 bajas revisadas, sin supresiones.

Respaldo restaurado e integrity_check correctos; 72 tablas anteriores comparadas
por todos sus valores sin cambios. Sin migración destructiva, proveedor real,
modelo instalado ni despliegue. Ver [operación y límites](../LOCAL_AI_GATEWAY.md).
