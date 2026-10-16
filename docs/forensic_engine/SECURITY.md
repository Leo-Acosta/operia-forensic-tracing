# Seguridad efectiva y límites

API: sesión obligatoria, evidence:read/evidence:write según acción, caso y
organización no nulos verificados para cada ID de dispositivo/adquisición/indicador/
job/export. Los IDs de artefactos se contrastan con el resultado del job revisado.
Cache-Control:no-store en rutas nuevas. Worker vuelve a comprobar caso,
organización y permisos del operador, integridad y configuración antes de ejecutar
y antes de persistir. Nunca consulta otro caso para enriquecer una alerta.

Entradas: bytes BLOB originales preservados transaccionalmente; nombres simples,
sin rutas, archivos comprimidos ni extracción del sistema. Núcleo/CLI no ejecutan
contenido ni plugins. Parser acotado, entidades XML y claves duplicadas rechazadas.
El CLI exige archivo regular, rechaza enlace simbólico directo y no sobrescribe
salida. Los bytes de entrada se copian a memoria del hijo, no se modifican originales.

Recursos implementados: 5 MiB por fuente, 256 KiB por conjunto/500 indicadores,
5000 registros, 8192 caracteres por línea, profundidad 24; salida máxima 16 MiB,
timeout configurable 1–300 s (30 por defecto). Worker único por lock de almacenamiento
y claim atómico. Máximo 25 trabajos activos por organización. Cuota lógica de BLOB
por organización 128 MiB (configurable 5 MiB–2 GiB), reservada con escritor SQLite.
Incluye entradas, indicadores, resultados y snapshots; **no mide páginas SQLite,
metadatos ni archivos legacy**. Cuota física de disco pertenece al despliegue.

El hijo usa un runtime propio de solo lectura y AppContainer nuevo por invocacion.
El analizador no tiene capacidades de red; el conector HTTPS recibe internetClient
ademas de la politica organizacion/finalidad y allowlist de aplicacion. Job Object
aplica 256 MiB, 10 segundos de CPU de usuario, un proceso activo, restricciones de
UI y KILL_ON_JOB_CLOSE. El proceso nace suspendido; se asigna al Job antes de
reanudar. Entrada/salida por pipes, sin .env, secretos, site-packages o proxy.
El launcher deniega si no puede aplicar la contencion; no hay fallback POSIX.
Se probo cierre abrupto de un supervisor y terminacion del hijo por el kernel.
Los nuevos JobEvent registran sandbox_attached_v1 e identidad del runtime.
Ver [pentest y operacion](../LOCAL_PENTEST.md). No sustituye cuenta dedicada del
supervisor, firewall por proveedor, parches del SO ni un pentest de produccion.

Recuperación: bajo lock exclusivo, los estados activos del dueño anterior pasan a
interrumpido, no a completado; reintento explícito con historial. Configuraciones
completadas no se reescriben. Hashes detectan cambios accidentales; un administrador
capaz de modificar bytes y hashes no queda detenido por este diseño. No se promete
cifrado en reposo ni almacenamiento WORM. Backups requieren permisos/cifrado externos.

Auditoría de aplicación registra recepción, encolado/cancelación/reintento,
revisión y descargas; JobEvent conserva transiciones técnicas sin volcar evidencia
en logs. No hay retención/eliminación automática; se registra la política del caso.
Los borradores de UI se mantienen en memoria, no en localStorage.

La recuperacion local esta apagada por defecto y acotada al host. Los servicios
externos requieren concesiones explicitas y contencion. No hay IA en el núcleo del motor.

## Límite transversal implementado

`identity/isolation.py` instala criterios de lectura ORM en las sesiones HTTP
protegidas y valida referencias antes de flush. Casos sin organización no son
comodines. Un hijo histórico con organización NULL hereda únicamente el ámbito
del caso; no se reescribe. Los documentos sin caso solo son visibles a su
organización explícita. Se protegen casos, evidencia/custodia, informes/versiones,
presentaciones, exportaciones, contexto legal, IA, Mind, geo y sus alias.

La incorporación exige evidence:write y reports:write. Descargas de originales e
instantáneas comprueban SHA-256. Se rechazan traslados entre casos y referencias
cruzadas. Los archivos nuevos usan nombres únicos y creación exclusiva; la descarga
local exige pertenencia al depósito del caso. Eliminar un caso con datos móviles
recibe 409 antes de ejecutar borrados masivos.

Este control es de aplicación, no RLS de la base. Un nuevo router debe incluir
`enforce_scope`; un proceso fuera de HTTP debe validar su propio ámbito (como el
worker). SQL directo, administradores de almacenamiento y recuperación local de
identidad no quedan aislados por este mecanismo. No certifica un SaaS multiempresa.

Las referencias de caso/documento enviadas en path, query o JSON se comprueban
antes de ejecutar el endpoint, incluyendo exportadores. Los nuevos archivos de
exportación reservan destinos únicos: un nombre enviado no selecciona ni
sobrescribe un archivo anterior y las rutas se rechazan. Los informes móviles
exportan texto preservado; HTML lo escapa y PDF no reconstruye datos del caso vivo.


## Frontera de conectores

La etapa de proyecciones incorpora limites HTTP, origen, permisos por metodo,
concurrencia, JSON estricto, salida denegada por defecto, validacion/pinning de DNS,
retirada de shell, mapas/HTML inertes y recuperacion local deshabilitada por defecto.
Las proyecciones permanecen pasivas incluso si se habilita un proveedor externo.
Consultar [capas y contrato](../SECURITY_LAYERS.md). Limites por proceso, no firewall
ni cuotas distribuidas. Hubo auditoria CVE y pentest local acotado; no adquisiciones
reales ni evaluacion de infraestructura productiva.
