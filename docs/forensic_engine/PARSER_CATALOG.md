# Catálogo de lectores implementados

Lectores versión 1.0.0, de implementación propia y sin dependencias entre ellos.
Fuente global de hasta 5 MiB; los metadatos de backup se limitan a 1 MiB.
Hasta 5000 registros; los lectores de líneas limitan cada línea a 8192 caracteres.

| ID | Entrada | Campos interpretados | Localizador | Exclusiones |
|---|---|---|---|---|
| operia.ios.configuration-profile | plist XML/binario de perfil con PayloadType=Configuration y PayloadContent lista | PayloadType, PayloadIdentifier, PayloadUUID; PayloadDisplayName opcional | /PayloadContent/N | CMS, firma, descifrado, certificados, valores secretos y semántica interna de payloads |
| operia.android.package-inventory | UTF-8, salida declarada de pm list packages o -f sin otras opciones | paquete y ruta APK si está presente | line:N, numeración desde 1 | flags adicionales, permisos, instalador, UID, versiones, ejecución o estado actual |
| operia.android.logcat-epoch | UTF-8, epoch con PID/TID, prioridad y tag; fracción de 3 a 6 cifras | epoch original, PID, TID, prioridad, tag, mensaje y URL HTTP(S) mencionadas | line:N | threadtime sin epoch, año/zona ambiguos, UID/formatos adicionales, registros binarios/multilínea |
| operia.ios.backup-info | Info.plist XML UTF-8/binario con Product Type y Product Version | producto, versión declarada, fecha plist opcional e inventario de aplicaciones opcional | /Product Type, /Product Version, /Last Backup Date, /Installed Applications/N | datos personales, archivos incrustados, adquisición completa e instalación actual |
| operia.ios.backup-manifest | Manifest.plist XML UTF-8/binario con IsEncrypted booleano | declaración de cifrado | /IsEncrypted | claves, Lockdown, descifrado, Manifest.db y archivos lógicos |
| operia.ios.backup-manifest-db | imagen SQLite UTF-8 rollback, tabla Files de cinco columnas | fileID, domain, relativePath, flags 1/2 | Files/fileID:<id> | BLOB file, fechas, archivos físicos, WAL/SHM y variantes de esquema |
| operia.ios.sqlite-catalog | imagen SQLite del perfil ordinario | tipo, nombre y tabla de tablas/índices | sqlite_schema/<tipo>/<nombre escapado> | DDL, columnas, filas, vistas/triggers y esquemas activos |
| operia.android.sqlite-catalog | mismo perfil SQLite acotado | tipo, nombre y tabla de tablas/índices | sqlite_schema/<tipo>/<nombre escapado> | DDL, columnas, filas y recuperación de registros |

Payloads inválidos y líneas no reconocidas conservan localizador y motivo en
exclusiones. Las claves plist duplicadas se rechazan; profundidad/nodos son
acotados y no se resuelven entidades XML. Ningún archivo se instala ni ejecuta.
Se preserva todo el original; solo se replican campos interpretados en artefactos.
Los localizadores plist identifican claves, no offsets físicos inventados.

El perfil aportado no demuestra estar instalado. El inventario no demuestra
ejecución de paquetes. Una URL en texto no prueba que hubo conexión. Las cabeceras
logcat no son eventos. Los registros duplicados se enlazan y no duplican alertas.

Oráculos manuales y datos: tests/fixtures/native_mobile/README.md. No se usaron
adquisiciones reales ni salidas de otro motor como verdad de referencia.

Motor actual 0.3.0: ocho lectores y siete formatos distintos. [Contrato y límites
SQLite](E6_MANIFEST_SQLITE.md); se mantiene el [tramo anterior](E6_BACKUP_METADATA.md).
Los perfiles SQLite requieren los controles de la compilación validada, rechazan
esquemas incompatibles y nunca abren la evidencia como una base de datos en disco.
