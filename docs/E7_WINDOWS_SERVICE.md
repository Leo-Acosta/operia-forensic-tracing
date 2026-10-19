# E7: ciclo del servicio de Windows

Estado vigente: rotación DPAPI y recuperación local aceptadas. Ver la [auditoría de cierre de este tramo](audits/e7-dpapi-recovery-20261019.json). Los resultados parciales de abajo se conservan como historia de los ensayos anteriores.

Fecha: 2026-10-19. ContinuaciÃ³n del [runtime protegido](E7_SERVICE_RUNTIME.md).
El procedimiento estÃ¡ limitado deliberadamente a instalaciones de ensayo con
`synthetic_only: true`: no activa la instalaciÃ³n habitual ni importa su DB o clave.
Los resultados de ejecuciÃ³n se consolidan en la auditorÃ­a de este tramo.

**Estado real:** servicio de ensayo registrado, con inicio manual, detenido y
OperiaSvc deshabilitada. Se verificaron arranque de API, token sin privilegios,
integridad media, autoprueba AST en AppContainer, actualizaciÃ³n con backup y
rollback ante fallo de arranque. La aceptaciÃ³n integral todavÃ­a no pasÃ³: el
Ãºltimo intento de elevaciÃ³n UAC fue cancelado por Windows antes de ejecutarse.
La fuente final agrega la comprobaciÃ³n correcta de tablas de Ã¡tomos por Job y
su diagnÃ³stico, pero esa versiÃ³n no quedÃ³ activada. **E7 no estÃ¡ cerrado.**
Ver [auditorÃ­a y pendientes exactos](audits/e7-windows-service-20261019.json).

## Arquitectura y lÃ­mites

`scripts/OperiaService.cs` es un host SCM compilado con el compilador de .NET
Framework que ya trae Windows; no descarga NSSM, WinSW, pywin32 ni otro wrapper.
El host se ejecuta bajo la cuenta local OperiaSvc y crea Python suspendido, lo
asigna a un Job Object con KILL_ON_JOB_CLOSE y reciÃ©n entonces lo reanuda. AsÃ­,
la caÃ­da del host termina sus descendientes. Los jobs AppContainer existentes
siguen restringiendo el anÃ¡lisis nativo y el proveedor estÃ¡tico; no hay fallback
a ejecuciÃ³n sin sandbox.
Antes de crear procesos, reduce su etiqueta obligatoria a integridad media. El
supervisor mide esa etiqueta con GetTokenInformation y rechaza cualquier valor
distinto de 8192. Las rutas USERPROFILE/APPDATA/LOCALAPPDATA se obtienen de las
carpetas conocidas del token, no de valores de entorno heredados de otro perfil.

El supervisor arranca la API Ãºnicamente en 127.0.0.1 y dos pollers independientes.
Comprueba SID, ausencia de pertenencia administrativa/elevaciÃ³n, integridad de
cÃ³digo y runtime, denegaciÃ³n de escritura sobre archivos protegidos, guard
productivo mÃ­nimo y descifrado de un canario DPAPI. La disponibilidad incluye una
generaciÃ³n aleatoria y el PID del supervisor: el host rechaza archivos de estado
de una ejecuciÃ³n anterior. Una caÃ­da de API o worker hace fallar el servicio.
Una autoprueba AST con un texto fijo benigno debe ejecutarse dentro de
AppContainer antes de anunciar disponibilidad; su diagnÃ³stico solo contiene ese
texto de ensayo y metadatos del perfil, nunca evidencia de expedientes.
En sesiÃ³n 0, USER32 (dependencia indirecta de ctypes) requiere acceso de lectura
a objetos USER. La cuenta estÃ¡ndar no puede crear una estaciÃ³n con nombre. El
lanzador verifica que la estaciÃ³n actual sea Service-* y no sea visible, concede
Ãºnicamente al SID AppContainer reciÃ©n creado los derechos de inicializaciÃ³n
USER32 0x20123 (lectura/enumeraciÃ³n y Ã¡tomos) y usa un escritorio vacÃ­o
privado de integridad baja por trabajo. Solo ese SID tiene lectura/escritura en
su escritorio; los lÃ­mites UI del Job siguen aplicÃ¡ndose. Revoca la ACE de la
estaciÃ³n al cerrar; un mutex privado serializa los cambios entre pollers.
El Job virtualiza los Ã¡tomos en una tabla propia, comprobada contra un Ã¡tomo
del supervisor como control positivo. No cambia WinSta0 ni la DACL del
escritorio predeterminado del servicio, no concede acceso a ALL APPLICATION
PACKAGES en esos objetos, ni retira las restricciones UI 0xff del Job Object.
Los runtimes incluyen el hash de esta polÃ­tica en su identidad; cambiarla exige
preparar versiones nuevas, sin sobrescribir las anteriores.
La parada pide finalizar los pollers, cierra la API y espera trabajos en curso;
el Job Object garantiza limpieza si vence el plazo. Los trabajos persistentes
conservan sus mecanismos previos de reclamaciÃ³n y recuperaciÃ³n.

