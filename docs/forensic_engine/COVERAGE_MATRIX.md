# Matriz final de cobertura E6 — motor 0.7.0

Alcance congelado para esta entrega: **13 lectores / 11 formatos distintos**,
contrato `operia.forensic/1`. Las dos variantes de catálogo son lectores por
plataforma del mismo formato. Solo el lector lógico está en versión 1.1.0;
los demás están en 1.0.0. Esta es la matriz vigente; se conserva la
[matriz anterior completa](history/COVERAGE_MATRIX_before_E6_closure_0.7.0.md).

## Límites comunes y significado de validación

- Fuente completa hasta **5 MiB** y salida canónica hasta **16 MiB**. El límite
  específico menor prevalece. Los paquetes cuentan el JSON/base64 completo.
- CLI sobre archivo seleccionado; API sobre adquisición preservada de un caso.
  Sin descubrir archivos, conectar al dispositivo, reparar originales o abrir
  enlaces. Worker Windows AppContainer/Job, red deshabilitada para el motor.
- Runtime validado: Python 3.12.14 / SQLite 3.53.1 / Windows. Linux, macOS,
  PostgreSQL y otras compilaciones no quedan validados por estas pruebas.
- Todos los lectores tienen fixtures sintéticos originales y pruebas negativas.
  El perfil iOS cuenta además con una demostración de artefacto público externo.
  **Ningún lector tiene validación con adquisición real de un dispositivo.**
  La versión de OS escrita en una muestra es una declaración, no certificación.
- Integridad por hash, lectura y detección son capacidades distintas. Ausencia
  de alertas o registros no acredita ausencia de compromiso. Revisión requerida.

## Catálogo cerrado

| Plataforma / lector | Formato API/CLI | Cobertura y límites específicos | Exclusiones principales / referencia |
| --- | --- | --- | --- |
| iOS · operia.ios.configuration-profile 1.0.0 | apple-profile-plist | XML/bplist Configuration; hasta 5000 payloads; árbol de hasta 24 niveles/50000 nodos; tipo/identificador/UUID y nombre declarado | Sin firma CMS, cifrado, instalación/actividad ni interpretación de DNSSettings. No interpreta automáticamente todos los campos del perfil. [Catálogo](PARSER_CATALOG.md) |
| Android · operia.android.package-inventory 1.0.0 | android-pm-packages | UTF-8, pm list packages o -f; hasta 5000 registros, 8192 caracteres por línea; paquete y ruta APK declarada | Otros flags, permisos, UID, versiones, instalación y ejecución actual. [Catálogo](PARSER_CATALOG.md) |
| Android · operia.android.logcat-epoch 1.0.0 | android-logcat-epoch | UTF-8 epoch con PID/TID/tag/prioridad; 5000 registros, 8192 caracteres por línea, fracción de 3..6 cifras; URL HTTP(S) mencionada hasta 2048 caracteres | Threadtime, registros binarios/multilínea, fechas ambiguas; URL mencionada no prueba conexión. Reloj no contrastado. [Catálogo](PARSER_CATALOG.md) |
| iOS · operia.ios.backup-info 1.0.0 | apple-backup-info-plist | 1 MiB; XML UTF-8/bplist; producto/versión hasta 256 caracteres, fecha plist e inventario opcionales; hasta 5000 artefactos en total, IDs de apps hasta 255 caracteres | Identificadores personales, datos incrustados, instalación actual, autenticación de backup/OS. [Metadatos](E6_BACKUP_METADATA.md) |
| iOS · operia.ios.backup-manifest 1.0.0 | apple-backup-manifest-plist | 1 MiB; XML UTF-8/bplist; IsEncrypted booleano estricto | Claves, Lockdown, descifrado y verificación criptográfica del cifrado. [Metadatos](E6_BACKUP_METADATA.md) |
| iOS · operia.ios.backup-manifest-db 1.0.0 | apple-backup-manifest-sqlite | Imagen principal UTF-8 rollback; Files con cinco columnas exactas; hasta 5000 filas; fileID, dominio, ruta y flags 1/2 | BLOB file, fechas, permisos, archivos físicos, otras tablas, WAL/SHM. No verifica asociación física ni convención SHA-1. [SQLite](E6_MANIFEST_SQLITE.md) |
| iOS · operia.ios.sqlite-catalog 1.0.0 | sqlite-schema-catalog | Imagen principal del perfil ordinario; hasta 128 objetos; nombres/tipos de tablas e índices | DDL, columnas, filas, vistas/triggers, esquemas activos, WAL/SHM y recuperación. [SQLite](E6_MANIFEST_SQLITE.md) |
| Android · operia.android.sqlite-catalog 1.0.0 | sqlite-schema-catalog | Mismo catálogo ordinario, hasta 128 objetos, plataforma Android declarada | No interpreta mensajes, historial o filas de aplicaciones. [SQLite](E6_MANIFEST_SQLITE.md) |
| iOS · operia.ios.manifest-wal-set 1.0.0 | apple-backup-manifest-wal-set | operia.sqlite-set/1; hasta 1024 frames; último commit, Files hasta 5000 filas y procedencia; SHM opcional de 32768 bytes con cabeceras contrastadas | Cola sin commit excluida; sin versiones intermedias, BLOB, borrados, asociación/atomicidad autenticada ni locks/tablas hash SHM. [WAL/SHM](E6_WAL_SHM.md) |
| iOS · operia.ios.sqlite-wal-set 1.0.0 | sqlite-wal-catalog-set | Mismo conjunto, hasta 1024 frames; catálogo hasta 128 objetos y procedencia de derivada | Filas, borrados, otros perfiles SQLite y SHM completo. [WAL/SHM](E6_WAL_SHM.md) |
| Android · operia.android.sqlite-wal-set 1.0.0 | sqlite-wal-catalog-set | Mismo perfil de conjunto/catálogo, plataforma Android declarada | Sin semántica de aplicaciones ni validación de OS real. [WAL/SHM](E6_WAL_SHM.md) |
| iOS · operia.ios.backup-logical-files 1.1.0 | apple-backup-logical-set | operia.ios-logical-set/1; 1..32 archivos de hasta 256 KiB; manifiesto Files principal/WAL; hasta 4129 artefactos. Plist escalar, texto UTF-8, JSON estructurado y catálogo SQLite | Omitidos/directorios explícitos; sin recorrido, BLOB/UID/NSKeyedArchiver, filas Safari automáticas, cifrado, asociación física autenticada ni WAL de cada archivo lógico. [Selección](E6_IOS_LOGICAL_FILES.md), [JSON](E6_IOS_LOGICAL_JSON.md) |
| iOS · operia.ios.safari-history 1.0.0 | ios-safari-history-sqlite | Imagen principal ordinaria; history_items/history_visits y columnas permitidas; 500 filas por tabla, URL/título hasta 2048 caracteres; hasta 500 artefactos | Sin elegir época de visit_time, eventos temporales, BLOB, perfiles, etiquetas, sincronización, redirecciones, WAL/SHM ni otras apps. [Safari](E6_IOS_APP_SQLITE.md) |

