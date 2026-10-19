# E7: preparación productiva — privilegios, secretos y recuperación

Inicio 2026-10-18 y validación 2026-10-19, posterior al cierre E6 0.7.0. **E7 no está cerrado ni
se declara el SaaS listo para producción.** No se desplegó, publicó o instaló un
servicio. Sin migraciones, dependencias nuevas, cambios de ACL por expediente ni
reescritura de custodia/informes. El motor y su runtime mantienen la versión 0.7.0.

## Auditoría y refuerzos

| Hallazgo | Refuerzo implementado | Límite / pendiente |
| --- | --- | --- |
| Supervisor bajo cuenta del operador, miembro de Administradores aunque no elevada | Inicio API y CLI de workers rechaza en modo production token elevado, membresía Administradores (incluso deny-only/UAC filtrada) y cuentas SYSTEM/servicio integradas | No se creó una cuenta ni servicio Windows. Provisión de cuenta dedicada, código/venv/migraciones de solo lectura y permisos de escritura únicamente en datos/runtime preparados, pendiente de prueba bajo esa identidad |
| Clave local generada con permisos heredados; sin fuente externa por archivo | ACL privada antes de escribir claves nuevas; OPERIA_AUTH_SIGNING_KEY_FILE con 32 bytes exactos, archivo regular, sin enlaces/reparse/hardlinks y permisos privados; conflicto inline+archivo rechazado | Producción requiere archivo explícito y padre privado. No se implementa un vault multiempresa ni rotación coordinada de sesiones |
| Configuración insegura podía presentarse como producción | Guard antes de secretos/migraciones en API y entrada de workers; rechaza claves inline, falta de archivo privado, recuperación local habilitada, orígenes sin HTTPS y entornos desconocidos | Es política mínima, no comprobación de TLS real, firewall, MFA o RLS. La configuración local continúa local; no se la convierte a producción automáticamente |
| Respaldo existente solo cubría SQLite y no cifraba archivos/secretos | Nuevo paquete offline con DPAPI de usuario, manifiesto interno y hashes, SQLite y archivos/configuración/clave explícita; verificación integral y restauración solo en árbol nuevo | Alcance enumerado, no snapshot de host. Requiere escritores detenidos por operador. No equivale a RPO/RTO ni recuperación ante pérdida de cuenta/host |
| Conexiones SQLite no se cerraban explícitamente en utilidad anterior | contextlib.closing en copia/verificación, también en nuevo paquete | El helper antiguo sigue siendo solo SQLite, sin cifrado; no confundirlo con el paquete nuevo |
| Docker local como root, puerto abierto al host y contexto demasiado amplio | USER 10001, raíz de contenedor readonly, cap_drop ALL/no-new-privileges, bind a loopback, volúmenes explícitos y /tmp acotado/noexec; contexto por allowlist sin storage, claves o backups; migraciones incluidas y CORS JSON corregido | Compose validado; daemon Docker no disponible para build/ejecución. Docker Linux y sus workers no quedan validados para producción ni reemplazan AppContainer |

`scripts/production_audit.py` devuelve solo códigos, sin secretos, SID, rutas ni
cadenas de conexión. En el entorno local encuentra modo no productivo, cuenta
privilegiada por membresía, archivo externo no configurado y CORS de desarrollo.
La salida **no es un certificado**. La importación de Settings puede crear los
directorios vacíos de almacenamiento previstos; no migra ni modifica datos.

## Secretos: compatibilidad y operación

- La clave inline existente sigue admitida en local por compatibilidad, redactada
  por SecretStr; se rechaza en production. No configurarla junto con el archivo.
- El archivo externo contiene **32 bytes binarios**, no texto/base64/JSON. Se lee
  y valida en cada uso: una sustitución intencional cambia firmas y requiere
  procedimiento de rotación/invalidación de sesiones, no se oculta en caché.
- La clave local previa conserva su mecanismo y bytes si existe. Los archivos
  nuevos se crean privados antes de escribir secreto. No hay fallback de clave
  predecible o ante archivo externo inválido.