SCM tiene tres reinicios escalonados (5, 15 y 30 segundos), despuÃ©s ninguna
acciÃ³n; restablecimiento del contador a 24 horas. No reinicia el equipo ni lanza
comandos arbitrarios. El servicio se instala con inicio **manual**. La cuenta se
habilita al arrancar y se deshabilita tras la parada controlada. SCM carga el
perfil de la cuenta, sin conceder SeBackupPrivilege ni SeRestorePrivilege.

Se concede SeServiceLogonRight exclusivamente al SID esperado y se deniega
logon interactivo, remoto interactivo y de red. La denegaciÃ³n de logon de red
no equivale a un firewall de egreso. La cuenta debe seguir perteneciendo solo
a Users y no puede compartirse con otro servicio. La DACL de SCM reserva
administraciÃ³n y cambio de configuraciÃ³n a Administradores y SYSTEM.
La lista SCM de privilegios requeridos contiene Ãºnicamente
SeChangeNotifyPrivilege; no hereda los privilegios adicionales del logon de
servicio. Harden reaplica esta configuraciÃ³n a un servicio previamente detenido
usando su credencial actual, sin cambiar la contraseÃ±a ni la identidad.

```text
C:\ProgramData\OPERIA-E7-Service-<identificador>\
  host\Operia.Service.exe
  config\service.json, active-release.txt
  releases\<24 hex>\code, runtime, layout.json, runtime-manifest.json
  data\storage, memory_vault, logs, temp, control
  secrets\synthetic-signing-key.bin
  management\operation.lock, journal.jsonl
  backups\*.dpapi
```

CÃ³digo, host, runtime y configuraciÃ³n son RX para OperiaSvc. Los dos runtimes
derivados tambiÃ©n son RX y accesibles a AppContainer. Solo los datos necesitan
Modify; management y backups son privados del operador, Administradores y SYSTEM
y no conceden acceso al servicio. El secreto es de
Administradores, con lectura para OperiaSvc y acceso administrativo de SYSTEM.
El operador y los administradores del host son principales de confianza: estos
controles no impiden que un administrador malicioso reemplace el programa.

## Credenciales

`ServiceNative.cs` usa SecureString y buffers nativos que borra al liberarlos.
La contraseÃ±a no se convierte en texto para argv, scripts, JSON, .env o logs.
CreateServiceW/ChangeServiceConfigW pasan el buffer directamente a SCM; Windows
mantiene su credencial de servicio. El operador guarda su copia en Windows
Credential Manager, en el perfil del operador, con estos destinos:

```text
OPERIA/service/<nombre>/active
OPERIA/service/<nombre>/pending
```

OperiaSvc comprueba que no puede leer el destino del operador. Ese aislamiento
no impide al propio operador leer su credencial ni sustituye un vault empresarial.
El bootstrap puede fijar la contraseÃ±a solo de la identidad dedicada inicialmente
deshabilitada, con SID y descripciÃ³n exactos y sin otros servicios asociados.
La rotaciÃ³n posterior usa **NetUserChangePassword con contraseÃ±a anterior**,
actualiza la credencial cacheada en SCM y promueve el destino pending a active.
No utiliza un restablecimiento administrativo de contraseÃ±a sobre una identidad
en uso, para preservar el acceso DPAPI.

