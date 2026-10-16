# Auditoría de seguridad y dependencias — 2026-10-16

Registro histórico de la etapa 77c0971. El aislamiento del SO y las pruebas
posteriores están en [Pentest local](LOCAL_PENTEST.md); los límites de esta etapa
se mantienen aquí como evidencia de lo que se verificó entonces.

Alcance: código Python de `operia` y `apps/api`, entorno Windows x64 CPython
3.12.14 y lockfile npm completo, incluyendo herramientas de desarrollo. Revisión
manual de identidad, archivos, límites y conectores; pruebas con datos sintéticos.
No se realizó un pentest de infraestructura ni una adquisición de dispositivos.

## Dependencias y hallazgos corregidos

`pip-audit 2.10.1` encontró 32 entradas de avisos en cuatro paquetes, equivalentes
a **16 identificadores únicos** (el servicio devolvió entradas duplicadas).
`npm audit` encontró seis paquetes afectados: cinco de severidad alta y uno media.
La nueva consulta de ambos servicios devolvió cero vulnerabilidades conocidas.
Es una fotografía de sus bases de avisos, no una garantía sobre paquetes sin CVE.
Los identificadores, versiones y resultados están en
[el registro reproducible de la revisión](audits/security-audit-20261016.json).

| Dependencia | Antes | Corregida |
|---|---|---|
| Markdown | 3.7 | 3.11.1 |
| python-multipart | 0.0.20 | 0.0.32 |
| requests | 2.32.3 | 2.34.2 |
| Starlette | 0.41.3 | 1.8.0 |
| FastAPI, por compatibilidad con Starlette | 0.115.6 | 0.143.3 |

Se actualizó npm sin `--force`, conservando los rangos de `package.json`.
Se fijaron las 50 distribuciones Python del entorno validado en
`requirements-win-py312.lock`, con SHA-256 de ruedas compatibles. Es un lock de
desarrollo/pruebas para esa plataforma, no un entorno mínimo de producción ni
un lock portable a Linux. Las herramientas de auditoría tienen un entorno aparte.
Los hashes verifican los artefactos descargados; no certifican ausencia de malware.

Bandit 1.9.4: se corrigió el hallazgo alto B324 declarando MD5 como checksum
histórico sin uso de seguridad (`usedforsecurity=False`). SHA-256 sigue siendo
la comprobación de integridad. Quedan 13 avisos bajos revisados: B105 sobre
valores vacíos de esquema/tokens y el literal `bearer`; B404/B603 sobre procesos
con comando fijo, `shell=False`, sin argumentos ejecutables del usuario. No se
silenciaron reglas. La revisión no equivale a un análisis exhaustivo de flujo.

También se corrigieron la clave de firma predecible, sesiones que podían seguir
válidas después de cambiar organización/rol, administración entre organizaciones,
contraseñas por defecto, colisiones de archivos Mind y referencias de grafos entre
casos. Las nuevas contraseñas usan PBKDF2-HMAC-SHA256 con 600.000 iteraciones;
las antiguas se verifican y actualizan solamente después de un acceso correcto.

## Aislamiento de conectores

La salida requiere simultáneamente permiso de ruta, contexto autenticado,
organización activa, host exacto habilitado por el servidor y autorización de
esa organización para la finalidad concreta. No existe concesión implícita para
conectores nuevos. Las políticas inválidas deniegan la salida.

Cada operación usa un proceso Python de comando fijo, sin configuración de API,
ORM, `.env`, proxies o secretos heredados. La API termina el proceso al agotar
el presupuesto común de la solicitud (máximo 12 segundos, incluido DNS y cabeceras).
Hay cuatro operaciones globales, una por organización y 20 intentos/minuto por
organización. HTTPS mantiene DNS público validado y fijado, SNI/TLS y cuerpos
acotados; rechaza redirecciones. IA local exige dos habilitaciones y `ai:use`.

Esto no es un sandbox del sistema operativo: el hijo tiene la misma cuenta y
acceso al disco. Para proveedores o plugins no confiables se requieren cuentas
separadas, contenedores/aislamiento de SO y firewall. Las cuotas son por proceso;
varias instancias requieren cuotas compartidas. No se habilitó ningún proveedor
real ni se transmitieron evidencias durante esta revisión.

## Operación y preservación

La clave aleatoria se conserva en `storage/.auth-signing-key`, excluida de Git.
Protegerla con ACL del host y respaldarla con el almacenamiento completo.
Alternativamente, el operador puede proporcionar `OPERIA_AUTH_SIGNING_KEY`
mediante un gestor de secretos (al menos 32 bytes UTF-8, generado aleatoriamente).
No copiar claves a logs o repositorios. Las sesiones anteriores necesitan volver
a iniciar sesión; los registros históricos de sesión se conservan.

La política adicional se configura por un operador en `Organization.settings_json`:

```json
{"connectors":{"geo_ip":{"enabled":true,"hosts":["ipinfo.io"]},"legal_source":{"enabled":true,"hosts":["proveedor.example"]},"local_ai":{"enabled":false}}}
```

También hace falta la allowlist global `OPERIA_CONNECTOR_ALLOWED_HOSTS`. El
ejemplo no activa proveedores ni autoriza enviar evidencia. Se debe revisar
finalidad y datos mínimos antes de activar cada uno. No se añadió una API para
que administradores de casos modifiquen estas concesiones.

No hay migración destructiva ni reescritura de adquisiciones, revisiones,
proyecciones, BLOB originales, informes o cadena de custodia. Las notas Mind
nuevas usan rutas de organización/caso y creación exclusiva; las antiguas
conservan su ubicación. Un respaldo SQLite anterior se restauró a un destino
nuevo con `integrity_check` y SHA-256 idéntico:
`b2aaad233d98b5f11e2b9546c1cefe5f575d214bf6943eeea86f30e155a16371`.
El respaldo SQLite no contiene archivos externos ni la clave de firma.

## Repetición de las verificaciones

En un entorno de herramientas separado instalar `requirements-audit.txt`.
Ejecutar `python -m pip_audit --path .venv/Lib/site-packages --strict`,
`python -m bandit -r operia apps/api -ll`, `npm audit` en `apps/web`,
`python -m pytest -q -p no:cacheprovider` y `npm run build`.
Para instalación verificada usar pip `--require-hashes --only-binary=:all:` con
`requirements-win-py312.lock`; después ejecutar `pip check`. No usar un índice
privado o herramientas que expongan credenciales en los reportes.

Referencias: [pip-audit](https://github.com/pypa/pip-audit),
[npm audit](https://docs.npmjs.com/cli/commands/npm-audit/),
[OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html).

Validación final: **164 pruebas aprobadas**, cuatro advertencias de deprecación
(TestClient/httpx, ReportLab/ast y FastAPI on_event), en 216,16 s sobre el entorno
reconstruido. Se repitió además la prueba de restablecimiento acotado y entre
organizaciones: aprobada. `pip check` correcto; `npm ci --ignore-scripts` y
TypeScript/Vite 6.4.4 aprobados (1582 módulos). Las 72 tablas históricas se
compararon con el respaldo sin diferencias. No se silenciaron advertencias.
