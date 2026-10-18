# E5 — Laboratorio estático: primera entrega parcial

Registro histórico de la importación externa. La continuidad con proveedor real,
trabajos y revisiones está en [CPython AST y trabajos](STATIC_PROVIDER_JOBS.md).

Fecha: 2026-10-18. Base: `d06b955`. Implementación local, sin publicación.

## Alcance comprobable

La primera entrega incorpora importación pasiva de resultados externos por API:
expediente → evidencia con archivo preservado → resultado externo → observaciones
con localizadores. No ejecuta herramientas, muestras, shell, consultas de red,
extracción de archivos ni instrucciones incluidas en el resultado.

**E5 continúa parcial.** No hay proveedor real validado, interfaz de laboratorio,
trabajos de proveedores, revisiones profesionales versionadas ni proyección de
estos resultados a hallazgos e informes. Todos los registros quedan pendientes
de revisión; no se aprueban automáticamente. El motor móvil existente no cambia.

REA sigue siendo opcional y externo. No se instaló REA, JADX ni Ghidra. La consulta
de ejecutables en PATH no encontró esos comandos; esto no certifica su ausencia
en todo el equipo. No se verificaron repositorios, versiones ni licencias de
proveedores porque no se incorporó código o ejecución de ninguno.

## Contrato de importación

Se acepta exclusivamente `operia-static-report/1`, con campos cerrados y tipos
estrictos: SHA-256 de muestra, proveedor, versión, revisión, operación
`static-observations`, cobertura declarada, limitaciones y observaciones.

Cada observación tiene identificador único, miembro relativo, desplazamiento y
texto. Los localizadores se conservan como declaraciones externas; no se abren
ni se certifica su exactitud. Se rechazan rutas absolutas, traversal, URI,
separadores ambiguos, controles inválidos, Unicode inválido, claves duplicadas,
comandos, campos desconocidos y coberturas inconsistentes.

Límites: 256 KiB tanto para el original como para su representación normalizada,
200 observaciones, muestra existente de hasta 32 MiB para archivos del depósito y
1.000 importaciones por organización. La cuota se cuenta bajo bloqueo de escritura
SQLite, incluye expedientes no visibles y no devuelve sus conteos. No se duplican
los bytes de la muestra. No se amplían límites de workers, IA o conectores.

Antes de importar se compara el hash declarado con el registrado en evidencia y
con sus bytes preservados, sin ejecutar la muestra. La procedencia del análisis
se conserva como **external-import**, con ejecución del proveedor no verificada.
Los nombres y versiones del proveedor son declaraciones del documento recibido.
Una mención de URL no demuestra conexión; cobertura `complete` es la declaración
del proveedor, no cobertura universal acreditada por OPERIA.

## Uso por API

Todas las rutas requieren autenticación y acceso al expediente:

| Método y ruta | Uso |
| --- | --- |
| GET `/api/static-lab/cases/{case_id}/providers` | Diagnóstico: entrega parcial, ejecución deshabilitada, ningún proveedor validado |
| POST `/api/static-lab/cases/{case_id}/evidence/{evidence_id}/imports` | Cuerpo JSON original, `Content-Type: application/json` |
| GET `/api/static-lab/cases/{case_id}/imports` | Listado: 20 por defecto, máximo 100, cursor opcional `before` |
| GET `/api/static-lab/cases/{case_id}/imports/{id}` | Metadatos y observaciones normalizadas |
| GET `/api/static-lab/cases/{case_id}/imports/{id}/original` | Original como adjunto; además requiere capacidad de exportación |

El rol limita lectura/escritura de evidencia. La importación exige capacidades
explícitas de lectura, análisis e incorporación de evidencia del expediente,
salvo la política de administrador de organización ya establecida en E3.
Revocar el acceso impide consultas e importaciones posteriores. Otro expediente
u organización recibe recurso no disponible, sin revelar su contenido.

