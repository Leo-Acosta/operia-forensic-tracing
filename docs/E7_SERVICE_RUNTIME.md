# E7: runtime independiente y arranque con OperiaSvc

Continuación de `f1d9b04`, 2026-10-19. Este tramo prepara y prueba un despliegue
aislado con datos sintéticos; no activa el servicio productivo ni migra datos.

## Instalación offline

Instalación validada: `C:\ProgramData\OPERIA-E7-Runtime-20261019-R2`. El intento
anterior y el staging del repositorio se conservan como trazabilidad. Elegir una
ubicación administrativa fuera del perfil del desarrollador permite validar los
antecesores de rutas privadas sin ampliar acceso al perfil personal.

`scripts/install_service_runtime.py` instala dentro de un staging nuevo generado
por `scripts/stage_service.py`. Usa CPython 3.12.14 de la instalación local y el
cierre de dependencias de requirements.txt, incluidas las opciones standard de
Uvicorn. No modifica la .venv, no descarga paquetes ni resuelve versiones nuevas.
La .venv no contiene pip: no se atribuye una ejecución exitosa de pip check.
El instalador usa packaging en el entorno del operador (26.3 en esta instalación,
ya disponible con requirements-dev/pytest); no lo añade al runtime de la API.

Se instalaron **42 distribuciones**, con stdlib, DLLs, recursos de share/include,
licencias/metadatos y manifiesto SHA-256 de **3.734 archivos**. Se excluyen wrappers
de consola (los procesos usan python -m), pycache y herramientas de pruebas ajenas
al cierre. Los recursos declarados de las distribuciones seleccionadas se copian
íntegros; no se afirma que se hayan eliminado sus módulos internos de pruebas.

El instalador exige versiones directas exactas, comprueba restricciones transitivas
y extras/markers, rechaza dependencias ausentes o incompatibles, RECORD faltante,
hash/tamaño alterado, enlaces, rutas externas no admitidas y hooks .pth. Lee el CSV
RECORD directamente porque Distribution.files puede omitir archivos ausentes.
Solo se admiten site-packages y recursos share/include dentro del entorno; los
archivos del intérprete provienen de la base local explícita.

RECORD y el manifiesto verifican consistencia respecto de la instalación del
operador, **no autenticidad upstream** ni ausencia de vulnerabilidades. Un
wheelhouse firmado/verificado, lock reproducible externo, SBOM/licencias y CI
siguen siendo requisitos de cadena de suministro para producción.

`python312._pth` restringe sys.path a Lib, DLLs, site-packages y la copia de código.
No importa site ni procesa hooks de usuario; se usa -B explícito para evitar
bytecode, también en preparación administrativa. La prueba de importación local
confirmó isolated=1, no_site=1, base_prefix dentro del runtime e importación de
FastAPI, SQLAlchemy, Uvicorn, python-docx, ReportLab, Requests y Folium.

## Protección y ensayo privilegiado

`scripts/validate-service-runtime.ps1` exige consola elevada de 64 bits y el SID
exacto de OperiaSvc, deshabilitada y miembro únicamente de Usuarios. Verifica
inventario/hashes de código y runtime, ausencia de datos/secretos anteriores y
ausencia de reparse antes de aplicar cambios al staging.

La política prevista da RX al código, intérprete y dependencias; Modify solo a
storage, memory_vault, logs y temporales. Los runtimes AppContainer se preparan
administrativamente y sus árboles completos quedan RX para OperiaSvc y los
AppContainers, con verificación de manifiestos existente. La cuenta no puede
reemplazar esos árboles mediante los permisos del padre.

Ese alcance de escritura se refiere al árbol de despliegue. La cuenta estándar
conserva los permisos normales de su perfil Windows, necesario para los perfiles
AppContainer; el supervisor no se convierte en un contenedor global. Los hijos
de análisis conservan su aislamiento AppContainer/Job existente.

Secrets usa propietario Administradores y ACE solo para Administradores/SYSTEM
(control administrativo) y OperiaSvc (lectura). Se genera una clave **sintética**
nueva de 32 bytes: no se copia, reemplaza o rota la clave de la aplicación habitual.

La contraseña temporal de la cuenta solo se utiliza en memoria con ProcessStartInfo,
sin argumentos ni logs. El proceso se inicia con credenciales de OperiaSvc y su
perfil cargado, entorno por allowlist y sin heredar variables de firma o Python
del operador. La carga del perfil puede crear el perfil local Windows de la cuenta.
El ensayo termina procesos en timeout y deshabilita la cuenta en finally; no
instala servicio, scheduler, inicio automático o PasswordNeverExpires. Un cierre
forzado del lanzador exige comprobar su estado y procesos; no se promete limpieza
ante cualquier caída del host.

