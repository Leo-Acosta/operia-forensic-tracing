# E6: lectura acotada de archivos lógicos iOS

Entrega 2026-10-18. Motor **0.5.0**, contrato `operia.forensic/1`, doce lectores y
diez formatos distintos. Lector propio `operia.ios.backup-logical-files` 1.0.0,
formato **`apple-backup-logical-set`**. Sin dependencias nuevas ni migraciones de datos.

## Selección preservada y asociación

El paquete original `operia.ios-logical-set/1` conserva un manifiesto y una selección
explícita de copias lógicas con bytes exactos en base64 y SHA-256 individual.
Se preserva como una adquisición nueva de un único expediente, sin referenciar o
reutilizar automáticamente adquisiciones de otros casos u organizaciones.

Contrato: claves exactas `schema`, `selection`, `manifest`, `files`; `selection`
debe ser `explicit_subset`. `manifest` contiene `format`, `sha256`, `content_base64`.
Solo admite los perfiles Files ya conocidos: `apple-backup-manifest-sqlite` o
`apple-backup-manifest-wal-set`. Cada elemento de `files` contiene únicamente
`file_id`, `sha256`, `content_base64`. No admite rutas, lectores elegidos por el
cliente, comandos SQL ni opciones de ejecución dentro del paquete.

Cada `file_id` debe aparecer una sola vez en la selección y corresponder a una
declaración Files interpretable con flags=1. Un ID desconocido, duplicado, de
directorio, con hash discordante o fuera de cuota rechaza el paquete completo
antes de publicar contenido. Dominios y rutas heredan los límites del manifiesto.
No se verifica la convención SHA-1 dominio/ruta del fileID, el modo físico del
archivo ni la autenticidad de la asociación: son declaraciones aportadas, no una
identidad criptográfica del dispositivo. Los hashes acreditan los bytes recibidos.

Los archivos regulares no seleccionados y los directorios se enumeran como
exclusiones. «No aportado» no significa ausente, eliminado ni limpio. El lector
no recorre directorios, no resuelve rutas de Manifest.db, no sigue enlaces ni abre
la copia de backup en el filesystem. Solo recibe los bytes del paquete preservado.

## Cobertura de contenido

| Tipo seleccionado por extensión declarada | Lectura | Exclusiones |
| --- | --- | --- |
| `.plist`, XML UTF-8 o bplist00 con raíz diccionario | Valores escalares str/bool/int/float y fecha plist declarada; contenedores dict/list con localizador de claves e índices escapados | Datos binarios, UID, NSKeyedArchiver en cualquier nivel, CMS, entidades XML, tags/atributos fuera del vocabulario, claves duplicadas y estructuras excesivas |
| `.txt`, `.log`, UTF-8/BOM opcional | Líneas de texto y localizador `line:N` | Binarios, controles C0 salvo tab/CR/LF, DEL, otros encodings, exceso de cuota y semántica específica del log |
| `.db`, `.sqlite`, `.sqlite3` | Catálogo ordinario de nombres/tipos de tablas e índices mediante el lector SQLite defensivo | Filas, mensajes, historial de aplicaciones, vistas/triggers/esquemas activos, cifrado y WAL/SHM del archivo lógico |
| Otras extensiones o contenido no interpretable | Declaración, tamaño y SHA-256 del archivo seleccionado | Contenido excluido con motivo; sin descompresión, ejecución ni extracción de contenedores |

Las fechas plist se muestran como valores declarados, **sin eventos en la línea
temporal**. Las líneas no prueban tráfico ni ejecución. El catálogo SQLite no
equivale a interpretar registros de aplicaciones. Los valores de texto/plist
pueden contener datos personales o secretos: la selección y su revisión deben
respetar el acceso del expediente; no se incorporan automáticamente a la IA.

Los errores de contenido afectan a ese contenido: se conserva el artefacto de
preservación del archivo y una exclusión, sin publicar un prefijo interpretado de
un archivo que exceda sus límites. Una exclusión puntual de BLOB/UID o string largo
puede coexistir con escalares compatibles, identificando su localizador.

## Límites y procedencia

- Paquete completo de hasta **5 MiB**, incluido base64 y manifiesto anidado.
- **1..32 archivos seleccionados**, hasta **256 KiB** cada uno.
- Texto: **64 KiB**, **128 líneas**, **2048 caracteres por línea**.
- Plist: preflight de entidades/profundidad, raíz diccionario, **1024 nodos** y
  **128 valores/exclusiones**, claves de hasta 128 caracteres y strings de hasta
  2048; diccionarios/listas reutilizan la defensa del lector plist existente.
