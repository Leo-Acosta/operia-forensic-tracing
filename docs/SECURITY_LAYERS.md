# Capas de seguridad y contrato de conectores

Estado: 2026-10-16. Controles de aplicacion implementados y probados con datos
sinteticos. Pentest local acotado y contencion Windows: [informe](LOCAL_PENTEST.md).
No constituyen una certificacion de invulnerabilidad.

## Fronteras implementadas

| Riesgo | Control | Limite |
|---|---|---|
| Acceso entre organizaciones/casos | Sesion obligatoria, permiso por modulo/metodo, filtros ORM heredados por caso y documento padre, validacion de referencias | Es control de aplicacion; no RLS ni defensa ante administradores de la base |
| Referencias manipuladas | Artefactos seleccionados dentro de la revision incorporada, hashes y FK de caso, validacion de IDs en hipotesis | El texto profesional sigue requiriendo revision humana |
| SSRF y fuga mediante conectores | Salida HTTPS denegada por defecto, hosts exactos configurados, todos los resultados DNS publicos, conexion a IP validada con SNI/TLS del host original, sin proxies de entorno ni redirecciones | No reemplaza firewall de egreso; proceso hijo con deadline comun de hasta 12 s; AppContainer/Job en Windows, sin fallback |
| Ejecucion de comandos | Retirada de shell arbitraria por API; los workers usan exclusivamente comandos fijos | AppContainer sin red para el analizador, Job de 256 MiB/10 s CPU/1 proceso; supervisor aun requiere cuenta sin privilegios |
| Recuperacion indebida de administrador | Recuperacion local apagada por defecto; requiere habilitacion de configuracion y solicitud local | No mantenerla habilitada durante operacion normal |
| Solicitudes excesivas | 8 MiB, lectura en 15 s, 240 solicitudes/minuto por peer, 20 POST de identidad/minuto y 8 solicitudes simultaneas | Cuotas locales por proceso; gateway compartido requerido para despliegues multiples |
| Respuestas de proveedores | Cuerpo maximo 256 KiB, encoding identity, redirecciones rechazadas, JSON acotado sin duplicados ni no finitos, tiempo de lectura limitado | El padre termina el proceso cuando vence el presupuesto total |
| Contenido activo | React/texto, HTML de informes escapado, mapas SVG estaticos sin JS/CDN/tiles externos; descarga de mapas con CSP sandbox | Los documentos descargados siguen siendo material no confiable para otros programas |
| Abuso del navegador | Origen de escrituras limitado a CORS configurado, nosniff, no-referrer, SAMEORIGIN, Permissions-Policy y no-store para API | Bearer no protege frente a una extension maliciosa o equipo comprometido |
| Agotamiento y ambiguedad de entrada | Cuerpo contado aun sin Content-Length, framing ambiguo y compresion rechazados, JSON con profundidad/estructura acotadas | El proxy debe limitar conexiones, cabeceras y tiempo total |
| Auditoria | UUID por solicitud, eventos de rechazo con codigo sin payload/token, auditoria de proyecciones y actor de dominio | Logs deben centralizarse y protegerse fuera del proceso |

## Configuracion segura por defecto

- `OPERIA_CONNECTOR_ALLOWED_HOSTS=[]`: ninguna salida del cliente de conectores.
  Para habilitar un proveedor aprobado usar una lista JSON de hosts exactos,
  por ejemplo `["ipinfo.io"]`. No usar destinos procedentes de la evidencia.
- `OPERIA_LOCAL_AI_ENABLED=false` y `OPERIA_LOCAL_AI_GATEWAY_ENABLED=false`: la
  pasarela interna es opt-in, con caso, ai:use y modelos concedidos por organizacion.
  Solo el broker confiable conecta al destino fijo; los validadores siguen en
  AppContainer sin red. No hay excepcion de loopback. Ver LOCAL_AI_GATEWAY.md.
- `OPERIA_LOCAL_RECOVERY_ENABLED=false`: no hay recuperacion automatica por HTTP.
  Un operador del host puede habilitarla temporalmente en entorno local y apagarla
  inmediatamente despues. Se conserva la autenticacion normal.
