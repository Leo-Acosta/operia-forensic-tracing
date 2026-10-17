# E2 — custodia append-only y rectificaciones versionadas

Fecha: 2026-10-17. Base de código: `3001850`. Alcance validado: aplicación local
Windows y SQLite, sin habilitar proveedores externos ni cambiar límites de workers.

## Modelo e invariantes

Los eventos existentes de `chain_of_custody_actions` conservan sus columnas y valores.
Una tabla nueva, `custody_ledger_entries`, añade procedencia y versiones a los eventos
nuevos. No hay backfill: los históricos sin ledger siguen sin una atribución nueva.
Un nombre declarado antiguamente no se convierte en una identidad autenticada.

Cada actuación nueva de aplicación recibe una entrada de ledger con raíz, versión 0,
identidad del usuario autenticado, nombre y rol al registrar, fecha de incorporación
y tipo de evento. También cubre actuaciones automáticas de otros módulos y las
integraciones nativas, a través de la sesión de base de datos. La herramienta que
origina la actuación sigue identificada en sus campos; el actor es quien inició
el flujo autenticado. La actividad interna sin actor de solicitud queda identificada
como proceso interno, sin inventar una identidad personal.

La rectificación añade otro evento y otra entrada de ledger. Registra:

- Raíz original, evento inmediatamente anterior y versión incremental.
- Motivo obligatorio y campos declarados como corrección, preservados en changes_json.
- Actor obtenido de la sesión, nunca de los campos enviados por el cliente.
- Fecha de registro UTC y, opcionalmente, fecha declarada del hecho con zona explícita.
- Representación ISO del tiempo declarado y normalización a UTC separadas.

La descripción del evento nuevo identifica qué actuación rectifica y su motivo,
de modo que las bitácoras e informes futuros que muestran los eventos distinguen
la corrección. El historial original no se reemplaza ni su estado cambia de forma
retrospectiva. Los valores declarativos, como validated_by, no equivalen a una
autenticación independiente de terceros ni a aprobación pericial certificada.

Solo puede rectificarse el último evento de una cadena. Una solicitud basada en
una versión antigua devuelve 409. La restricción única (raíz, versión) y la
transacción impiden dos sucesores simultáneos; el perdedor revierte el evento
provisional y no deja un huérfano. La auditoría se incorpora en la misma transacción.

## API y permisos

- `POST /api/evidence/custody-actions`: nueva actuación, contrato existente.
- `POST /api/evidence/custody-actions/{action_id}/rectifications`: nueva rectificación.
- `GET /api/evidence/custody-actions/{action_id}/history`: cadena completa, sin ocultar versiones.
- PUT/DELETE de actuaciones, tanto canónicos como del alias legal-report: 409.
- PATCH no está implementado; no proporciona una vía alternativa de modificación.

Ejemplo de cuerpo para rectificar:

```json
{
  "reason": "Corrección fundamentada del registro",
  "changes": {"detailed_description": "Detalle corregido"},
  "occurred_at": "2026-01-02T10:00:00-03:00"
}
```

`occurred_at` es opcional; no se supone una fecha o zona ausente. Las propiedades
adicionales se rechazan. No se admiten cambios de caso, evidencia, autor, raíz o
versión. Se limita el motivo a 2000 caracteres, cada valor corregido a 16000
caracteres y el conjunto de valores a 32 KiB UTF-8. Se mantienen permisos
evidence:write/read, sesión y aislamiento organizacional existentes. Referencias
de distintos casos o de otra organización se rechazan. Las ACL individuales por
expediente son E3 y todavía no se implementan en esta etapa.

## Protección en aplicación y SQLite

Un guard global ORM bloquea cambios y borrados de eventos y ledger, incluso fuera
de una solicitud HTTP. Los triggers SQLite rechazan UPDATE/DELETE sobre ambas
tablas, cubriendo SQL directo y operaciones masivas que omitan el guard ORM.

También se impide eliminar un caso o evidencia con custodia. Hay comprobación
antes del borrado en la API, guard ORM y triggers de protección de padres. Esto
evita borrar informes/exportaciones antes de descubrir una custodia que preservar.
Los casos sin custodia siguen sujetos a las reglas de borrado anteriores.

Estos controles no son almacenamiento WORM ni una firma digital. Un administrador
con control del archivo SQLite o del host puede retirar triggers o sustituir datos.
Se requieren controles de host, backups externos y auditoría independiente según
el despliegue. No se certificó un backend PostgreSQL: el instalador de triggers
rechaza otros dialectos y no ofrece una alternativa que simule la protección.

## Interfaz

La custodia muestra identificador de evento, raíz, versión y actor registrado.
Los registros antiguos sin ledger aparecen como históricos sin atribución
retrospectiva. No hay acción de eliminación o edición. Rectificar abre un formulario
con motivo obligatorio y agrega una actuación nueva. Si ya hay sucesor se indica
que existe una rectificación posterior. El backend vuelve a validar el conflicto.

