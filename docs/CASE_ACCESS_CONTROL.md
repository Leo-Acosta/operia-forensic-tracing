# E3 — permisos por expediente

Fecha: 2026-10-17. Base: `fb9cc01`. Entorno: Windows y SQLite local.

## Política

El permiso efectivo combina sesión activa, organización activa, rol y concesión del
expediente. Los usuarios sin concesión no acceden a expedientes existentes, aunque
su rol permita trabajar con casos. No se asignan permisos retrospectivos por nombre,
responsable declarado o pertenencia a la organización.

El administrador tiene acceso a los expedientes de su propia organización y es el
único que administra concesiones. Esta excepción explícita permite recuperar el
acceso a los expedientes anteriores sin abrirlos a todos los usuarios. Un administrador
no puede acceder a otra organización. Su acceso implícito no se revoca con una ACL:
para retirarlo se debe cambiar su rol o desactivar su cuenta mediante Identidad;
ese flujo audita el cambio e invalida sus sesiones anteriores.

Los creadores reciben concesiones explícitas en la misma transacción que crea el
expediente, tanto por la ruta canónica como por el alias legal anterior. El rol sigue
limitando las operaciones: una concesión de escritura no convierte a un lector en
analista ni concede acceso a configuración.

| Capacidad | Alcance |
| --- | --- |
| `read` | Consultas, listados, relaciones y contexto del expediente |
| `write` | Edición general del expediente y sus datos operativos |
| `evidence` | Incorporar evidencia, adquisiciones, dispositivos y custodia |
| `analysis` | Análisis, trabajos nativos, hallazgos, hipótesis, Geo e IA |
| `review` | Revisiones profesionales y rúbricas |
| `participants` | Gestión de participantes |
| `reports` | Generación y edición de informes y presentaciones |
| `approve` | Aprobación/finalización de informes y sellado final |
| `export` | Exportaciones y descargas de originales y archivos |

Todas requieren lectura. Los flujos compuestos requieren las capacidades de cada
registro afectado: por ejemplo, incorporar un análisis como evidencia e informe
requiere análisis, evidencia e informes. Se mantienen los controles del rol de cada
ruta. Las políticas de organización y servidor siguen limitando los conectores.
Un contexto de IA sin expediente no habilita datos de un expediente no autorizado.

## Concesiones, revocaciones e historial

En **Detalle del caso → Permisos del expediente**, el administrador selecciona
usuario, capacidades y motivo. El historial muestra autor, fecha y decisión.
El panel conserva el estilo existente; el rediseño shadcn/ui corresponde a E4.

API autenticada:

- `GET /api/cases/{case_id}/access`: historial administrativo.
- `GET /api/cases/{case_id}/access/me`: capacidades asignadas y condición de administrador;
  las capacidades devueltas siguen sujetas a los permisos del rol.
- `POST /api/cases/{case_id}/access`: decisión con `user_id`, `access`, `reason`
  y, opcionalmente, `permissions`.

Ejemplo de concesión:

```json
{"user_id": 12, "access": "read", "permissions": ["read", "analysis"], "reason": "Asignación autorizada del análisis"}
```

`access: "revoked"` añade revocaciones para las capacidades seleccionadas. Sin
`permissions`, `read` concede lectura, `write` concede todas las capacidades y
`revoked` revoca todas. Las concesiones son aditivas: conceder solo lectura no
retira capacidades anteriores. Para reducir acceso, revocar expresamente las
capacidades que se retiran. Una lista vacía se rechaza.
También se pueden revocar concesiones de una cuenta inactiva antes de reactivarla;
no se conceden permisos nuevos a cuentas inactivas.

Revocar lectura bloquea todo el expediente, aunque existan otras concesiones.
Restaurar lectura reactiva las capacidades que no fueron revocadas; para retirar
todo acceso se debe revocar el conjunto completo.

Cada capacidad tiene eventos sucesivos en `case_access_events`. La última decisión
por usuario, expediente y capacidad define su estado. Los eventos no se actualizan
ni eliminan: guardas ORM y triggers SQLite rechazan ambas operaciones. Otro trigger
verifica que expediente, usuario y autor pertenezcan a la organización declarada.
La decisión y su `AuditLog` se confirman en la misma transacción. Los valores del
cliente no pueden sustituir al autor autenticado.

## Aplicación de la autorización

Los filtros de sesión cubren expedientes y registros relacionados, incluyendo
listados, búsquedas, conteos, auditoría, notas, informes, manifiestos y resultados
nativos. Las rutas móviles también usan el ámbito común y verifican el expediente.
Los accesos directos no disponibles responden 404; la falta de un permiso global
del rol puede responder 403. Los listados omiten los registros no autorizados.

