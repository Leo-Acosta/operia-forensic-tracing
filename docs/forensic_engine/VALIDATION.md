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
