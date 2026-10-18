# E5 — Proveedor CPython AST, trabajos y revisión versionada

Entrega local del 2026-10-18, sobre `78ffa31`. No se publicó ni desplegó.
Conserva la [primera entrega de importación externa](STATIC_LAB.md) y sus registros.

## Proveedor real y cobertura

Se integró **CPython AST 3.12.14**, ya instalado, mediante el adaptador propio
`operia-ast-adapter/1`. El proveedor real es el parser AST de CPython, ejecutado
en un proceso aislado; las respuestas no son un mock. No se instaló software nuevo.

Alcance: fuente Python en UTF-8, hasta 128 KiB. Identifica declaraciones de
importación, funciones y clases, con desplazamientos en bytes verificables.
No ejecuta ni importa la muestra, no genera bytecode, no consulta URLs y no produce
veredictos de seguridad. Una declaración de importación no demuestra comportamiento.
La cobertura devuelta es parcial o vacía, nunca detección universal o «limpieza».
No se declara soporte de APK, PE, ELF, bytecode, firmware ni descompilación.
JADX, Ghidra y REA continúan sin integrar; no aparecieron como comandos en PATH.

La muestra benigna reproducible está en
`tests/fixtures/static_lab/benign-source.py.txt`. Incluye dos importaciones, una
función, una clase y una excepción deliberada que no debe ejecutarse. Se compararon
las cuatro observaciones y sus offsets con la fuente. El trabajo se completó dentro
de AppContainer sin ejecutar esa excepción. No se descargó ni ejecutó malware.