```powershell
.venv/Scripts/python.exe scripts/stage_service.py RUTA_NUEVA
.venv/Scripts/python.exe scripts/install_service_runtime.py RUTA_NUEVA
# Consola elevada, identidad dedicada previamente preparada y deshabilitada:
pwsh -NoProfile -File scripts/validate-service-runtime.ps1 -DeploymentRoot RUTA_NUEVA -AccountSid SID_VERIFICADO
```

No ejecutar sobre una instalación con datos ni reutilizar como activador
productivo. El guard de datos vacíos impide confundir un ensayo con una migración.

## Qué debe validar el proceso real

El probe de operador `scripts/service_runtime_probe.py` no acepta una DB o URL
arbitraria: utiliza una base nueva e7-runtime-validation.db bajo data/storage y
HTTP en 127.0.0.1 con puerto asignado por el sistema. Comprueba SID/token reales,
ausencia de privilegios administrativos, aislamiento de Python, versiones,
archivos/carpetas RX y lectura de la clave sintética con la política privada.

Arranca Uvicorn y la API con OPERIA_ENV=production para ejercitar el guard mínimo;
HTTPS de CORS es sintético, **no prueba existencia de TLS**. La inicialización
pública bootstrap debe seguir rechazada. Se crean dos organizaciones y usuarios
solo en esa DB nueva, se usa login normal y se prueban denegación por defecto,
concesión/revocación de expediente y denegación entre organizaciones.

Un archivo Python benigno se analiza mediante worker CLI y CPython AST en
AppContainer/Job (su contenido no se ejecuta); un texto Android de paquetes
sintético pasa por el worker nativo CLI y su AppContainer. Se conservan filas
previas del informe/custodia del ensayo y se rechaza UPDATE/DELETE de custodia.
No hay fallback a ejecutar muestras o workers sin aislamiento.

## Resultados y límites

Instalación y pruebas unitarias: 7 aprobadas. Regresión selectiva de seguridad:
**114 aprobadas**, 4 avisos de deprecación, 322,93 segundos; no se ejecutó otra
vez la suite completa de 504 casos. Incluye permisos, custodia, recuperación,
pentest local y workflows de workers en procesos nuevos. La prueba real con la
cuenta se registra en la [auditoría del tramo](audits/e7-service-runtime-20261019.json).

El primer ensayo bajo el perfil personal rechazó la validación del secreto aunque
la DACL mostraba los tres principales previstos. En ProgramData, con la misma
política, se pasó ese control y arrancó la API. No se ampliaron permisos del perfil
personal. El cliente de ensayo anunciaba JSON en GET vacío y fue rechazado por el
guard de cuerpos; se corrigió ese cliente, manteniendo la política de la API.
El ensayo final R2 **pasó**: token real de OperiaSvc sin privilegios, guard mínimo
productivo, API HTTP lista, worker nativo completado y proveedor AST verificado
en AppContainer/Job. Se probaron denegación por defecto, concesión y revocación
por expediente, aislamiento entre organizaciones, conservación de informe/custodia
previos del ensayo y rechazo de UPDATE/DELETE de custodia; SQLite integrity ok.

Se auditaron las ACL de **5.302 archivos** de código, Python/dependencias y ambos
runtimes derivados: OperiaSvc no es propietaria y no tiene escritura, eliminación,
cambio de DACL o toma de propiedad. El lanzador verificó otra vez los inventarios
y hashes de código/runtime después de ejecutar. La cuenta terminó deshabilitada.

Comparación final de la instalación habitual: **74 tablas con valores y esquema
idénticos, 9 disparadores, 116 archivos originales/restaurados y clave de firma
sin cambios**. No se migraron ni reescribieron expedientes o históricos reales.
Los resultados sanitizados de ejecución están en data/logs/runtime-trial.json y
runtime-admin-result.json de la instalación de ensayo; los manifiestos detallados,
binarios, DB, claves sintéticas y logs no se incorporan a Git.

Pendientes productivos independientes: servicio/reinicio/actualizaciones, cuenta
y credencial gestionadas, restricciones de logon y egreso, TLS, configuración y
clave efectivas preservadas, retención/offsite/escrow y recuperación de host,
aceptación operativa y regresión de despliegue. La cuenta se mantiene deshabilitada
fuera de las ventanas controladas de prueba.

Referencias: [Python ._pth](https://docs.python.org/3.12/library/sys_path_init.html#pth-files),
[carga de perfil de Windows](https://learn.microsoft.com/en-us/dotnet/api/system.diagnostics.processstartinfo.loaduserprofile).