Se persiste pending antes de cambiar SAM. El journal registra etapas sin secretos
y un lock exclusivo evita administraciones concurrentes. Si una interrupciÃ³n
deja pending, Start/Restart/Update/Rotate se bloquean: RecoverCredential prueba
pending y active con logon de servicio, actualiza SCM con la vÃ¡lida y termina
detenido y con la cuenta deshabilitada. No hay una transacciÃ³n distribuida entre
SAM, SCM y CredMan; el journal y pending permiten resolver esa ventana. El
operador conserva su perfil/vault: perderlo no tiene recuperaciÃ³n automÃ¡tica.

La contraseÃ±a no expira por calendario de Windows en este ensayo; la operaciÃ³n
Rotate es explÃ­cita. Antes de producciÃ³n hay que definir responsable, frecuencia,
alertas, recuperaciÃ³n del operador y eventual migraciÃ³n a una cuenta administrada.

## OperaciÃ³n de ensayo

Ejecutar en PowerShell 7 de 64 bits **elevado**; no debilitar UAC ni la polÃ­tica de
ejecuciÃ³n. El descubrimiento del mÃ³dulo LocalAccounts usa la ruta real del mÃ³dulo
de Windows, incluida su subcarpeta de versiÃ³n. Crear primero un snapshot con
`scripts/stage_service.py`; preparar una raÃ­z ProgramData nueva con
`scripts/prepare-windows-service.ps1`. RuntimeSource debe ser una instalaciÃ³n
offline previamente validada, sin modificar dependencias ni reutilizar sus datos.

```powershell
$serviceRoot = 'C:\ProgramData\OPERIA-E7-Service-20261019'
.\scripts\manage-windows-service.ps1 -Root $serviceRoot -Action Status
.\scripts\manage-windows-service.ps1 -Root $serviceRoot -Action Harden
.\scripts\manage-windows-service.ps1 -Root $serviceRoot -Action Start
.\scripts\manage-windows-service.ps1 -Root $serviceRoot -Action Restart
.\scripts\manage-windows-service.ps1 -Root $serviceRoot -Action Rotate
.\scripts\manage-windows-service.ps1 -Root $serviceRoot -Action Stop
.\scripts\manage-windows-service.ps1 -Root $serviceRoot -Action RecoverCredential
```

No pasar contraseÃ±as como parÃ¡metros. El script rechaza cuenta con SID/grupos
incorrectos, enlaces/reparse, archivos alterados, otra cuenta privilegiada o
compartida, configuraciones ajenas y despliegues no sintÃ©ticos.

## ActualizaciÃ³n y recuperaciÃ³n

Publicar una versiÃ³n nueva en releases, con manifiestos Ã­ntegros; nunca editar
una versiÃ³n activa. Update verifica el candidato antes de parar el servicio.
Luego detiene escritores, crea y verifica un recovery bundle DPAPI del operador
(SQLite, evidencias, informes, memoria y clave sintÃ©tica), prepara los runtimes
derivados y cambia el archivo de selecciÃ³n con reemplazo atÃ³mico. Se preservan
las versiones anteriores y los respaldos. El backup reutiliza el lector privado
existente mediante una copia transitoria de la clave sintÃ©tica en scratch
administrativo, eliminada al terminar; no copia claves de la aplicaciÃ³n habitual.

```powershell
.\scripts\manage-windows-service.ps1 -Root $serviceRoot -Action Update -Release '<24 hex>'
.\scripts\manage-windows-service.ps1 -Root $serviceRoot -Action RecoverUpdate
```

Un candidato alterado se rechaza antes de la parada. Si falla el arranque de un
candidato Ã­ntegro, se selecciona y arranca la versiÃ³n anterior. **No se restaura
ni rebobina la DB**, ni se borran evidencia, custodia o informes. No se introducen
migraciones nuevas en este tramo: el rollback de cÃ³digo requiere compatibilidad
de esquema. Si la versiÃ³n anterior tampoco arranca, se conserva el estado para
recuperaciÃ³n manual. Un marcador update-pending persistido antes del cambio
bloquea otra operaciÃ³n normal; RecoverUpdate vuelve explÃ­citamente a la versiÃ³n
anterior, conserva la DB y valida el arranque. Una credencial pending debe
resolverse antes de recuperar la actualizaciÃ³n.

