# E6: registros SQLite de Safari iOS sobre copias preservadas

Continuidad 2026-10-18. Motor **0.7.0**, contrato `operia.forensic/1`,
**13 lectores y 11 formatos**. Lector propio `operia.ios.safari-history` **1.0.0**,
formato explícito **`ios-safari-history-sqlite`**, sin dependencias nuevas ni
migraciones. Es el primer perfil de filas de aplicaciones iOS; no es un lector
general de bases de aplicaciones.

## Entrada y perfil de esquema

Una copia elegida explícitamente de `History.db`, preservada como adquisición
nueva de un expediente con bytes, hash, autorización y metadatos de procedencia.
El nombre del archivo o del formato no autentica que provenga de Safari/iOS.
No explora backups ni abre rutas de Manifest.db. No vincula automáticamente esta
copia a un fileID: documentar esa asociación en la adquisición y conservar el
manifiesto por separado. La asociación física queda pendiente de corroboración.

Solo imagen SQLite 3 principal, UTF-8 y modo rollback, hasta **5 MiB**, recibida
como bytes y deserializada en una copia privada `:memory:`. No abre la evidencia
con SQLite en disco, crea sidecars, modifica cabeceras ni agrega WAL/SHM. Reutiliza
los controles [SQLite defensivos](E6_MANIFEST_SQLITE.md): query_only, defensive,
trusted_schema desactivado, extensiones/vistas/triggers desactivados, límites VM,
memoria/columnas/SQL y autorizador de denegación por defecto.

Tablas ordinarias con nombres y columnas exactos (tipos declarados):

| Tabla | Columnas seleccionadas | Clave requerida |
| --- | --- | --- |
| history_items | id INTEGER, url TEXT | id, única columna de PRIMARY KEY |
| history_visits | id INTEGER, history_item INTEGER, visit_time REAL, title TEXT | id, única columna de PRIMARY KEY |

Se toleran columnas ordinarias adicionales, **no se consultan sus valores**:
exclusiones por ordinal. Otras tablas se enumeran como excluidas, sin leer sus
filas. Esquemas activos, vistas, triggers, tablas virtuales, columnas generadas,
restricciones calculadas, DEFAULT/COLLATE/REFERENCES y variantes fuera del perfil
se rechazan completos. Índices solo ordinarios de columnas bajo el perfil
preexistente, sin expresiones ni predicados. Máximo **128 objetos de esquema**.
No habilita automáticamente esquemas reales que excedan estas restricciones.

## Filas, límites y exclusiones

Dos consultas fijas, sin joins ni consultas aportadas por el usuario, ordenadas
por id, con **LIMIT 501** para detectar exceso. Hasta **500 filas por tabla**;
si cualquiera supera el límite, no se publica ningún prefijo de resultados.

IDs positivos de tipo INTEGER. Cada visita interpretable referencia un elemento
interpretable en esta misma copia. URL almacenada no vacía de hasta **2048
caracteres**; título nullable de hasta **2048**. Strings sin C0 ni DEL. No visita ni
normaliza URLs, resuelve DNS, extrae dominios o descarga contenido. El título se
conserva como texto, sin ejecutar HTML. BLOB y otros tipos inválidos se excluyen.
La URL es texto de la columna; no se valida su sintaxis ni se incorpora como
candidato URL/dominio/IP de indicadores. La comparación explícita por hash de la
fuente conserva el comportamiento previo del motor.

`visit_time` puede devolver un número finito o SQL NULL. Se conserva su valor y
tipo devueltos por SQLite, **sin elegir época, unidad, zona ni generar eventos temporales**.
El tipo expuesto por SQLite respeta afinidades de columnas; no identifica el
tipo serial físico de la celda en disco.
Los flotantes tienen precisión binaria; el valor numérico no conserva un lexema
SQL histórico. NULL no acredita cómo se produjo. No identifica versión de iOS,
usuario, origen local/remoto, apertura efectiva o comunicación de red.