- Contenido SQLite: perfil ordinario anterior, hasta 128 objetos, consultas fijas,
  configuración defensiva, autorizador y límites VM; sin consultas arbitrarias.
- Hasta **4129 artefactos**: una procedencia, 32 preservaciones y 32 × 128 registros
  de contenido, sujetos también a la cuota global de **16 MiB** de salida.
- Manifest mantiene 5000 filas Files; selección omitida, directorios, exclusiones
  del manifiesto y cola WAL no confirmada permanecen explícitos en cobertura.

`logical-set/provenance` identifica hash/formato de manifiesto y conteos de selección,
omisión y directorios. Si el manifiesto usa WAL, conserva la procedencia completa
de su instantánea, hashes de componentes/derivada y transformaciones. Cada archivo
usa `logical/<fileID>` con dominio/ruta declarados, tamaño y SHA-256. Los valores
usan `logical/<fileID>/plist/<clave escapada>`, `.../line:N` o `.../sqlite_schema/...`.
Son localizadores lógicos, no offsets físicos ni prueba de adquisición simultánea.
Cada registro de contenido incluye además `file_id`, `file_sha256` y `content_locator`; contenido
idéntico en archivos distintos conserva su contexto y no se agrupa como un mismo
registro. Valores iguales en claves o posiciones distintas de un mismo archivo
conservan su ubicación observada; no se deduplican por igualdad de valor ni se
infiere por ello independencia probatoria. Otros lectores mantienen su política
de correlación existente.

## Operación sobre copias

Preparar un paquete desde rutas elegidas explícitamente, sin explorar el backup:

```powershell
python -S scripts/preserve_ios_logical.py --manifest copia-Manifest.db --file aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa=copia-seleccionada.plist --output seleccion-nueva.json
```

El fileID del ejemplo es sintético; usar el declarado por el manifiesto preservado.
Repetir `--file fileID=ruta` para cada copia. La utilidad solo lee archivos regulares
seleccionados, dentro de cuota y sin symlinks directos; no abre SQLite ni sobrescribe
la salida. No garantiza una adquisición atómica de archivos vivos. Documentar cómo
se preservó y asoció cada copia. Para manifiesto WAL preparar primero el conjunto
[WAL/SHM](E6_WAL_SHM.md) y elegir `--manifest-format apple-backup-manifest-wal-set`.
Los sidecars de bases lógicas no se mezclan automáticamente; requieren examen
separado con el perfil de conjuntos SQLite correspondiente.

En Forense móvil elegir `apple-backup-logical-set` y subir el paquete JSON.
También disponible en CLI independiente:

```powershell
python -S -m operia.forensic_engine seleccion-nueva.json --platform ios --format apple-backup-logical-set --output resultado-nuevo.json
```

Preparar el runtime 0.5.0 antes de operar API/worker actualizados. Se mantienen
AppContainer sin red, Job Object y límites de CPU/memoria/procesos, permisos por
expediente, hashes, revisión versionada, incorporación explícita y custodia.
Los resultados/informes anteriores conservan sus bytes y versión. Un pendiente
de otra versión falla por incompatibilidad; crear otro examen explícito desde la
adquisición preservada. No editar configuraciones ni recalcular históricos.

## Aceptación y pendientes

Pruebas originales `tests/test_logical_files.py`: oráculo de cuatro archivos
seleccionados, uno omitido y un directorio; once artefactos, cuatro exclusiones y
canarios BLOB/filas SQLite no exportados. Plist XML/binario, texto de dos líneas,
SQLite real sintético, manifiesto principal/WAL, cuotas, corrupción, asociaciones
inválidas, CLI real `-S`, copias intactas y ausencia de descubrimiento automático.
Dos workers aislados reales, permisos de lectura/revocación/otra organización,
revisión posterior e informe/exportación históricos estables. Resultados definitivos
en [VALIDATION](VALIDATION.md) y auditoría de entrega.

Validación local Python 3.12.14/SQLite 3.53.1/Windows. Pendientes: corpus real por
OS y método de adquisición consistente, asociación física/cifrado/NSKeyedArchiver,
lectores específicos de aplicaciones, archivos mayores, otros formatos y la
[validación física de accesibilidad](../ASSISTIVE_ACCESSIBILITY.md). El soporte
no equivale a leer backups completos ni a detectar spyware de forma certificada.

Referencia primaria: [tipos y límites funcionales de plistlib](https://docs.python.org/3.12/library/plistlib.html).
Se reutilizan los lectores propios [Manifest/SQLite](E6_MANIFEST_SQLITE.md) y
[WAL/SHM](E6_WAL_SHM.md), sin copiar implementación ni corpus externos.