El borrador se descarta al cambiar de caso o sesión. Las respuestas se muestran
como texto; no se ejecutan HTML ni instrucciones de una descripción. Esta etapa
no incorpora el rediseño premium E4.

## Migración y recuperación

Migración aditiva: `20261017_0006`, después de `20261016_0005`. Se ensayó upgrade
repetido y downgrade no destructivo sobre copia de SQLite; las tablas anteriores
permanecieron iguales. La migración importa sus modelos de referencia para poder
resolver claves foráneas en un proceso limpio. El bootstrap local instala el ledger
y protecciones antes de que la API esté disponible.

La migración se aplicó a la base local en transacción SQLite BEGIN IMMEDIATE,
después de comprobar que no había listener de la API en el puerto local 8020.
No se ejecutaron el bootstrap completo ni otras migraciones sobre los históricos.
La inspección verifica tabla/triggers realmente presentes; el indicador heredado
de versión base no acredita por sí solo todas las migraciones de Alembic.

Respaldos privados, fuera de Git:

- `storage/temp/pre-e2-custody-20261017.db`: SQLite previo, con manifiesto.
- `storage/temp/e2-data-backup-20261017/`: SQLite previo y 116 archivos persistentes,
  incluidos los archivos de configuración/clave que existían.
- `storage/temp/e2-migration-rehearsal-20261017.db`: copia ensayada, sin backfill.
- `storage/temp/e2-data-restore-20261017/`: archivos y respaldo previo restaurados y verificados.
- `storage/temp/post-e2-custody-20261017.db`: respaldo posterior con protecciones.
- `storage/temp/e2-post-restore-check-20261017.db`: restauración posterior verificada.

Las copias se protegen por ACL para usuario actual, SYSTEM y administradores.
Son locales y no cifradas; no reemplazan un respaldo externo. Copias de archivos y
SQLite no constituyen un snapshot atómico transversal. Se excluyen temporales,
runtimes derivados, pruebas y modelos Ollama externos al proyecto.

El downgrade conserva la tabla y los triggers: no borra revisiones ni reabre la
edición. No restaurar la base previa encima de una base que ya tenga nuevas
actuaciones, porque perdería esas incorporaciones. La recuperación se ensaya en
destinos nuevos, con API/workers detenidos, verificando manifiestos e inventarios.

## Verificación

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_custody_ledger.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

Se prueban inmutabilidad canónica/alias/ORM/SQL, protección de padres, identidad
autenticada, histórico sin backfill, versiones y conflictos, concurrencia real de
dos sesiones, límites de campos, zonas horarias, permisos y accesos cruzados.
Los tests verifican que los informes/versiones/manifiestos existentes y los bytes
exportados no se modifican al rectificar. Rectificar no regenera informes ni
exportaciones; nuevas generaciones/exportaciones son nuevas actuaciones y deben
identificar el estado considerado. No se certifica que cualquier renderización
futura de un informe antiguo basado en datos vivos sea un snapshot histórico.

Las pruebas y adquisiciones utilizadas son sintéticas. No se incorporaron
proveedores ni se ejecutó malware o evidencia real.

La exportación antigua de bitácoras ya no reutiliza un nombre fijo: cada petición
crea un archivo nuevo mediante el generador de rutas existente. Se comprobó que
exportar después de rectificar no sobrescribe la bitácora anterior.

## Resultado final

Regresión completa: **256 aprobadas**, una omitida (Ollama real optativo), cuatro
advertencias de deprecación preexistentes, 403,69 s. Incluye 23 casos nuevos de
ledger/custodia. La integración focalizada anterior aprobó 32 pruebas. Después
del ajuste final de la exportación antigua se repitió su prueba de preservación:
una aprobada, con informe, versiones y archivos anteriores intactos.

Build TypeScript/Vite 6.4.4 aprobado, 1583 módulos. La comprobación de respuestas
tardías en el formulario se implementó con contexto de caso/sesión y se verificó
por compilación y revisión de código; sin nueva inspección visual ni suite de
navegador en esta etapa. Bandit final: cero altas/medias y 15 bajas revisadas,
cero errores, sin suprimir reglas ni añadir dependencias de aplicación.

La base local tiene 73 tablas: las 72 anteriores conservan todos sus valores y
la nueva tabla está vacía, sin backfill. Los seis triggers están instalados.
Los 116 archivos persistentes y su inventario coinciden con respaldo y restauración.
El respaldo posterior y su copia restaurada tienen integrity_check correcto y SHA-256:
`1b02346c363201189530e28855b76455bd5472ba449e066ff7625f9e7ccb23a9`.

[Registro técnico sanitizado](audits/e2-custody-20261017.json).
La próxima etapa es E3: permisos individuales por expediente. E2 no acredita
inmutabilidad frente al administrador del host ni preparación SaaS productiva.