El recovery bundle estÃ¡ ligado al operador y equipo mediante DPAPI; no prueba
recuperaciÃ³n tras pÃ©rdida de host. La retenciÃ³n, copia independiente, escrow,
RPO/RTO y restauraciÃ³n autorizada de histÃ³ricos siguen siendo decisiones
productivas pendientes, junto con TLS, egreso y observabilidad.
Este backend de ensayo rechaza bundles mayores de 128 MiB, archivos/DB mayores
de 32 MiB y mÃ¡s de 5.000 archivos; superar un lÃ­mite bloquea la actualizaciÃ³n.

## AceptaciÃ³n

| ComprobaciÃ³n | Resultado de este tramo |
| --- | --- |
| Host/helper compilados y vault de Windows guardar/leer/borrar | PasÃ³ |
| SCM registrado, API loopback y autoprueba AST real | PasÃ³; ensayo sintÃ©tico |
| SID, Users solamente, token sin elevaciÃ³n, integridad 8192 y privilegio SCM mÃ­nimo | PasÃ³; consulta final de SCM y cuenta |
| ActualizaciÃ³n con backup cifrado y rollback conservando DB | PasÃ³ en los intentos con fallo de arranque; 7 bundles conservados |
| RegresiÃ³n selectiva | 161 aprobadas, 4 avisos; no es la suite completa |
| MÃ³dulo final y lÃ­mites del operador | 12 aprobadas; 10 se superponen con la regresiÃ³n, no se suman de nuevo |
| Trabajos nativo/AST por API bajo la versiÃ³n corregida del servicio | Pendiente; el primer proveedor fallÃ³ y el cliente posterior tenÃ­a un nombre de organizaciÃ³n duplicado, ya corregido |
| Canarios efectivos de archivos/memoria/red/clipboard/escritorio y Ã¡tomos por Job en SCM | Preparados; validaciÃ³n final pendiente por UAC cancelada |
| Reinicio con comprobaciÃ³n de PIDs y recuperaciÃ³n tras matar supervisor | Implementados, pendientes de prueba integral |
| RotaciÃ³n SAM/SCM, conservaciÃ³n DPAPI tras rotaciÃ³n y recuperaciÃ³n de pending | Implementadas, pendientes de prueba integral |
| Candidato alterado sin parar servicio, recuperaciÃ³n de actualizaciÃ³n interrumpida | Implementados y checks de integridad probados; escenarios completos SCM pendientes |

Para retomar, publicar primero un snapshot de la fuente actual como versiÃ³n
nueva y ejecutar Update con esa versiÃ³n. No editar el cÃ³digo de una versiÃ³n ya
publicada ni ejecutar el validador contra la versiÃ³n antigua: compara los hashes
de los controles relevantes con la copia de trabajo y exige publicar la fuente
actual. El ensayo de aceptaciÃ³n se encuentra en un script versionado:

QuedÃ³ preparado el snapshot local `storage/temp/e7-scm-final-source-20261019`
(225 archivos de cÃ³digo, sin datos ni secretos operativos). Su runtime estÃ¡
vacÃ­o por diseÃ±o: al publicarlo como candidato se copia Ãºnicamente el runtime
y runtime-manifest.json de la versiÃ³n verificada anterior; nunca sus datos.
El directorio de staging y los ensayos crudos son locales e ignorados por Git.

```powershell
.\scripts\validate-windows-service.ps1 -Root $serviceRoot -IncludeFaultInjection
```

Requiere una consola elevada y configuraciÃ³n sintÃ©tica. El switch declara que
se probarÃ¡n caÃ­das, candidatos alterados y ventanas de cambio de contraseÃ±a; sin
Ã©l se rechaza antes de operar. El PID que se mata se coteja con ejecutable,
comando fijo, SID y parentesco con el servicio. Escribe el resultado privado en
management/lifecycle-validation.json y termina con error si falla. Finalmente
detiene el servicio y deshabilita la cuenta; no borra DB, versiones o respaldos.
Los bearer de prueba se conservan exclusivamente cifrados con DPAPI del operador
para comprobar el mismo JWT y las revocaciones despuÃ©s de los reinicios.