- `OPERIA_HTTP_MAX_BODY_BYTES=8388608`, `OPERIA_HTTP_MAX_CONCURRENT_REQUESTS=8`,
  `OPERIA_HTTP_REQUESTS_PER_MINUTE=240`, `OPERIA_HTTP_AUTH_PER_MINUTE=20`.
- Los rechazos entregan 400/403/408/413/415/422/429/503 segun el control, con
  identificador de solicitud; 429/503 incluyen Retry-After.

No se ejecutan comandos de laboratorio enviados por usuarios. Las integraciones
futuras con herramientas requeriran adaptadores de argumentos fijos, allowlist
administrada, limites de recursos y aislamiento del proceso. No habilitar shell.
La API Geo Trace ya no abre URLs de evidencia ni resuelve sus dominios. La consulta
de IPs a un proveedor requiere host HTTPS global y concesion geo_ip de su organizacion. El
proveedor anterior por HTTP se retira; sus registros historicos permanecen.

## Contrato obligatorio para un nuevo conector

1. Declarar finalidad, datos minimos enviados, proveedor, permisos, consentimiento,
   organizacion/caso, condiciones de retencion y version de parser. Las credenciales
   de cada organizacion no se guardan en evidencia, URL ni logs. Este cambio no
   implementa un almacen de secretos/OAuth multiempresa.
2. Montar rutas con `enforce_scope`, ademas del permiso especifico; validar todos
   los IDs contra el mismo caso antes de red, archivos o procesos.
3. Utilizar `operia.security.outbound.fetch_bytes/fetch_json`. No incorporar
   requests/httpx/urlopen ni resoluciones DNS propias como rutas alternativas.
   No agregar callbacks o URLs de proveedor elegibles por el usuario.
4. Contrastar formato, limites, origen y hash; conservar respuesta original si es
   evidencia mediante un registro independiente. No modificar resultados previos.
5. Separar hechos observados, enriquecimiento externo y conclusiones profesionales.
   Un fallo de red no demuestra riesgo ni ausencia de compromiso.
6. Agregar pruebas negativas de permisos, referencias, SSRF, volumen, tiempos,
   aislamiento, idempotencia e integridad antes de exponer el conector.

La prueba de arquitectura detecta llamadas de red comunes fuera de los adaptadores
aprobados y shell=True. Es una barrera de regresion, no un analizador completo de
seguridad ni una forma de ejecutar codigo de plugins no confiables.

## Despliegue pendiente de validacion operacional

Antes de exponer evidencia real a Internet: TLS en gateway, cuotas compartidas por
cuenta/organizacion, configuracion estricta de proxies, firewall de egreso,
identidades/secretos administrados, aislamiento de worker, cifrado y permisos de
backups, observabilidad/alertas y auditoria de dependencias/CVE y pentest con alcance
autorizado. La auditoria CVE se documenta en SECURITY_AUDIT.md y el pentest local en
LOCAL_PENTEST.md; falta una evaluacion del despliegue productivo. No se
promete proteccion contra DDoS distribuido, administradores hostiles o compromiso
del equipo. Estos requisitos no deben confundirse con los controles ya presentes.

Referencias de diseno consultadas:
- [OWASP SSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)
- [OWASP REST Security](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html)

## Refuerzo auditado de conectores

Cada finalidad requiere una concesion explicita en Organization.settings_json, ademas
de la allowlist global. IA local requiere tambien concesion local_ai y permiso ai:use.
Los hijos no heredan secretos ni proxies; limites de 4 operaciones globales, 1 por
organizacion y 20/minuto por organizacion, con plazo HTTPS maximo de 12 segundos.
La inferencia de POST /api/ai/assist tiene un presupuesto separado de hasta 60 s;
no amplia el presupuesto HTTPS ni las capacidades de red de los validadores.
Windows aplica AppContainer y Job Object, con runtime RX sin secretos y perfiles
individuales. Siguen pendientes cuenta dedicada del supervisor, firewall de egreso
y validacion de produccion. Operacion y limites: [pentest local](LOCAL_PENTEST.md).

## Pasarela de IA local

Implementada el 2026-10-17: supervisor con broker de destino fijo y dos
validadores desechables sin red. Limites, contexto opt-in, modelos y riesgos del
servicio de inferencia en [guia operativa](LOCAL_AI_GATEWAY.md). Los controles del
worker nativo y el conector HTTPS no se flexibilizan.
