# Transición y recuperación

Base de esta entrega: 11a6761, feature/mobile-forensics-mvt, Git limpio. El commit
21bc0a4 y las 57 pruebas informadas no estaban disponibles: se verificaron 70 pruebas
reales del piloto antes de cambiarlo, más compilación frontend. La nueva rama es
feature/operia-native-mobile-engine. No se publica, despliega ni reescribe historia.

Referencias previas detectadas en mobile_forensics/router.py, service.py, schemas.py,
MobileForensics.tsx, docs/MOBILE_FORENSICS.md y pruebas. Retirada activa: importaciones,
revisiones y nuevas exportaciones legacy responden 410 con sesión/ámbito válido;
los GET históricos y descargas siguen disponibles, con origen externo y versión
declarada. No se ejecuta ni se busca un ejecutable externo. Se mantienen modelos y
bytes originales; ningún dato se convierte a operia_native.

Antes de editar esquema se ejecutaron backup y restore con scripts/sqlite_backup.py
en storage/temp/pre-native-engine-20261016.db y su copia de restauración. No se
respaldó mediante Git ni se aplicó una migración destructiva a la base del usuario.
La prueba de migración ensaya una base anterior con snapshot externo y verifica
sus bytes después de upgrade repetido y downgrade no destructivo.

Migración aditiva 20261016_0003 (depende de 0002): crea seis tablas native_mobile_*.
Bootstrap local también las registra/crea como en el resto del proyecto. La baseline
Alembic heredada no construye toda la plataforma vacía: seguir inicialización
existente. El downgrade conserva datos para evitar pérdida. No se probó PostgreSQL.

Operación de recuperación:
1. Detener API/worker y respaldar SQLite con su API backup, más storage completo y
   configuración por canal protegido (los archivos de evidencia legacy son externos).
2. Usar `python scripts/sqlite_backup.py backup ORIGEN DESTINO_NUEVO`; verificar con
   `verify DESTINO_NUEVO` y restaurar con `restore RESPALDO OTRA_RUTA_NUEVA`.
3. Probar hash e integrity_check y consultar casos/históricos antes de migrar la copia.
4. Reversión de código: volver a 11a6761 conservando tablas nuevas. Reversión completa
   de datos: apuntar OPERIA_DATABASE_URL/OPERIA_STORAGE_DIR a una restauración nueva
   verificada y consistente, con escritores detenidos. No sobrescribir una base activa.

La prueba de restauración es sintética; no es un plan de continuidad certificado.
Guardar respaldos cifrados, fuera de Git, con permisos/retención y otra copia física.

## Etapa de evidencia y aislamiento

Migración aditiva 20261016_0004, dependiente de 0003: agrega solamente
`native_mobile_evidence_integrations`. Upgrade repetible y downgrade que conserva
la tabla. No transforma exámenes, revisiones, exportaciones ni blobs históricos.
La prueba restaura una copia SQLite con un examen externo y compara sus bytes y
snapshot después de upgrade repetido/downgrade. Bootstrap registra la tabla nueva.

Respaldo local verificado: `storage/temp/pre-evidence-integration-20261016.db`,
con manifiesto SHA-256. Solo incluye SQLite; los archivos externos requieren su
respaldo separado. No usar una reversión de código para borrar las tablas nuevas.


Etapa siguiente: 0005, dependiente de 0004, agrega native_mobile_projections.
Upgrade repetible; downgrade conserva tabla y datos. El bootstrap tambien registra
Geo Trace para resolver la nueva FK en procesos de worker independientes.

Respaldo verificado: storage/temp/pre-projections-security-20261016.db. Su copia
restaurada projections-security-restore-check-20261016.db recibio upgrade dos veces
y downgrade no destructivo: las 71 tablas anteriores conservaron todos sus valores,
se agrego solo native_mobile_projections y SQLite integrity_check dio ok. Evidencia
de comprobacion en storage/test_runs/projections-migration-check.json, fuera de Git.
El respaldo SQLite no incluye archivos externos.