La documentación oficial describe [el parser AST y sus límites de recursos](https://docs.python.org/3.12/library/ast.html).
La versión y revisión están fijadas en cada resultado; el runtime tiene manifiesto
SHA-256 de archivos y una identidad ligada a versión y código del adaptador y
política. Se conserva `LICENSE.txt` de Python dentro del runtime. No se incorporó
CPython ni código de terceros al repositorio; sus binarios locales quedan ignorados.
Los cambios de runtime invalidan trabajos pendientes fijados a otra revisión.

## Aislamiento y límites

Runtime separado: `storage/static-lab-runtime/{identity}`. Se copian únicamente
el runtime estándar y un inventario cerrado de módulos del adaptador y su guardia;
sin site-packages, archivos de API, base, claves ni configuración de usuarios.
Se verifica el manifiesto antes de lanzar. No se cambió el runtime del motor móvil.

Cada lanzamiento usa un AppContainer nuevo, sin capacidades de Internet ni
excepción de loopback, y un Job Object: 1 proceso, 128 MiB y 5 segundos de CPU.
Timeout de pared por defecto: 10 segundos. Salida máxima: 256 KiB. El padre drena
los pipes con límites y termina el árbol ante cancelación, timeout o exceso.
El hijo exige AppContainer y pertenencia a Job Object antes de leer la muestra.
No existe fallback sin aislamiento.

Solo se transfieren bytes por pipes anónimos. No se entrega una ruta del depósito,
el expediente, credenciales ni el contexto de otro trabajo. No se escriben muestras
o resultados en un directorio compartido: se conserva el snapshot en base y el
perfil AppContainer es exclusivo y descartable. El runtime compartido contiene
solo código y tiene acceso de lectura/ejecución para AppContainers.

El cierre normal elimina el perfil y sus handles. Un cierre abrupto del host o del
worker puede dejar metadatos del perfil Windows; la recuperación marca el trabajo
interrumpido y no lo republica. La retención administrativa de perfiles huérfanos
requiere un procedimiento operativo separado; no se eliminan perfiles ajenos.

## Trabajos persistentes

| Ruta | Función |
| --- | --- |
| POST `/api/static-lab/cases/{case_id}/evidence/{evidence_id}/jobs` | Crear con `{"request_key":"revision-1","provider":"cpython-ast"}` |
| GET `/api/static-lab/cases/{case_id}/jobs` | Últimos 100 trabajos autorizados, sin bytes de muestras |
| GET `/api/static-lab/cases/{case_id}/jobs/{job_id}` | Estado, resultado, eventos y revisiones |
| POST `/api/static-lab/cases/{case_id}/jobs/{job_id}/cancel` | Cancelación persistente y auditada |
| POST `/api/static-lab/cases/{case_id}/jobs/{job_id}/reviews` | Nueva revisión profesional |
| GET `/api/static-lab/cases/{case_id}/providers` | Runtime disponible, alcance y evidencia de ejecución en ese expediente |

La cola guarda fuente preservada, hash, evidencia, organización, actor y revisión
del runtime. Máximo 1.000 trabajos por organización, contando también expedientes
no visibles sin devolver esos conteos. Misma evidencia y `request_key` devuelven
el trabajo original; para otro intento se usa otra clave. No hay reintentos ocultos.

Estados: queued → preparing → running → completed, failed o cancelled. Al reiniciar
el worker se registra interrupted para trabajos activos anteriores, sin inventar
resultados. Un bloqueo exclusivo de archivo impide dos workers estáticos para el
mismo almacenamiento. La toma del trabajo usa además actualización condicional.

Se requieren rol de escritura de evidencia y capacidades de lectura, análisis y
evidencia del expediente. Se revalidan organización, usuario, rol y concesiones
antes de ejecutar, durante la ejecución y bajo bloqueo antes de publicar. Revocar
acceso o suspender al operador impide publicar el resultado. Cerrar una sesión
no cancela por sí solo trabajos ya autorizados: se usa cancelación explícita o
revocación del usuario o sus capacidades. Cancelación fallida,
proveedor ausente o muestra corrupta no producen un resultado exitoso vacío.

## Revisión y custodia

Cuerpo de revisión:

```json
{
  "expected_version": 0,
  "decision": "needs_corroboration",
  "rationale": "Observaciones contrastadas con la fuente; falta corroboración independiente."
}
```

Se requiere capacidad `review`, además del permiso del rol. Decisiones admitidas:
accepted, rejected y needs_corroboration. Cada revisión agrega versión, actor,
fecha, fundamento y hash exacto del resultado revisado. El cliente debe enviar
la última versión; las revisiones concurrentes desactualizadas reciben 409.
Máximo 100 revisiones por trabajo. No se sustituyen revisiones previas.

Una aceptación profesional no equivale a aprobar un informe ni habilita exportación.
No se crean automáticamente hallazgos, atribuciones ni conclusiones legales.
Resultados locales y sus versiones se mantienen separados de los resultados
externos históricos, cuyo origen no se reclasifica.

Al completar el análisis se agrega custodia y auditoría en la misma transacción,
con el usuario autenticado que solicitó el trabajo y el hash del snapshot analizado.
Los eventos originales permanecen. Los eventos de trabajo y revisiones son
append-only; los snapshots y resultados publicados no pueden sustituirse.
La evidencia vinculada y el expediente no admiten borrado ordinario.

## Operación local y migración

1. Respaldar base, archivos y secretos antes de actualizar.
2. Ensayar migraciones `20261018_0008` y `20261018_0009` en copia. El inicializador
   SQLite existente crea también las nuevas estructuras durante el próximo arranque.
3. Preparar el runtime como operador: `.venv/Scripts/python.exe -m operia.static_lab.runtime`.
4. Cargar la muestra benigna como evidencia y crear el trabajo mediante la API.
5. Procesar un trabajo: `.venv/Scripts/python.exe -m operia.static_lab.worker`.
6. Consultar el resultado y agregar las revisiones mediante la API.

El comando procesa un trabajo por invocación; no se instaló un servicio ni una tarea
programada. No se procesaron trabajos ni se migró la base habitual. El esquema y datos
habituales permanecen sin migrar durante esta entrega; las pruebas usan copias.
SQLite es la plataforma validada. PostgreSQL y operación múltiple son requisitos
pendientes de E7, no capacidades acreditadas por estas pruebas.

Respaldo previo con ACL restringida:
`storage/temp/e5-static-provider-20261018`. En una copia se ensayaron upgrade
repetido y downgrade conservador: 74 tablas anteriores y sus objetos de esquema
idénticos; integridad `ok`, 17 triggers totales después de agregar los nuevos.
Se restauraron base y 116 archivos en destinos nuevos con hashes iguales.
Downgrade conserva los registros: revertir código no borra la historia.
También se archivaron y restauraron los 678 archivos del runtime y su manifiesto,
verificados por SHA-256, en carpetas nuevas del respaldo. Al recuperar para
ejecución, verificar manifiesto e identidad y restablecer únicamente lectura/
ejecución para AppContainers sobre ese runtime no secreto; el archivo de respaldo
conserva ACL privada. No conceder acceso al depósito de evidencia ni a la base.

## Aceptación y pendientes

Las pruebas combinan ejecuciones **reales** del proveedor aislado con dobles de
proceso únicamente para fallos controlados de timeout, salida excesiva y revocación
durante la ejecución. No se presenta un doble como validación del proveedor.
La evidencia resumida está en la [auditoría de esta entrega](audits/e5-provider-jobs-20261018.json).

Sigue pendiente en E5 la interfaz del laboratorio y la transferencia explícita de
observaciones revisadas a hallazgos e informes. Otros formatos requieren otro
proveedor y perfil validados. La prueba con NVDA, VoiceOver y TalkBack en dispositivos
reales conserva su [matriz pendiente](ASSISTIVE_ACCESSIBILITY.md). No se declara
producción lista, certificación WCAG ni custodia resistente al administrador del host.

Regresión general: **285 aprobadas, 1 omitida y 4 advertencias conocidas**.
La omisión requiere activación explícita de Ollama real. La validación posterior
incluye un proceso CLI nuevo y atribución de custodia, además de las pruebas
negativas de jobs y revisiones. El frontend no cambió en este tramo; no se acredita
una nueva inspección visual ni pruebas físicas de lectores de pantalla.

Comprobación final sobre la versión corregida: **38 pruebas aprobadas** de
trabajos, importación y custodia, incluido el worker CLI en un proceso nuevo.
La regresión general y esta tanda se superponen; no se suman como casos únicos.

Continuidad posterior del 2026-10-18: la interfaz y la incorporación revisada que
se registraban pendientes arriba se implementan en [Laboratorio premium](STATIC_LAB_INTERFACE.md).
Este documento conserva la evidencia y los límites de la entrega anterior.
