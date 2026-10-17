# Validación verificable

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