## Sublímites y rechazo

**Plist de metadatos de backup:** preflight XML hasta 52 niveles/50000 elementos,
sin entidades; binario hasta 20000 objetos declarados; árbol hasta 24 niveles y
50000 nodos. El perfil Configuration usa su propia validación; no se le atribuye
el preflight específico del lector de metadatos.

**SQLite ordinario:** 128 objetos, 64 columnas, valores hasta 256 KiB, SQL fijo
hasta 8192 bytes y 100000 pasos VM comprobados cada 1000 operaciones. Controles
SQLite defensivos obligatorios y autorizador específico. Sin adjuntos, funciones,
extensiones, escrituras, vistas/triggers, columnas generadas, CHECK/DEFAULT/
COLLATE/REFERENCES ni índices calculados/parciales. El filtro conservador también
puede rechazar una base legítima fuera de ese perfil. La inicialización nativa
queda acotada por fuente y proceso, no por una cifra exacta de instrucciones VM.

**Contenido lógico por archivo:** 128 registros/exclusiones. Texto: 64 KiB,
128 líneas, 2048 caracteres por línea. Plist: raíz dict, 1024 nodos, claves de
128 caracteres y strings de 2048. JSON: UTF-8/BOM, raíz objeto/array, 64 KiB,
24 niveles, 1024 nodos, 128 escalares/exclusiones, claves 128 y strings 2048;
sin duplicados, números no finitos ni controles fuera de perfil. Contenedores
vacíos como exclusiones; sin interpretación de esquemas de aplicaciones o fechas.

Corrupción, cuota o esquema incompatible no se convierten en análisis completo.
En el conjunto lógico, un archivo con contenido excluido conserva declaración y
hash; una asociación inválida rechaza todo el paquete. En SQLite/Safari no se
publican prefijos tras sobrecuota o corrupción; filas inválidas aisladas pueden
quedar excluidas con localizador. Los contratos detallados precisan cada estado.

## Evidencia de aceptación y evolución posterior

Referencias de formato, fixtures, oráculos, pruebas, preservación e incidentes:
[VALIDATION](VALIDATION.md), [catálogo](PARSER_CATALOG.md) y
[procedencia](PROVENANCE_AND_DEPENDENCIES.md). La demostración pública y el cierre
se documentan por separado; no sustituyen una adquisición real autorizada.

Para versiones posteriores: corpus autorizado por OS/método, otros esquemas y
aplicaciones, bugreport Android identificado, permisos/procesos/ajustes con
esquema comprobado, asociación física, WAL/SHM de Safari, cifrado y formatos fuera
de este catálogo. No se agregan lectores nuevos como condición implícita de este
cierre. La preparación productiva pertenece a E7, con sus controles propios.
