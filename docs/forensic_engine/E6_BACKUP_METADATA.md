# E6: metadatos de backups iOS, motor 0.2.0

Entrega del 2026-10-18. El motor amplía su catálogo de tres a cinco lectores.
Son implementaciones propias de lectura pasiva posteriores a la adquisición;
no se instala ni se ejecuta otro motor. El núcleo continúa usando solo stdlib.

## Contrato y cobertura

| Formato API/CLI | Lector 1.0.0 | Campos interpretados | Localizadores |
| --- | --- | --- | --- |
| `apple-backup-info-plist` | `operia.ios.backup-info` | Product Type, Product Version; opcionales Last Backup Date e Installed Applications | Claves raíz e índice original de aplicación |
| `apple-backup-manifest-plist` | `operia.ios.backup-manifest` | IsEncrypted, booleano estricto | `/IsEncrypted` |

Ambos aceptan plist XML UTF-8 y binario `bplist00` compatibles con `plistlib`
de CPython 3.12. Los fixtures propios declaran plist XML 1.0. No se afirma
compatibilidad con todas las versiones de iOS, Finder o iTunes. Una versión de
sistema escrita en el archivo es un dato declarado, no identificación autenticada.

Info requiere los dos campos de producto como textos no vacíos, hasta 256 caracteres.
Las aplicaciones son identificadores de hasta 255 caracteres con segmentos separados
por puntos; variantes rechazadas conservan su índice en `excluded`. La fecha opcional
debe ser una fecha plist y produce un evento `fecha_de_backup_declarada` UTC,
con reloj no contrastado. No representa un inicio de ataque ni actividad de una app.
Manifest requiere IsEncrypted de tipo booleano: ausencia o texto «false» no se
interpretan como backup sin cifrar. Incluso un booleano válido no prueba cifrado real.

Los identificadores personales, teléfono, número de serie, BackupKeyBag, Lockdown
y datos incrustados permanecen en la adquisición original; no se replican en los
artefactos derivados. El lector no carga archivos nombrados por el plist, no sigue
rutas ni URLs y no consulta dispositivos. Los inventarios de aplicaciones no se
convierten en indicadores Android ni demuestran instalación o ejecución actual.

El alcance es **metadatos de dos archivos aportados**. No incluye Manifest.db,
archivos lógicos del backup, restauración, descifrado, SQLite/WAL/SHM, CMS, archivos
comprimidos ni adquisición directa. La cobertura global sigue siendo parcial y toda
conclusión requiere revisión. No hay estimación de precisión o validación de spyware.

## Límites y controles

- 1 MiB por archivo de metadatos; no se amplía el límite global del motor.
- Preflight XML: hasta 52 elementos anidados y 50000 elementos totales, sin entidades.
- Binario: hasta 20000 objetos declarados antes del parseo; árbol de hasta 24 niveles
  y 50000 nodos tras parsear.
- Hasta 5000 registros, incluyendo metadatos y fecha; sobrecuota o estructura
  obligatoria inválida no publica un resultado parcial.
- Claves duplicadas rechazadas y mensajes de error controlados.
- Se mantienen AppContainer, Job Objects, ausencia de red, runtime verificado,
  memoria/CPU/procesos/salida acotados y rechazo sin fallback.

El formato original se preserva por SHA-256. Un plist vacío no acredita ausencia de
backups. Un plist incompatible/corrupto no produce artefactos utilizables. La exclusión
de una aplicación inválida queda documentada como cobertura incompleta.

## Referencias y procedencia