La consulta final confirmÃ³: Manual/Stopped, PID 0, cuenta deshabilitada y solo
Users; credencial active presente, pending ausente y sin update-pending. El
Ãºltimo release activo de ensayo es 9d55a523ff52f27438b29a15, anterior a la fuente
final de aceptaciÃ³n. No se volviÃ³ a pedir ni ejecutar elevaciÃ³n tras la
cancelaciÃ³n UAC. La base habitual conserva 74 tablas con valores/esquema iguales,
9 triggers, 116 archivos anteriores/restaurados y la misma clave de firma.

Se prueba por separado: compilaciÃ³n del host/helper; selecciÃ³n e integridad de
versiones; SCM real y token no privilegiado; parada/reinicio con limpieza de
procesos; recuperaciÃ³n tras muerte del supervisor; API y trabajos nativo/AST;
default deny, concesiÃ³n/revocaciÃ³n y aislamiento de organizaciones; custodia
UPDATE/DELETE denegada; informe y entradas anteriores idÃ©nticos; rotaciÃ³n con
canario DPAPI conservado; recuperaciÃ³n de credencial pending; actualizaciÃ³n con
backup verificado, rechazo de alteraciÃ³n y rollback de arranque fallido. La
auditorÃ­a distingue lo ejecutado de lo pendiente y no usa la duraciÃ³n de IA como
horas humanas.

