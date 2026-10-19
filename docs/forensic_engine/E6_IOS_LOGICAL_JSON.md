# E6: ampliación de archivos lógicos iOS — JSON

Continuidad 2026-10-18. Motor **0.6.0**, lector
`operia.ios.backup-logical-files` **1.1.0**. Conserva el contrato
`operia.forensic/1`, doce lectores y diez formatos. Amplía el paquete
[`apple-backup-logical-set`](E6_IOS_LOGICAL_FILES.md) con contenido `.json`
seleccionado explícitamente y asociado por fileID a Files principal o WAL.
No agrega dependencias ni migraciones.

## Cobertura y exclusiones

JSON UTF-8/BOM opcional con raíz objeto o array: observaciones estructurales de
string, bool, int, float finito y null. No interpreta esquemas de aplicaciones,
fechas, rutas, comandos, URLs, referencias ni objetos serializados. Una URL queda
como texto; no se consulta. No publica eventos de línea temporal.

Los valores son la interpretación del decodificador JSON, no lexemas originales:
los flotantes usan la precisión binaria de Python y pueden redondearse o sufrir
underflow. La escritura decimal exacta se consulta en los bytes preservados;
no se usa esta observación como medición decimal de precisión arbitraria.

Cada artefacto `logical_json_scalar` conserva tipo/valor, `file_id`,
`file_sha256` y `content_locator`. El localizador es
`logical/<fileID>/json/<clave escapada o índice>`; `~` y `/` se escapan como
`~0` y `~1`. No representa offset físico. Valores idénticos en posiciones o
archivos distintos conservan su contexto. Los contenedores vacíos se indican como
exclusiones localizadas, sin inventar valores.

Límites por JSON: **64 KiB**, profundidad **24**, **1024 nodos de valores y
contenedores**, **128 escalares/exclusiones**, claves de **128 caracteres** y
strings de **2048**. Se rechazan claves duplicadas, números no finitos, Unicode
inválido, controles C0 (salvo tab/CR/LF en valores) y DEL. Se rechazan raíz escalar,
JSONL/NDJSON, comentarios, bytes extra y otros encodings. Una infracción excluye
**todo el contenido del archivo**, sin publicar prefijos; su declaración, tamaño
y hash permanecen. No se descifra, descomprime ni interpreta NSKeyedArchiver.

Las cuotas anteriores del paquete (5 MiB, 1..32 archivos de 256 KiB), asociación,
plist, texto y catálogo SQLite permanecen. Los archivos no aportados no equivalen
a ausentes o eliminados. No verifica autenticidad del dispositivo ni asociación
física; SHA-256 acredita los bytes aportados.

## Operación y preservación

Preparar la selección con `scripts/preserve_ios_logical.py` como en el tramo
anterior, eligiendo copias explícitas cuyo Manifest declare extensión `.json`.
No modificar la ruta declarada para forzar un lector. No se explora el backup.
Subir el paquete con el formato `apple-backup-logical-set` en Forense móvil.

Preparar un runtime nuevo **0.6.0** y reiniciar API/workers de forma controlada
antes de ejecutar trabajos con esta versión. Se conservan los
runtimes anteriores; no se sobrescriben sus fuentes. Los trabajos de versiones
anteriores conservan su versión y resultados; no se recalculan. Un pendiente
incompatible requiere un examen nuevo explícito, no editar su configuración.
Se mantienen AppContainer/Job, denegación por defecto por expediente y organización,
revisión versionada e incorporación explícita a informes. El JSON puede contener
datos sensibles; no se envía automáticamente a IA ni a conectores.

## Aceptación

Oráculo sintético con escalares de todos los tipos, claves escapadas, fechas y URL
tratadas como texto, null, posiciones repetidas, raíz array y BOM. Negativos:
claves duplicadas, NaN/Infinity/overflow, surrogate, controles, encoding, raíz,
profundidad, nodos, tamaño y cuotas. Verificación de exclusión completa y hash.
Recorridos con worker real para Manifest principal y WAL: concesión solo lectura,
revocación, organización ajena, original preservado e informe/exportación estables
tras otra revisión. Los resultados ejecutados se registran en
[VALIDATION](VALIDATION.md).

Pendientes: corpus autorizado real por versión de iOS/método de adquisición,
lectores específicos de aplicaciones, descifrado, archivos grandes y formatos
fuera de perfil. La cobertura estructural no acredita detección de spyware ni
lectura completa del backup. La validación física de accesibilidad sigue pendiente
según [su registro](../ASSISTIVE_ACCESSIBILITY.md).
