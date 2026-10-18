# E6: Manifest.db y catálogo SQLite acotados

Registro de la entrega 0.3.0. La continuidad [0.4.0 agrega perfiles WAL/SHM
separados](E6_WAL_SHM.md); no cambia la exclusión de sidecars de estos lectores.

Continuidad del 2026-10-18. Motor **0.3.0**, contrato de salida `operia.forensic/1`.
Ocho lectores registrados, de implementación propia; sin dependencias nuevas.
Los cinco lectores anteriores siguen disponibles y sus resultados no se reescriben.

## Cobertura declarada

| Perfil / plataforma | Entrada y salida | Exclusiones |
| --- | --- | --- |
| `apple-backup-manifest-sqlite`, iOS | Tabla ordinaria `Files` con cinco columnas exactas: fileID TEXT PRIMARY KEY, domain TEXT, relativePath TEXT, flags INTEGER, file BLOB. Extrae solo fileID, dominio, ruta relativa y flags 1/2. Localizador estable `Files/fileID:<id>` | No consulta el BLOB file, NSKeyedArchiver, fechas, permisos, otros registros ni contenidos lógicos. No abre rutas ni verifica la correspondencia de fileID con un archivo físico |
| `sqlite-schema-catalog`, iOS y Android | Nombres y tipos de tablas/índices ordinarios; localizador `sqlite_schema/<tipo>/<nombre escapado>` | No exporta DDL, columnas, filas, valores, fechas, mensajes ni historial. No consulta nombres recibidos como SQL |

Estos campos son declaraciones de la imagen aportada. No acreditan autenticidad,
integridad del backup completo, instalación, ejecución, tráfico ni ausencia de compromiso.
No se producen fechas inferidas. Las filas excluidas conservan localizador y motivo.

## Copia preservada y defensa del lector

La adquisición conserva bytes y SHA-256. El lector recibe esos bytes y deserializa
una copia privada en memoria: nunca abre la ruta del original como base de datos,
no crea sidecars y no usa rutas procedentes de `Files`. La API/worker conservan
las verificaciones de hash y autorización por organización/expediente ya existentes.
El worker mantiene AppContainer sin red, límites de memoria/CPU y Job Object.

Solo se admite imagen principal SQLite 3 UTF-8, sin cifrado, hasta **5 MiB**,
páginas completas y cabecera en modo rollback. WAL se rechaza sin modificar su
cabecera. No se comprueba la ausencia de WAL/journal externos: quien preserva la
fuente debe documentar cómo obtuvo una imagen consistente. No se fusionan WAL,
SHM o journals, ni se reparan, recuperan o descifran bases.

Controles obligatorios: configuración defensiva, esquema no confiable,
extensiones/triggers/vistas deshabilitados, `query_only`, temporales en memoria,
cero adjuntos e hilos auxiliares; autorizador con consultas fijas y denegación
restante. Sin SQL del cliente, funciones, escrituras, ATTACH ni lectura del BLOB.
`deserialize` realiza operaciones internas antes de instalar el autorizador;
se instala inmediatamente después y antes de toda consulta a la fuente.

Límites: 128 objetos de esquema, 64 columnas, 5000 filas de Files, valores SQLite
de hasta 256 KiB, SQL de hasta 8192 bytes y presupuesto de 100000 pasos de VM
comprobado cada 1000 operaciones. La inicialización nativa del esquema queda además
acotada por tamaño de fuente y límites del proceso; el contador VM no representa
un presupuesto exacto de todas las instrucciones nativas.

Se rechazan vistas, tablas virtuales, triggers, columnas generadas, CHECK,
DEFAULT, COLLATE, referencias y claves foráneas; solo índices simples de columnas,
sin expresiones o predicados. El filtro conservador puede rechazar bases legítimas
que contengan esas palabras en identificadores o variantes de índices no previstas.
No es un lector universal de SQLite. `quick_check` verifica consistencia interna
en este perfil; no autentica la evidencia. Un exceso de cuota/corrupción no publica
registros parciales. Variantes incompatibles se indican en cobertura y advertencias.

## Operación, custodia y continuidad

Elegir el formato en Forense móvil, preservar una adquisición y crear un examen
nuevo. El selector usa el catálogo del backend. También disponible en la CLI:

```powershell
python -S -m operia.forensic_engine Manifest.db --platform ios --format apple-backup-manifest-sqlite --output resultado-nuevo.json
```

La CLI no sobrescribe la salida. Usar una copia preservada autorizada. Para el
catálogo elegir `sqlite-schema-catalog` y la plataforma declarada correspondiente.
Preparar el runtime con `scripts/prepare_worker_sandbox.py` antes de iniciar el
worker de esta versión. Los controles requieren el runtime validado Python 3.12.14
con SQLite 3.53.1 en Windows; no se afirma compatibilidad con otras compilaciones.

Se heredan revisión versionada, incorporación explícita a evidencia/custodia/informe
y permisos por expediente con denegación por defecto. No hay migraciones de datos.
Exámenes anteriores se siguen leyendo con su versión y hash originales; un pendiente
de otra versión se rechaza por incompatibilidad de configuración. Crear otro examen
explícito sobre la adquisición preservada; nunca actualizar el resultado histórico.

## Aceptación y pendientes

`tests/test_manifest_sqlite.py` genera imágenes sintéticas originales con oráculo
manual de campos/localizadores. Incluye canarios BLOB/filas, consultas prohibidas,
esquemas activos, cabeceras WAL, truncamiento, cuotas, CLI y ambos perfiles en
workers aislados reales; revisión, informe preservado, concesión/revocación y
descarga del original. La regresión transversal comprueba ámbitos y custodia.
Resultados y recuperación: [validación](VALIDATION.md) y auditoría de esta entrega.

No se validaron backups de dispositivos reales ni versiones de iOS/Android.
Pendientes: corpus autorizado por versión, imágenes consistentes con sidecars,
archivos lógicos y lectores específicos de registros. La validación física de
NVDA/VoiceOver/TalkBack y móviles sigue [pendiente](../ASSISTIVE_ACCESSIBILITY.md).

## Referencias de especificación y seguridad

- [SQLite: defensa ante bases no confiables](https://www.sqlite.org/security.html),
  [límites](https://www.sqlite.org/limits.html),
  [autorizador](https://sqlite.org/c3ref/set_authorizer.html) y
  [deserialize](https://www.sqlite.org/c3ref/deserialize.html).
- [API sqlite3 de Python 3.12](https://docs.python.org/3.12/library/sqlite3.html).
- [Esquema Files observado por un proyecto comunitario](https://github.com/ekuester/pyGTK-List-ManifestDB-From-iOSBackup):
  referencia de nombres/tipos, sin copiar implementación ni fixtures. No es una
  especificación oficial completa de Apple ni validación entre versiones.