Para un recorrido benigno, cargar como evidencia `tests/fixtures/static_lab/benign-sample.txt`
y enviar `tests/fixtures/static_lab/external-result.json` a la ruta POST usando el
identificador devuelto por la carga. El archivo es texto sintético, no un binario
analizado por un proveedor real. No colocar tokens en URLs ni guardar credenciales
en ejemplos. No se incorpora una pantalla en este tramo.

## Históricos y custodia

El original exacto y la representación normalizada se guardan por separado, con
SHA-256 independientes, actor autenticado y fecha de incorporación. Se comprueba
integridad al leer. Repetir exactamente la misma importación es idempotente;
otro documento genera otro registro y conserva los anteriores.

La importación agrega un evento de custodia y auditoría en la misma transacción.
No modifica los eventos previos. La tabla rechaza UPDATE y DELETE mediante
triggers SQLite y protección ORM. Las evidencias vinculadas no se pueden editar
ordinariamente ni borrar, y se impide eliminar su expediente. No existen rutas
PUT/DELETE de resultados. La protección local no resiste por sí sola a un
administrador host que quite los triggers o reescriba base y hashes; no es WORM.

## Migración y recuperación

La migración aditiva `20261018_0008` agrega `static_lab_imports` y dos triggers.
También se integra con el inicializador SQLite existente: un próximo arranque
normal aplicará esa estructura. **No se arrancó la API contra la base habitual
ni se migró esa base durante esta entrega.** PostgreSQL queda sin habilitar para
esta función hasta validación propia.

Respaldo previo: `storage/temp/e5-static-lab-20261018`, con ACL restringida al
usuario, SYSTEM y administradores. Incluye SQLite, 116 archivos persistentes y
manifiesto de hashes, también secretos locales; queda fuera de Git.

Sobre una copia se ejecutaron upgrade repetido y downgrade conservador: las filas
de las 74 tablas anteriores, incluyendo duplicados, y sus objetos de esquema se
mantuvieron idénticos. Integridad `ok`, 11 triggers tras agregar los dos nuevos.
Se restauraron la base y los archivos en destinos nuevos y se verificaron hashes.

Para revertir código, conservar la tabla y sus registros: downgrade no los borra.
No restaurar un respaldo antiguo sobre una base que recibió nuevos registros.
Una recuperación completa debe coordinar base, depósito y secretos de la misma
fecha, con la aplicación detenida y restauración en destino nuevo.

## Pendientes de aceptación

- Proveedor estático real, revisión fijada, licencia y procedencia verificadas.
- Perfil de aislamiento propio, sin red ni secretos y sin fallback del SO.
- Trabajos persistentes, cancelación, reinicio, timeout y límites de salida.
- Revisión versionada y transferencia explícita a hallazgos e informes.
- Interfaz premium y pruebas de interacción con esa nueva interfaz.
- La validación E4 con NVDA, VoiceOver y TalkBack en dispositivos reales continúa
  pendiente según [la matriz de tecnologías de asistencia](ASSISTIVE_ACCESSIBILITY.md).

No se contabilizan horas humanas por duración de herramientas o inferencia.

## Evidencia de aceptación

Las seis pruebas específicas cubren contrato hostil, idempotencia, originales,
versiones, cuotas, integridad, accesos cruzados, revocación, custodia y migración
aditiva. Frontend: 47 pruebas aprobadas y build correcto. La regresión completa y
la verificación final de permisos/custodia (45 pruebas aprobadas) se registran en la
[auditoría de esta entrega](audits/e5-static-lab-20261018.json). No se ejecutó
Bandit: no está instalado en el entorno de pruebas; no se declara un resultado
de ese analizador. No se agregaron dependencias de ejecución.

Resultado de regresión general: **278 aprobadas, 1 omitida y 4 advertencias**.
La omisión corresponde a Ollama real optativo; las advertencias existentes son
de TestClient/httpx, ReportLab y el ciclo de vida de FastAPI. Las 45 pruebas
finales específicas de E5, permisos y custodia también pasaron tras los últimos
ajustes. No se hizo una nueva inspección visual: el frontend no cambió en E5.