La [documentación de plistlib de Python 3.12](https://docs.python.org/3.12/library/plistlib.html)
describe los contenedores XML y binarios. La referencia primaria de claves de backup
es [idevicebackup2.c, revisión 360703bb34d87b45ba981f5984c5d3fc990028fa](https://cgit.libimobiledevice.org/libimobiledevice.git/tree/tools/idevicebackup2.c?id=360703bb34d87b45ba981f5984c5d3fc990028fa):
su construcción de Info y consulta de Manifest permiten documentar el subconjunto
de metadatos. Esto no convierte su implementación en una especificación oficial
completa de Apple. Se consultaron nombres y tipos; no se copió código, pruebas,
reglas ni muestras, ni se incorporó esa herramienta como dependencia.

Los dos fixtures del repositorio son originales, mínimos y sintéticos. El oráculo
manual de Info espera cinco registros: dos productos, fecha UTC
`2024-01-02T03:04:05.000000Z` y dos aplicaciones. Manifest espera una declaración
de cifrado y ninguna fecha. La variante binaria se genera con plistlib y debe dar
los mismos datos semánticos, manteniendo el hash de su propia fuente.

## Operación y continuidad

1. Detener API y workers antes de actualizar el código del runtime en uso.
2. Preparar el runtime nuevo con `python scripts/prepare_worker_sandbox.py` desde
   el entorno CPython 3.12 auditado. No editar ni eliminar el runtime anterior.
3. Iniciar API y worker sobre la misma base/almacenamiento autorizado.
4. En **Forense móvil**, seleccionar un dispositivo iOS y uno de los formatos
   nuevos, preservar el archivo con su autorización y crear el examen.
5. Revisar artefactos, fecha declarada, advertencias y exclusiones. Incorporar una
   revisión al expediente y generar sus exportaciones con los controles existentes.

La interfaz obtiene los formatos del catálogo; no requiere un selector paralelo.
Ejemplo CLI aislado de dependencias web, sobre un fixture original:

```powershell
python -S -m operia.forensic_engine tests/fixtures/native_mobile/backup-info.plist --platform ios --format apple-backup-info-plist --output storage/temp/e6-info-result.json
```

No sobrescribir una salida existente. La CLI local no es, por sí sola, la prueba
de contención del worker. Los ensayos de integración ejecutan además el hijo real
en el runtime AppContainer nuevo.

Los trabajos completados, sus resultados 0.1.0, revisiones y exportaciones no se
recalculan. Un pendiente con configuración de otra versión se rechaza mediante
`engine_version_or_configuration_mismatch`; crear un examen nuevo desde la misma
adquisición, sin reescribir el trabajo anterior. La actualización no realiza
migraciones de datos ni cambia concesiones por expediente.

## Aceptación, recuperación y pendientes

Las pruebas verifican XML/binario, oráculo manual, hashes, duplicados, entradas
vacías/corruptas/hostiles, tipos estrictos, presupuestos, lectura sin dependencias
web y ejecuciones reales del worker sobre las muestras sintéticas. Los casos de
integración incluyen revisiones, custodia/informe, exportación preservada y
denegación/revocación por expediente. La regresión general conserva también los
controles organizacionales y los históricos externos.

La [auditoría E6](../audits/e6-backup-metadata-20261018.json) registra los resultados
finales: regresión general **308 aprobadas, 1 omitida y 4 advertencias conocidas**;
suite final reforzada de metadatos/CLI/integración **19/19 aprobadas**; frontend
**52/52** y build TypeScript/Vite correctos. La omisión requiere activar Ollama real;
no cambió la IA en esta etapa. Las suites se superponen y no se suman como casos únicos.
Respaldo privado: `storage/temp/e6-ios-backup-metadata-20261018`; base y
116 archivos restaurados y comprobados. La base habitual permanece sin migrar.
El runtime nuevo se archiva y se comprueba por manifiesto en un destino de
restauración nuevo. No se sobrescriben la instalación ni los datos previos.

Pendientes de ampliación: SQLite/Manifest.db, WAL/SHM, archivos lógicos,
variantes de bugreport e inventarios Android adicionales, y validación con muestras
reales autorizadas. La validación física de accesibilidad sigue en
[su matriz](../ASSISTIVE_ACCESSIBILITY.md). Este tramo no cierra el SaaS ni acredita
operación productiva. El registro de horas humanas no se incrementa por duración
de procesos de IA o pruebas.