Artefacto `ios_safari_history_visit`, con `visit_id`, `history_item_id`,
`stored_url`, `stored_title`, `stored_visit_time` y `stored_visit_time_type`.
Localizador `history_visits/id:N`: clave de registro, **no offset físico**.
`source.sha256` vincula cada artefacto con los bytes de la adquisición. Filas con
valores iguales conservan IDs distintos y no se fusionan como una observación.

Referencias huérfanas, URLs inválidas y visitas con título/fecha inválidos producen
exclusiones localizadas sin publicar sus valores. Elementos sin visita interpretable
quedan excluidos; no equivalen a borrados ni navegación ausente. IDs primarios fuera
de perfil, corrupción, cuota o presupuesto VM agotado rechazan el examen completo
sin filas parciales. Hasta **500 artefactos**, más exclusiones sujetas a los límites
anteriores y a la cuota global de **16 MiB** de salida.

## Operación, ámbitos e históricos

En Forense móvil elegir `ios-safari-history-sqlite` y subir la copia preservada.
El selector obtiene los formatos del catálogo versionado; no hay SQL configurable.
CLI sobre una copia explícita:

```powershell
python -S -m operia.forensic_engine History.db --platform ios --format ios-safari-history-sqlite --output resultado-nuevo.json
```

La salida no se sobrescribe. No se descubren sidecars contiguos. El paquete de
selección lógica previo mantiene su catálogo SQLite; **no empieza a leer filas de
Safari automáticamente**. Para este examen se requiere elegir el nuevo formato
y documentar la copia seleccionada, sin cambiar adquisiciones anteriores.

Preparar runtime **0.7.0** y reiniciar API/workers de forma controlada para nuevos
trabajos. Se mantienen AppContainer/Job, denegación por defecto por expediente,
aislamiento de organizaciones, revisión versionada, incorporación explícita a
evidencia/custodia/informes e históricos sin recálculo. El autorizador de este
perfil permite únicamente sus columnas: no amplía el autorizador de Manifest o
del catálogo. No se mandan estos datos sensibles a IA o conectores automáticamente.
Un pendiente incompatible requiere un examen nuevo explícito; no editar su versión.

Respaldo privado independiente en `storage/temp/e6-ios-app-sqlite-20261018`, con
base, archivos y restauración verificada. Se conservan backups, resultados y
runtimes anteriores. El archivo/restauración de runtime se verifica sin ejecutar
la copia archivada. Resultados concretos en [VALIDATION](VALIDATION.md).

## Aceptación y pendientes

Fixtures sintéticos originales: dos visitas interpretables, fecha desconocida,
referencia huérfana, elemento sin visita y columnas/BLOB/tabla privados excluidos.
Oráculos de valores, hashes y determinismo; límite exacto de 500 y rechazo de 501,
controles/tipos/fechas inválidos, esquemas activos, privilegios SQL y presupuesto
VM, CLI `-S` con WAL señuelo no leído. Worker real: original/evidencia íntegros,
custodia, revisión nueva con informe/exportación estables, denegación sin concesión,
solo lectura, revocación, otro expediente y otra organización.

Pendientes: corpus autorizado real por OS/adquisición y variantes de Safari,
confirmación de época de fechas, WAL/SHM específico del perfil, otros navegadores,
mensajes/contactos y demás aplicaciones, borrados, BLOB/archivos adjuntos,
sincronización, perfiles, etiquetas y redirecciones. No cubre backups completos
ni acredita ausencia de compromiso. La validación física de accesibilidad sigue
pendiente según [su registro](../ASSISTIVE_ACCESSIBILITY.md).

Referencia primaria de nombres de tablas/columnas y advertencia de variantes:
[iLEAPP, safariHistory.py](https://github.com/abrignoni/iLEAPP/blob/main/scripts/artifacts/safariHistory.py),
consultada 2026-10-18. Se consultó como descripción de formato; no se copió su
implementación, corpus, conversión de fechas ni se agregó como dependencia.
Este lector y sus fixtures son propios; la validación ajena no valida este motor.
