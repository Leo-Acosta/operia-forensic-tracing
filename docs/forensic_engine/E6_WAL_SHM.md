# E6: conjuntos SQLite/WAL/SHM preservados

Entrega 2026-10-18, motor **0.4.0**, salida `operia.forensic/1`.
Implementación propia sobre documentación de SQLite; no incorpora paquetes.
Once lectores registrados y nueve formatos distintos, conservando los anteriores.

## Alcance y exclusiones

| Formato / plataforma | Cobertura | Exclusiones |
| --- | --- | --- |
| `apple-backup-manifest-wal-set`, iOS | Última instantánea confirmada de Files, con los mismos cuatro campos declarativos del lector Manifest.db | BLOB file/NSKeyedArchiver, fechas, archivos físicos y registros de otras tablas |
| `sqlite-wal-catalog-set`, iOS y Android | Catálogo de tablas/índices ordinarios de la última instantánea confirmada | DDL, valores de filas, mensajes, cronología, consultas arbitrarias y objetos activos |
| SHM opcional | Cabeceras duplicadas de un bloque unix/win de 32768 bytes, checksum, orden nativo little/big, versión, página, sales, checksum del último commit, mxFrame/nPage y límites de backfill | Tablas hash, posiciones de páginas, marcas de lectores y locks; no se mmap-ea, ejecuta ni reconstruye el SHM |

Se exige una imagen principal WAL UTF-8 con páginas completas y cabecera válida,
un WAL versión 3007000 con 1..1024 frames completos y al menos un commit.
Se verifican cabecera, página, sales y cadena de checksums de **todos** los frames,
incluida la cola no confirmada. La cola válida posterior al último commit se
excluye con localizador/motivo. Truncamiento, checksum inválido, SHM inconsistente
o variante fuera del perfil rechazan el examen sin publicar instantáneas parciales.
No se rescata un prefijo válido de un archivo corrupto ni se supone actualizado el
estado de la base cuando falta WAL o no hay commits.

Los checksums no son firmas ni acreditan autenticidad. SQLite no proporciona en
estos campos una identidad criptográfica que pruebe la asociación DB/WAL; hashes,
sales y SHM compatibles tampoco prueban una adquisición simultánea. La procedencia,
el método de copia consistente y la asociación del conjunto requieren corroboración.
El lector no captura una base en ejecución ni infiere estados de bloqueo reales.

## Preservación y paquete de entrada

Se preserva un paquete JSON original como una adquisición del expediente: conserva
los bytes exactos de cada componente en base64 y su SHA-256 individual. El hash del
paquete queda en la adquisición, examen, resultado, custodia y exportaciones existentes.
No se mezclan adquisiciones de otros expedientes para completar un conjunto.

Contrato estricto `operia.sqlite-set/1`: claves `schema`, `database`, `wal`, `shm`.
Cada componente es `{ "sha256": "...", "content_base64": "..." }`; solo `shm`
puede ser `null`. Se rechazan claves extra, duplicadas, base64 inválido y hashes
discordantes. No hay nombres de archivo, rutas o SQL aportados dentro del contrato.
El paquete completo, incluido base64, debe ocupar como máximo **5 MiB**; no son
5 MiB por componente. SHM omitido y SHM vacío tienen estados diferentes.
Files mantiene un máximo de 5000 declaraciones, más un artefacto de procedencia
del conjunto: hasta 5001 artefactos, sujetos también a la cuota de salida de 16 MiB.

Preparar el paquete desde **copias preservadas** explícitas:

```powershell
python -S scripts/preserve_sqlite_set.py --database copia.db --wal copia.db-wal --shm copia.db-shm --output conjunto-nuevo.json
```

Omitir `--shm` únicamente cuando no fue aportado, documentándolo en la procedencia.
La utilidad lee archivos regulares seleccionados, sin abrir SQLite ni descubrir
sidecars; nunca sobrescribe la salida. No garantiza atomicidad de una copia en vivo.
Conservar además los originales y el registro del método de preservación.

