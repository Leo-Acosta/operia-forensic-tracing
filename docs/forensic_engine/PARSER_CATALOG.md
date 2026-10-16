# Catálogo de lectores implementados

Todos versión 1.0.0, originales de este cambio y sin dependencias entre ellos.
Tamaño máximo de fuente 5 MiB; hasta 5000 registros; líneas hasta 8192 caracteres.

| ID | Entrada | Campos interpretados | Localizador | Exclusiones |
|---|---|---|---|---|
| operia.ios.configuration-profile | plist XML/binario de perfil con PayloadType=Configuration y PayloadContent lista | PayloadType, PayloadIdentifier, PayloadUUID; PayloadDisplayName opcional | /PayloadContent/N | CMS, firma, descifrado, certificados, valores secretos y semántica interna de payloads |
| operia.android.package-inventory | UTF-8, salida declarada de pm list packages o -f sin otras opciones | paquete y ruta APK si está presente | line:N, numeración desde 1 | flags adicionales, permisos, instalador, UID, versiones, ejecución o estado actual |
| operia.android.logcat-epoch | UTF-8, epoch con PID/TID, prioridad y tag; fracción de 3 a 6 cifras | epoch original, PID, TID, prioridad, tag, mensaje y URL HTTP(S) mencionadas | line:N | threadtime sin epoch, año/zona ambiguos, UID/formatos adicionales, registros binarios/multilínea |

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
