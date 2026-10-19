# E7: identidad dedicada y código de solo lectura

Validación local Windows: 2026-10-19, continuación de `4280c56`.
**Cuenta preparada y ACL probadas; servicio productivo todavía no activado.**

## Resultado real

Se creó `OperiaSvc`, cuenta local estándar, miembro únicamente del grupo Usuarios
(SID de grupo S-1-5-32-545). Se verificó que no pertenece a Administradores.
Quedó **deshabilitada** después del ensayo. No se tocaron otras cuentas ni se
asignaron derechos de inicio como servicio, tareas programadas o inicio automático.

La prueba utilizó un token real obtenido mediante LogonUser y suplantación
sincrónica de identidad para operaciones de archivos; no una comparación textual
de ACL ni una simulación de usuario. El token y el búfer nativo de contraseña se
liberan al terminar. La cuenta se deshabilita en bloques finally, incluso ante
errores ordinarios. Un cierre forzado del proceso durante la breve prueba requiere
comprobar manualmente su estado; no se promete recuperación ante cualquier crash.

| Área nueva de staging | Acceso de OperiaSvc | Prueba realizada |
| --- | --- | --- |
| Raíz y código | ReadAndExecute | Lectura de canario permitida; modificación, creación y eliminación denegadas |
| data/storage, memory_vault, logs y temp | Modify | Crear, leer y eliminar archivos sintéticos |
| runtime | ReadAndExecute | Creación denegada; instalación de Python/dependencias pendiente |
| secrets | ReadAndExecute | Creación denegada; sin claves operativas copiadas ni lectura de clave real atribuida al ensayo |

Las DACL están protegidas, con propietario operador y control total para operador,
SYSTEM y Administradores; la cuenta de ejecución no es propietaria ni puede
cambiar las ACL. El control total de los administradores es un límite de confianza
del host, no resistencia frente a un administrador comprometido.

Además del ensayo efectivo con canario, se inspeccionaron las ACL de los 210
archivos: DACL protegidas, cuenta no propietaria y sin permisos de escritura,
eliminación, cambio de DACL o toma de propiedad. Sus hashes siguen idénticos.

El directorio validado está en
`storage/temp/e7-service-account-20261019-verified`. Contiene una copia de 210
archivos de código/canario con manifiesto SHA-256, carpetas de datos vacías y
resultados locales. El repositorio de desarrollo conserva sus permisos originales.
No se copiaron expedientes, bases, evidencias, informes ni claves de firma a la
cuenta nueva. Los intentos previos quedan en carpetas separadas como trazabilidad.

## Herramientas y uso

`scripts/stage_service.py DESTINO_NUEVO` genera una copia privada con selección
explícita de código y configuración de ejemplo, sin .env real, DB o claves.
Rechaza destino existente, solapamiento con árboles de código y enlaces/reparse
o hardlinks. No instala dependencias ni activa la aplicación.

```powershell
.venv/Scripts/python.exe scripts/stage_service.py RUTA_NUEVA
pwsh -NoProfile -File scripts/prepare-service-account.ps1 -DeploymentRoot RUTA_NUEVA -ValidateModule
# En una consola elevada, solo sobre la copia preparada y vacía:
pwsh -NoProfile -File scripts/prepare-service-account.ps1 -DeploymentRoot RUTA_NUEVA -Apply
```

El modo plan no crea cuentas ni modifica ACL. Apply requiere PowerShell de 64
bits elevado y vuelve a verificar inventario/hashes y ausencia de datos antes de
mutar. La carga de LocalAccounts usa exclusivamente el árbol de módulos de
System32, acepta instalación directa o carpetas de versión y rechaza reparse;
no busca en directorios de usuario ni instala módulos de Internet.

Se rechazan cuentas existentes por defecto. `-ResumeAccountSid SID_EXACTO`
permite retomar únicamente una identidad deshabilitada cuyo SID y descripción
coincidan con la cuenta preparada. Reemplaza su contraseña temporal de staging;
no es una operación de rotación de claves de OPERIA. Revisar siempre el resultado
previo antes de usarlo. No reutilizar esta opción para cuentas activas.