- ACL Windows permite usuario actual, SYSTEM y Administradores, propietario de ese
  conjunto, sin otros grants. La carpeta del archivo externo debe ser privada en
  producción. No protege frente al administrador del host o compromiso del proceso
  que necesita leer la clave. Hay validación POSIX de dueño/modo para archivos,
  pero el perfil productivo validado de esta entrega es Windows.

En esta instalación **no había .env ni clave persistente local** para cambiar ACL;
se inicializó la clave local faltante con permisos privados. No se reemplazó ni
rotó una clave previa. Es un archivo nuevo ignorado por Git; nunca se imprimió su
contenido. No se cambiaron cuentas, configuración del sistema, permisos de
expedientes o datos históricos. No se habilitó production en la copia habitual.

Plantilla `.env.production.example`, sin valores secretos. Para el servicio real,
un administrador debe provisionar carpeta/clave para la identidad de servicio,
con código y entorno Python no modificables por ella. Si ya hay clave efectiva,
conservar sus bytes durante la migración; no generar una sustituta silenciosa.
No copiar la clave al repositorio, comando, log, informe o variables del navegador.

Lanzador separado `scripts/start-api-production.ps1`: exige OPERIA_ENV=production,
ejecuta la política mínima y sirve en 127.0.0.1 con un proceso, sin reload ni
cabeceras de proxy confiadas. TLS/gateway y su configuración son pasos externos;
no cambiar al lanzador sin completar aceptación de despliegue.

## Respaldo cifrado y restauración segura

Herramienta **solo de operador**, sin endpoint ni posibilidad de elegir SQL.
`scripts/recovery_bundle.py` admite backup, verify y restore. Incluye:

- SQLite completo mediante backup API, con integridad y segunda instantánea en
  disco para detectar cambios persistentes durante la operación.
- evidence, uploads, exports y maps del storage seleccionado; memory_vault del
  proyecto, .env/.auth-signing-key raíz si existen, clave local de storage si existe.
- La **clave de firma efectiva elegida explícitamente**, también si está fuera de
  storage. No captura secretos solo presentes en variables de proceso o un vault.

Manifiesto y hashes quedan dentro de un ZIP_STORED cifrado con DPAPI de usuario
Windows, sin LOCAL_MACHINE ni fallback en claro. DPAPI necesita normalmente la
misma identidad y equipo/material de perfil para descifrar: **no es una copia
portátil independiente del host**. Una copia offsite exige política de claves/
escrow y ensayo independiente; no se implementa por fingir que copiar el archivo
resuelve la pérdida de cuenta. No se envió nada a servicios externos.

Límites: 128 MiB total de contenido/ZIP, 5000 archivos y 32 MiB por archivo/DB;
contenedor cifrado hasta 129 MiB. Se rechazan enlaces/reparse/hardlinks, entradas
traversal/ADS/dispositivos, alias por mayúsculas/canonización, colisiones de árbol,
compresión, archivos extra y hashes inválidos. Los límites son conservadores para
este perfil, no se amplían silenciosamente para evidencias mayores.

Los temporales en claro se crean en carpeta privada, con cierre explícito de
conexiones y limpieza al terminar normalmente. Un crash puede dejar temporales
privados: controlar disco/retención, no prometer borrado seguro. La memoria, swap,
volúmenes y cuenta del operador requieren protección del host.

Backup requiere `--quiesced`: **el operador confirma que detuvo API, workers y demás
escritores**; el flag no los detiene ni bloquea las escrituras. Inventario/hashes
antes/después y dos copias DB detectan cambios, pero no garantizan snapshot atómico
ante cambios transitorios revertidos. Rechazo sin publicar backup ante cambios.

```powershell
.venv/Scripts/python.exe scripts/recovery_bundle.py backup RUTA_PROYECTO RUTA_PRIVADA/datos.opb --storage RUTA_STORAGE --database RUTA_DB --signing-key-file RUTA_CLAVE --quiesced
.venv/Scripts/python.exe scripts/recovery_bundle.py verify RUTA_PRIVADA/datos.opb
.venv/Scripts/python.exe scripts/recovery_bundle.py restore RUTA_PRIVADA/datos.opb DESTINO_NUEVO
```