Antes de persistir registros se vuelve a comprobar el permiso. Las escrituras ORM
y las decisiones de acceso se serializan con el bloqueo de escritura SQLite para
evitar que una revocación ya confirmada sea ignorada al guardar. Las operaciones
masivas ORM también reciben filtros. Esto no convierte sesiones internas de
mantenimiento sin actor en una interfaz pública autorizada: los procesos internos
deben conservar sus verificaciones explícitas.

El worker verifica usuario, rol, organización y lectura/análisis antes de ejecutar,
durante el procesamiento y antes de publicar. Si pierde autorización, termina el
proceso aislado y registra `scope_or_operator_invalid` o `scope_or_operator_changed`.
No publica resultados parciales. La última verificación y la publicación ocurren
bajo el mismo bloqueo que serializa las revocaciones. No se alteran trabajos ya
completados, adquisiciones originales ni snapshots previos.

Las respuestas API mantienen `Cache-Control: no-store`. El cliente descarta respuestas
de sesiones anteriores, incluso si el cambio ocurre durante la lectura del cuerpo;
un 401 tardío no cierra la sesión nueva. Las colecciones del expediente se vacían
al recargar y sus respuestas se validan contra expediente, sesión y solicitud actual.
El panel de permisos se desmonta al cambiar de usuario o expediente.

## Migración, preservación y recuperación

`20261017_0007_case_access.py` agrega una tabla, sus índices y tres triggers. Es
idempotente. No cambia filas anteriores ni concede acceso a usuarios históricos.
El downgrade conserva los eventos y protecciones. No se debe volver al código E2
para operar con usuarios restringidos: ese código no conoce las ACL.

Se conserva un respaldo SQLite previo y una copia de los 116 archivos persistentes
con verificación SHA-256 y ACL de Windows restringida. Se prueba la migración sobre
una copia restaurada y se compara cada fila de las 73 tablas anteriores. Tras la
migración se comprueban integridad, ausencia de concesiones retrospectivas y
preservación de archivos. Los detalles sanitizados y los resultados finales están
en [la evidencia E3](audits/e3-case-access-20261017.json).

La restauración debe hacerse con API y workers detenidos y con una versión que
conozca estas ACL. Restaurar una base anterior retira las decisiones posteriores
al respaldo; requiere una recuperación administrativa controlada, no una vuelta
automática al esquema de permisos anterior. No borrar archivos o históricos para
revertir la etapa.

## Pruebas y límites

Las pruebas nuevas cubren usuarios reales sintéticos de la misma organización,
denegación por defecto, capacidades, intersección con roles, conteos, referencias,
organizaciones distintas, archivos, manifiestos, creación por ambos alias,
inmutabilidad de decisiones, migración idempotente y revocación de trabajos en
tres momentos. También comprueban que los trabajos completados no cambian.

Resultado: 271 pruebas aprobadas en la regresión, una integración Ollama omitida
por requerir activación explícita, una prueba posterior de revocación de cuentas
inactivas aprobada y cinco pruebas del cliente aprobadas. El build TypeScript/Vite
pasó. Persisten cuatro advertencias de deprecación ya conocidas.

Las pruebas del cliente se ejecutan con:

```powershell
cd apps/web
npm test
npm run build
```

Estas pruebas usan el código TypeScript real transpilado y respuestas sintéticas;
no sustituyen el recorrido visual y de accesibilidad en navegador previsto para E4.
No se agregan dependencias ni se habilitan proveedores externos.

Se corrigió además el entorno de pruebas: los inicializadores de Cybercrime,
Geo Trace, Geo Proximity y Rúbricas ahora reciben el motor SQLite sintético, y
Geo Proximity también recibe su fábrica de sesiones aislada. Antes conservaban
referencias al motor local y crearon anticipadamente la tabla ACL vacía. La
comparación del respaldo confirmó que no alteraron ninguna fila histórica. Una
prueba nueva verifica que todos estos inicializadores usen la base sintética.

La protección es de aplicación y SQLite local, no almacenamiento WORM. Un
administrador del host puede alterar el programa, la base o los triggers. Los
respaldos locales no están cifrados ni sustituyen recuperación externa. Una
revocación impide nuevos accesos y la publicación de trabajos; no puede retirar
información ya descargada o leída por un usuario previamente autorizado. No hay
notificaciones push de revocación: la interfaz detecta la pérdida de acceso en su
siguiente consulta o acción. E4 conserva la validación visual integral pendiente.