En Forense móvil seleccionar el formato del conjunto y subir ese JSON. El selector
admite bases SQLite y paquetes JSON y explica la selección. También disponible:

```powershell
python -S -m operia.forensic_engine conjunto-nuevo.json --platform ios --format apple-backup-manifest-wal-set --output resultado-nuevo.json
```

## Imagen derivada y aislamiento

El lector trabaja exclusivamente con bytes privados en memoria. Aplica las páginas
confirmadas hasta el último commit, conservando la última versión aplicable de cada
página y el tamaño confirmado; respeta truncamientos y exige páginas de crecimiento.
La imagen derivada normaliza expresamente los bytes de cabecera 18/19 a rollback,
28..31 al tamaño confirmado y 92..95 al contador de cambios, para deserializarla
en SQLite en memoria. **Es una transformación documentada de una copia derivada**;
no es un checkpoint de los originales ni un descifrado o reparación de evidencia.

Un artefacto `sqlite-set/provenance` conserva hashes/tamaños de componentes, SHA-256
y tamaño derivado, límite de commit, frames comprobados, número de commits, tamaño
de página, estado SHM y lista exacta de transformaciones. Los registros derivados
usan localizadores `derived/...`. No se publican versiones intermedias, páginas
eliminadas ni fechas inventadas. SHM ausente se informa como `no_aportado`.
La salida representa el estado resultante y puede incluir filas ya presentes en
la base principal: no es un listado de cambios exclusivos del WAL ni atribuye
cada fila a un frame, página o celda física concreta.

La instantánea pasa por los lectores [SQLite acotados](E6_MANIFEST_SQLITE.md): mismo
autorizador, consultas fijas, defensa de esquema, límites de recursos y rechazo de
objetos activos. Se mantienen AppContainer sin red, Job Object, memoria/CPU/procesos
y cuota de salida. Los originales nunca se abren como bases en disco ni se generan
sidecars a su lado. El runtime anterior se conserva; preparar el nuevo antes de operar.

## Continuidad y aceptación

No hay migraciones de datos ni cambios en permisos. Concesión/revocación, organización,
expediente, adquisición, revisión e incorporación siguen las comprobaciones existentes.
Los resultados e informes anteriores conservan su versión y bytes. Pendientes de
otra versión fallan por incompatibilidad; crear un examen nuevo explícito sobre la
adquisición preservada. No reemplazar configuraciones ni recalcular históricos.

Pruebas originales en `tests/test_wal_sqlite.py`: WAL/SHM generados por SQLite real
con datos sintéticos y oráculo de dos filas, dos commits y flags 2/1; replay nativo
independiente para checksums big-endian, vectores manuales, crecimiento/truncamiento,
SHM en ambos órdenes, cola no confirmada, corrupciones, límites, esquemas activos,
paquete/CLI y tres workers reales. Incluyen permiso de solo lectura, revocación,
organización ajena, revisiones posteriores e informe/exportación históricos estables.
Los resultados definitivos se registran en [VALIDATION](VALIDATION.md) y auditoría.

Validación local Python 3.12.14, SQLite 3.53.1 y Windows. El formato de checksum WAL
big-endian no equivale a haber probado hardware big-endian. No se validaron backups
reales de iOS/Android, capturas concurrentes, otros VFS, SHM multibloque, WAL reciclado
con cola inválida, journaling rollback, cifrado, archivos lógicos ni exactitud de
detección. La [validación física de accesibilidad](../ASSISTIVE_ACCESSIBILITY.md)
permanece pendiente. E6 amplio y la aceptación productiva no están concluidos.

Referencias primarias: [formato SQLite/WAL y checksums](https://www.sqlite.org/fileformat2.html#walformat)
y [WAL-index unix/win](https://www.sqlite.org/walformat.html). Se consultaron conceptos
y campos; no se copiaron implementaciones ni corpus externos.
