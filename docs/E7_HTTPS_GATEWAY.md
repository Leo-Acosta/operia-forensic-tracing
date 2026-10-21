# E7 — HTTPS y exposición de red

Fecha: 2026-10-21. Implementación y aceptación local con datos sintéticos;
no constituye publicación productiva ni cierre de E7.

## Arquitectura

Cliente HTTPS → Caddy → API `127.0.0.1:8020` (o puerto del servicio).
Los pollers native/static no tienen servidor de red; los procesos AppContainer
mantienen sus restricciones existentes. El gateway no recibe claves JWT,
contraseñas, acceso a la base, evidencias ni control del servicio OPERIA.

Se utiliza Caddy oficial 2.11.7, fijado por SHA-256 del ZIP y del ejecutable.
La descarga es local, sin instalación global. La configuración generada incluye:

- TLS 1.2/1.3 con certificado suministrado; sin HTTP plano, HTTP/3 ni puerto admin.
- Bind IPv4 explícito, loopback por defecto. No se admite wildcard de escucha.
- SNI/Host estricto, HSTS sin preload ni includeSubDomains, sin banner Server.
- API hacia un único upstream numérico loopback; sin destino controlado por URL.
- Encabezados de forwarding eliminados y Uvicorn mantiene `proxy_headers=False`.
  Los límites por IP son por tanto agregados en el gateway; no se atribuyen IP
  individuales hasta implementar un canal de forwarding autenticado.
- Límite de cuerpo 8 MB y tiempos acotados de cabeceras/carga/respuesta.
- Sin access log que pueda almacenar queries, JWT o datos de expedientes.
- Frontend únicamente desde un `dist` compilado revisado; no se sirve el repo.
  Sin frontend provisionado, las rutas fuera de `/api` devuelven 503.
- Frontend de producción consulta `/api` por el mismo origen HTTPS.
- Configuración de Caddy sin autosave. Estado separado mediante XDG_DATA_HOME y
  XDG_CONFIG_HOME, sin heredar secretos/proxies del proceso operador.

## Preparación reproducible

Desde la raíz del repositorio, PowerShell 7:

```powershell
./scripts/get-caddy-validation.ps1 -Destination storage/temp/caddy-2.11.7-new
```

El ZIP queda en una ruta ignorada por Git. No se debe usar esa carpeta mutable
como instalación definitiva: publicar el ejecutable verificado en una carpeta
RX para la cuenta dedicada del gateway, modificable solo por el operador.

Provisionar certificado y clave en un directorio privado separado del código y
del almacenamiento de OPERIA. La clave y su directorio deben superar
`assert_private`; no se generan claves productivas ni se instala confianza raíz
como efecto de esta etapa. La cuenta gateway debe poder leer únicamente su clave,
su configuración y el frontend publicado; no debe tener acceso a datos OPERIA.

Ejemplo de generación (rutas de ejemplo, requieren archivos reales):

```powershell
.venv/Scripts/python.exe -m scripts.prepare_https_gateway --hostname operia.example.org --certificate C:/ProgramData/OPERIA-Gateway/tls/fullchain.pem --private-key C:/ProgramData/OPERIA-Gateway/tls/key.pem --output C:/ProgramData/OPERIA-Gateway/config/Caddyfile --caddy C:/ProgramData/OPERIA-Gateway/bin/caddy.exe --bind 127.0.0.1 --port 8443 --upstream-port 29876 --web-root C:/ProgramData/OPERIA-Web/dist
```

El generador crea un archivo nuevo, valida con Caddy y no arranca listeners.
No sobrescribe configuración existente. Revisar el bind: para publicación elegir
una IPv4 concreta del servidor y puerto 443. Mantener la API en loopback.
La CORS de la aplicación debe coincidir exactamente con el origen HTTPS público,
incluido el puerto si no es 443. No habilitar el servidor Vite en producción.

Arranque foreground bajo una cuenta dedicada sin Administradores/SYSTEM:

```powershell
.venv/Scripts/python.exe -m scripts.run_https_gateway --caddy C:/ProgramData/OPERIA-Gateway/bin/caddy.exe --config C:/ProgramData/OPERIA-Gateway/config/Caddyfile --state-dir C:/ProgramData/OPERIA-Gateway-State
```

El lanzador verifica hash, ACL privada, identidad y rutas; no gestiona credenciales
SCM. El directorio privado de estado debe existir y estar separado de config.
Para cambios/renovación, validar un nuevo archivo y realizar reinicio controlado;
no existe API admin de reload. Mantener certificado previo para rollback del
proxy; nunca restaurar una base histórica para revertir el gateway.

## Exposición y límites de aceptación

Los launchers locales y SCM ya fijan API a 127.0.0.1. Docker publica exclusivamente
`127.0.0.1:8020`; su listener 0.0.0.0 interno al contenedor no publica la API en LAN.
No se alteraron reglas globales del firewall ni se abrió un puerto externo.
El aislamiento loopback no impide que otros procesos locales del host lleguen a
la API; siguen siendo obligatorias autenticación y autorización por expediente.

`audit-service-network.ps1 -Root <raíz SCM>` inspecciona los PIDs de la generación
ready y rechaza listeners API fuera de loopback y listeners TCP/UDP de pollers.
Debe ejecutarse con acceso a CIM/NetTCP y con el servicio listo. Es lectura sola;
no arranca el servicio ni modifica la cuenta. No cubre todos los procesos del host
ni sustituye la prueba desde una segunda máquina.

Pendientes de producción: dominio/IP confirmados, certificado confiable y política
de renovación, cuenta independiente y servicio SCM del proxy, ACL desplegadas,
regla firewall limitada al puerto HTTPS y redes aprobadas, escaneo desde otro
host y repetición integral SCM con proxy en la release publicada. El servicio
OperiaSvc anterior no se actualizó ni se arrancó en esta validación; no atribuirle
las pruebas ejecutadas con la API sintética en el proceso de pruebas.

## Pruebas

`tests/test_https_gateway.py` usa Caddy real solo si OPERIA_TEST_CADDY apunta al
binario explícito; sin él, la integración se marca skipped, no aceptada.
Certificado autofirmado de un día, confianza solo en el cliente de prueba y base
sintética aislada. No se agrega una CA al almacén Windows. Verifica TLS, rechazo
de confianza ausente/protocolo viejo/HTTP/Host incorrecto, autenticación real,
forwarding sin bypass, rutas de configuración/datos inaccesibles y bind LAN.
La regresión de permisos/custodia sigue siendo necesaria: HTTPS no los reemplaza.

Referencias oficiales consultadas: https://caddyserver.com/docs/caddyfile/options,
https://caddyserver.com/docs/caddyfile/directives/reverse_proxy,
https://caddyserver.com/docs/caddyfile/directives/request_body.

## Resultado de aceptación local

6 pruebas de gateway (incluidas dos integraciones reales, con y sin SPA), 124 de regresión backend y 52 de frontend aprobadas; build de producción correcto. Sin fallos ni skips en la aceptación HTTPS explícita. Advertencias de deprecación de dependencias y de TLS antiguo esperado en la prueba negativa. Preservación: 116 archivos, 74 tablas, 9 triggers y clave intactos. [Acta resumida](audits/e7-https-gateway-20261021.json). La auditoría de listeners del servicio SCM y publicación permanente permanecen pendientes según el alcance descrito arriba.