El padre del backup debe ser privado (si es nuevo lo crea/protege). No sobrescribe
backup ni restauración. Verifica manifiesto completo, hashes y DB **antes de crear
el destino de restore**; nunca usa extractall. La restauración es **staging**, no
activación del servicio: preserva los bytes y valores originales, incluidas rutas
absolutas en DB/.env. Reubicar/reconfigurar esas referencias de forma trazable y
probar operación corresponde al ensayo de recuperación productivo posterior.

Se preservan bytes y valores SQLite; no es una imagen forense del volumen ni
preserva ACL originales, propietarios, timestamps NTFS o flujos alternativos.
La restauración aplica permisos privados nuevos al árbol de recuperación.

Excluidos: runtimes derivados, código/venv/dependencias, modelos Ollama, temporales,
pruebas, archivos de muestra externos y cualquier referencia fuera de los árboles
seleccionados salvo la clave explícita. Inventariar esos componentes y recuperar
la revisión correcta por separado. Los backups SQLite antiguos se conservan;
no se convierten retrospectivamente en cifrados.

## Ensayo de esta entrega

Respaldo inicial privado `storage/temp/e7-baseline-20261018`: DB, 116 archivos y
restauración previa. El ensayo cifrado usa **esa copia preservada, sin escritores**,
no una afirmación de que el servicio habitual fue detenido. Incluye además la clave
local nueva inicializada, no una clave previa inventada. Paquete
`encrypted/data.opb`, restauración `encrypted-restored`: **118 archivos verificados**,
SQLite íntegro, hashes y contenido confidencial no visible en el contenedor.
La DPAPI y ACL se ejercitan realmente en Windows. Resultados definitivos de
regresión/preservación se agregan a la auditoría y sección de validación.

La primera prueba detectó que comparar memoria/disco daba diferencias de cabecera
y que context managers SQLite no cerraban conexiones; se corrigió con dos snapshots
en disco y cierre explícito. No se repararon ni modificaron bases originales.

## Pendientes productivos: E7 continúa

Continuación del 2026-10-19: [cuenta dedicada y ACL de código](E7_SERVICE_ACCOUNT.md)
preparadas/probadas sobre staging sintético; cuenta deshabilitada. Los resultados
de esta sección corresponden al tramo inicial, no sustituyen la nueva auditoría.

Validación final 2026-10-19: **496 pruebas aprobadas, 1 omitida** (integración
Ollama real opt-in) y 4 avisos de deprecación, 734,15 segundos. Incluye las 21
pruebas nuevas de política, ACL, DPAPI y restauración adversarial. Sin cambios de
frontend en este tramo. Compose config y git diff --check pasan; build/runtime
Docker siguen sin probar. Comparación final confirma 74 tablas con valores y
esquema idénticos en base habitual/restaurada, 9 triggers y 116 archivos previos
intactos/restaurados; clave nueva recuperada con bytes idénticos.
Ver [auditoría de esta entrega](audits/e7-production-hardening-20261019.json).

1. Identidad dedicada y ACL de código preparadas con prueba real de acceso en
   staging; faltan runtime/venv protegido, lectura de clave efectiva y arranque
   completo bajo esa identidad; servicio/reinicio/actualizaciones.
2. Gateway TLS real, egreso por proveedor, secretos externos gestionados y MFA/
   recuperación de cuentas. El rechazo de CORS HTTP no demuestra que TLS exista.
3. Destino cifrado independiente/offsite, programación, retención sin borrar
   históricos, escrow de claves, RPO/RTO acordados y recuperación operativa desde
   fallo de host; bitácora/alertas de backup. No se creó scheduler sin esa política.
4. Monitorización y alertas sin evidencia sensible, cuotas físicas/compartidas,
   PostgreSQL y migraciones/multiinstancia, CI/SBOM/licencias y despliegue/pentest.
5. Validar Docker build/runtime con daemon disponible; no habilitar análisis Linux
   sin aislamiento equivalente validado. La muestra de perfil E6 sigue sin ser
   una adquisición de dispositivo real; la accesibilidad física E4 sigue pendiente.

Referencias primarias: [DPAPI de usuario y límites de recuperación](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata),
[DACL Windows](https://learn.microsoft.com/en-us/windows/win32/api/aclapi/nf-aclapi-setnamedsecurityinfow).
No certifica resistencia frente a un administrador del host ni disponibilidad de
un despliegue que todavía no se ha probado.