La contraseña aleatoria de ensayo vive en memoria, no se entrega por argumento,
archivo o log y se descarta al finalizar. No queda una contraseña de servicio
operable en el repositorio. La activación exige aprovisionamiento seguro de una
credencial nueva y su ciclo de vida; no se configuró PasswordNeverExpires.

La carpeta secrets de este ensayo conserva también una ACE explícita del operador
y propietario operador, para administración de staging. Antes de alojar la clave
real debe reprovisionarse con propietario Administradores/SYSTEM, ACE solamente
para identidad de servicio, SYSTEM y Administradores, lectura para el servicio y
control administrativo para los otros. La política read_key valida desde la
identidad ejecutora y rechazaría la ACE/propietario del operador ajeno al conjunto
permitido; no basta copiar una clave a la carpeta de ensayo.

## Separación de rutas

Los runtimes AppContainer del motor y del laboratorio ahora se ubican bajo
`OPERIA_STORAGE_DIR`, en sandbox-runtime y static-lab-runtime. Antes se vinculaban
al directorio del código. Los hashes de identidad, manifiestos y verificaciones
del sandbox siguen siendo obligatorios; no se añadió fallback de aislamiento.

Para el despliegue previsto: código y Python/dependencias preinstalados por el
administrador en árboles de lectura, `OPERIA_STORAGE_DIR` en data/storage,
SQLite en ese storage y memory_vault en data/memory_vault. Los runtimes derivados
deben prepararse/verificarse explícitamente; el supervisor no recibe escritura
sobre código o dependencias. Esta entrega valida rutas y ACL, no el arranque de
toda la aplicación bajo la cuenta ni su compatibilidad con un runtime instalado.

## Validación y pendientes

Pasaron 25 pruebas específicas antes del ensayo elevado: preparación, rechazo de
datos/enlaces/alteración, plan sin mutaciones, carga real del módulo, rutas
externas y pruebas E7 de secretos/DPAPI. La regresión completa y comparación final
se registran en [auditoría del tramo](audits/e7-service-account-20261019.json).
Las 4 pruebas de preparación también se repitieron sobre el script final y pasan.

La ejecución integral recorrió 501 casos: 498 aprobados, 2 fallos y 1 omitido
(Ollama real opt-in), 4 avisos de deprecación, 1484,90 segundos. Los dos fallos
eran preparaciones antiguas de workers en proceso nuevo: configuraban storage
vacío y dependían del runtime global del repositorio. Ahora preparan el runtime
aislado en su storage explícito; no se cambiaron las aserciones de finalización
ni custodia. Cada caso corregido pasó por separado; la repetición conjunta con
las pruebas E7 terminó con **27 aprobadas**, 4 avisos, 63,31 segundos. No se
repitieron los 501 casos después de modificar solo esas dos preparaciones de
prueba; no se presenta aquella ejecución integral como una ejecución sin fallos.
La comparación posterior confirmó 74 tablas con valores y esquema idénticos,
9 disparadores, 116 archivos originales/restaurados y clave de firma sin cambios.

Se corrigieron tres problemas hallados durante las pruebas: ruta del módulo sin
carpeta de versión, SID pasado como tipo incorrecto al parámetro Member y
comparador del canario que no aceptaba CRLF. La cuenta quedó deshabilitada después
de cada intento que alcanzó su creación. Ninguno modificó históricos.

Pendientes: instalar y proteger runtime Python/dependencias; aprovisionar clave
efectiva preservando sus bytes; configuración absoluta, arranque y sandbox bajo
la nueva identidad; restricciones de logon/egreso y derecho de servicio según el
modelo operativo; servicio/reinicio/actualizaciones; TLS y recuperación externa.
Los runtimes derivados del sandbox quedan bajo storage y por ahora heredan su
área modificable; sus manifiestos se verifican al usarlos. Proteger sus árboles
como RX después de la preparación administrativa y probar su actualización es
parte del despliegue pendiente, no una garantía de este ensayo con runtime vacío.
No habilitar producción con esta carpeta de ensayo ni confundir datos vacíos con
una migración productiva validada.

Referencias: [New-LocalUser](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.localaccounts/new-localuser?view=powershell-5.1),
[LogonUser](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-logonuserw),
[derechos de archivos](https://learn.microsoft.com/en-us/dotnet/api/system.security.accesscontrol.filesystemrights).