Referencias: [cuentas de servicio y perfil SCM](https://learn.microsoft.com/en-us/windows/win32/services/service-user-accounts),
[credenciales por sesiÃ³n del usuario](https://learn.microsoft.com/en-us/windows/win32/api/wincred/nf-wincred-credwritew),
[cambio con contraseÃ±a anterior](https://learn.microsoft.com/en-us/windows/win32/api/lmaccess/nf-lmaccess-netuserchangepassword),
[Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).
El diagnÃ³stico de sesiÃ³n 0 se apoya en [inicializaciÃ³n de USER32](https://learn.microsoft.com/en-us/troubleshoot/windows/win32/user32-kernel32-not-initialize),
[creaciÃ³n de estaciones](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-createwindowstationw)
y [derechos de una estaciÃ³n no interactiva](https://learn.microsoft.com/en-us/windows/win32/winstation/window-station-security-and-access-rights).

## Continuidad de aceptaciÃ³n integral del 2026-10-19

Se retomÃ³ con autorizaciÃ³n explÃ­cita de elevaciÃ³n UAC. La aceptaciÃ³n HTTP bajo
SCM comprobÃ³ trabajos AST y nativos, default deny, concesiÃ³n/revocaciÃ³n, aislamiento
entre organizaciones, custodia UPDATE/DELETE denegada e informes histÃ³ricos.
TambiÃ©n pasaron reinicio con limpieza de PIDs y recuperaciÃ³n SCM tras la muerte
controlada del supervisor. Los datos habituales no se migraron al ensayo.

La rotaciÃ³n detectÃ³ dos defectos: NetUserChangePassword rechazÃ³ la credencial
larga con error 1325; el cambio mediante SSPI sin migraciÃ³n efectiva del perfil
no conservÃ³ la capacidad de descifrar el primer canario DPAPI sintÃ©tico. Ese
canario se conserva sin sobrescribir en data/control/credential-canary.dpapi,
SHA256 b445ab27c085ea26f8d1d554b363860a1c16a0342a32517aacb5c0144c7e54d1.
No se afirma que siga siendo descifrable. No contenÃ­a evidencia, contraseÃ±as ni
claves: era un texto fijo de ensayo. La versiÃ³n de prueba actual usa un canario
v2 separado; su aceptaciÃ³n exige conservar los mismos bytes y descifrarlos tras
cada rotaciÃ³n. La versiÃ³n nueva no convierte el intento anterior en exitoso.

El protocolo corregido conserva previous y pending en Credential Manager antes
del cambio SAM. SSPI usa la contraseÃ±a anterior conocida, sin reset administrativo.
La migraciÃ³n se realiza dentro del proceso SCM, mediante CryptUpdateProtectedState,
con una conexiÃ³n local de una sola instancia. El pipe tiene propietario
Administrators, DACL para Administrators/SYSTEM/SID exacto de OperiaSvc,
FIRST_PIPE_INSTANCE y REJECT_REMOTE_CLIENTS. El cliente comprueba propietario;
el servidor coteja el SID del proceso cliente. La contraseÃ±a anterior solo pasa
por memoria y buffers del canal, que se limpian; no va a argv, entorno, archivos
ni logs. AppContainers no reciben una ACE de acceso al canal.

La credencial anterior no se elimina hasta que el proceso SCM haya completado
migraciÃ³n, descifrado del mismo canario y readiness. RecoverCredential puede
reanudar esta ventana. Las recuperaciones admiten una versiÃ³n de rescate explÃ­cita,
verificada antes de seleccionarse; no restauran ni retroceden la base de datos.

La prueba negativa del canal rechaza un propietario sin elevar antes de transmitir
secretos. La compilaciÃ³n del helper de migraciÃ³n se incluye en las pruebas Windows.
Los resultados definitivos de esta continuidad se incorporan en una auditorÃ­a
separada; la auditorÃ­a parcial previa permanece como histÃ³rico.

Referencias de la correcciÃ³n: [SSPI ChangeAccountPasswordW](https://learn.microsoft.com/en-us/windows/win32/api/sspi/nf-sspi-changeaccountpasswordw),
[CryptUpdateProtectedState y ejecuciÃ³n desde la cuenta destino](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptupdateprotectedstate).

### Resultado final de esta continuidad: aceptaciÃ³n parcial

La [auditorÃ­a nueva](audits/e7-windows-service-acceptance-20261019.json) registra
164 pruebas de regresiÃ³n seleccionada aprobadas y 13 pruebas del mÃ³dulo Windows
aprobadas despuÃ©s de los Ãºltimos cambios. No es una ejecuciÃ³n de toda la suite.
Los trabajos reales con datos sintÃ©ticos, permisos, custodia, reinicio y recuperaciÃ³n
SCM pasaron. La rotaciÃ³n con preservaciÃ³n del mismo canario DPAPI NO pasÃ³.
CryptUpdateProtectedState declarÃ³ 1 clave migrada / 7 obsoletas, pero el descifrado
real fallÃ³ tanto mediante suplantaciÃ³n como en SCM; esos contadores no acreditan
recuperaciÃ³n. Los dos canarios anteriores siguen conservados sin sobrescribir y
no se afirma que puedan descifrarse. Los datos habituales y su clave siguen intactos.

La correcciÃ³n preparada genera contraseÃ±as aleatorias de 52 caracteres para el
camino local NetUserChangePassword; el puente SSPI queda para credenciales largas
preexistentes. previous/pending se conservan hasta verificar readiness, descifrado
real y hash idÃ©ntico del canario existente. Ante error, se detiene el servicio y
se deshabilita la cuenta. La recuperaciÃ³n puede considerar previous si pending y
active ya no corresponden al SAM. No se exponen contraseÃ±as ni se rebajan polÃ­ticas.

Estado comprobado al terminar: OperiaE7Validation Manual/Stopped, PID 0;
OperiaSvc deshabilitada, solo SeChangeNotifyPrivilege requerido por SCM;
active/pending/previous presentes en el almacÃ©n cifrado del operador;
sin update-pending. El release activo 8363bcbbea5158a98a330695 no estÃ¡ listo y
es anterior a la fuente final. NO habilitar el servicio sin recuperar esta ventana.

La Ãºltima elevaciÃ³n UAC fue cancelada por Windows; no se solicitÃ³ otra despuÃ©s.
El snapshot final storage/temp/e7-scm-next-source-20261019 contiene 227 archivos
de cÃ³digo y ningÃºn dato/clave operativos. El ensayo local ignorado
storage/test_runs/e7-scm-v3-acceptance.ps1 estÃ¡ preparado para una transiciÃ³n
explÃ­cita del entorno sintÃ©tico conservando los canarios anteriores y una copia
sellada de la credencial asociada al segundo canario. NO fue ejecutado; la versiÃ³n
v3 del canario no existe aÃºn. Su creaciÃ³n no acreditarÃ­a recuperaciÃ³n de v1/v2:
solo una nueva ronda que conserve y descifre exactamente v3 tras cada cambio
podrÃ¡ aceptar el protocolo corregido. Revisar ese ensayo antes de retomarlo.

Quedan pendientes la aceptaciÃ³n completa de rotaciÃ³n/recuperaciÃ³n de credencial,
actualizaciÃ³n vÃ¡lida, candidato alterado, rollback de arranque e interrupciÃ³n de
actualizaciÃ³n, y la restauraciÃ³n del respaldo del servicio a un Ã¡rbol nuevo.
El verificador preparado de esa restauraciÃ³n no se ejecutÃ³ porque exige primero
que pase el ciclo de vida. El respaldo habitual previo sÃ­ sigue verificado:
74 tablas completas/esquema, 9 triggers, 116 archivos y clave de firma idÃ©nticos.
Los informes JSON anteriores se mantienen como histÃ³ricos de sus respectivos intentos.


## Cierre del tramo DPAPI y recuperación, 2026-10-19

La corrección pasa el SID explícito del token de OperiaSvc a
CryptUpdateProtectedState dentro del proceso SCM. En esta estación, la llamada
con SID nulo declaraba migraciones sin recuperar el descifrado; el SID explícito
sí recuperó el mismo canario. El criterio sigue siendo descifrado real más hash
idéntico, identidad correcta y readiness; nunca el contador de claves migradas.
No se cambió a DPAPI de máquina ni se habilitó una excepción de privilegios.

Pasaron rotación normal, interrupción tras SAM antes de SCM, fallo de migración
forzado con vuelta verificable a la credencial anterior, caída del supervisor,
actualización válida, candidato alterado, rollback de arranque fallido y
recuperación de actualización interrumpida. Los mismos JWT, revocaciones, informes
y custodia se verificaron entre etapas. El respaldo cifrado del servicio se
restauró en un árbol nuevo; se cotejaron todas sus tablas, esquema, triggers,
archivos y clave. No se restauró ni retrocedió la base en uso.

El canario v2 histórico también se recuperó con su credencial conservada, sin
sobrescribir sus bytes. V3 conserva el mismo ciphertext después de las rotaciones
y recuperaciones. V1 queda como límite explícito: es un canario sintético fijo
del prototipo anterior, conservado sin descifrado porque falta la credencial
original; no contiene evidencia, informes, contraseñas ni la clave de firma.
No se presenta su conservación física como recuperación criptográfica.

La recuperación de credenciales devuelve recovery_outcome para distinguir
committed_pending de rolled_back_previous_preserving_dpapi. Ante un fallo no
se elimina la credencial anterior hasta recuperar el mismo canario y verificar
el arranque. El ensayo dirigido puede ejecutarse con -Scenario CredentialRollback;
el informe separado evita confundirlo con la aceptación integral Full.

Los fallos acumulados de ensayos anteriores agotaron el presupuesto de reinicios
SCM. La prueba sintética de caída aísla su contador con reset=0 y restaura siempre
reset=86400 y tres reinicios acotados. El handle administrativo usa únicamente
SERVICE_CHANGE_CONFIG y SERVICE_START, requeridos para acciones de reinicio.
Esto no concede derechos adicionales a OperiaSvc.

Estado final: servicio Manual/Stopped, PID 0, cuenta deshabilitada; active presente,
pending/previous ausentes y sin actualización pendiente. La credencial archivada
de v2 permanece sellada para su trazabilidad. La regresión seleccionada pasó 164
pruebas y el módulo Windows final 13 (incluidas en parte en la regresión).
Los datos habituales siguen preservados: 74 tablas completas, 9 triggers,
116 archivos y la misma clave. No se contabilizaron horas humanas por duración
de IA o de pruebas. E7 productiva continúa pendiente de TLS, secretos efectivos y
recuperación independiente del host/operador, entre otros controles ya documentados.

Referencias: [CryptUpdateProtectedState](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptupdateprotectedstate) y
[permisos para configurar acciones SCM](https://learn.microsoft.com/en-us/windows/win32/api/winsvc/nf-winsvc-changeserviceconfig2w).
