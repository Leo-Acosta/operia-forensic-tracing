# Pasarela segura para IA local — 2026-10-17

Este documento conserva el registro de la primera entrega. La etapa posterior
con Ollama real, configuración local y datos sintéticos se documenta en
[Validación local de Ollama](OLLAMA_LOCAL_VALIDATION.md).

La consulta de IA usa una pasarela interna del supervisor. No abre un servidor
nuevo ni concede loopback a AppContainer. El supervisor ya es la frontera confiable
que autentica y lee el caso; su broker permite exclusivamente POST a
`http://127.0.0.1:11434/api/generate`. No acepta destinos, puertos, rutas, headers,
cookies, credenciales, herramientas o funciones elegidos por el usuario.

## Flujo y separación

1. La ruta verifica usuario, permiso `ai:use`, organización activa y caso disponible.
   El cuerpo debe identificar el mismo caso que el ámbito autorizado. Sin caso
   no se realiza generación; se conserva la degradación de las rutas antiguas.
2. Hacen falta ambos flags globales y una concesión explícita de la organización
   para ese modelo, además de la allowlist global de modelos. No se copian ni
   actualizan automáticamente las políticas existentes.
3. Un worker AppContainer sin capacidades de red prepara el protocolo limitado.
   El supervisor comprueba que coincide exactamente con la solicitud autorizada.
4. El broker abre una conexión numérica nueva al destino fijo. No usa DNS,
   redirecciones, proxies, pools de conexión ni estado conversacional.
5. Otro worker AppContainer nuevo analiza el JSON del proveedor y devuelve solo
   texto. Rechaza duplicados, no finitos, profundidad excesiva, respuestas parciales,
   errores y contenido inválido. El supervisor verifica nuevamente forma y tamaño.
6. Se agrega una AIInteraction de la organización/caso con revisión humana
   obligatoria. No se cambia evidencia, custodia, informes, revisiones, proyecciones
   ni interacciones anteriores. La respuesta es texto inerte; no ejecuta acciones.

El validador usa el mismo launcher Windows y Job que los demás workers: perfil
individual, runtime RX sin secretos, memoria/CPU/procesos acotados, cierre de Job
y comprobación del token antes de leer entrada. El analizador sigue sin red y el
conector HTTPS conserva su finalidad/host. La antigua vía `local_ai` del worker
de conectores continúa rechazada y su transporte directo fue retirado.

La pasarela no ejecuta un worker con permisos normales. Su conexión de loopback
es una función pequeña y confiable del supervisor; el parser de framing HTTP de
stdlib se ejecuta allí, mientras que la validación del JSON del proveedor se hace
fuera del proceso. La aplicación y sus administradores del host siguen siendo
fronteras de confianza. Ollama es un proveedor separado que debe operar de forma
confiable; no queda dentro del Job/AppContainer del validador.

## Datos mínimos, límites y auditoría

La pantalla de IA incorpora «Consultar IA local» para el caso seleccionado. El
resumen, las descripciones de evidencia y los hallazgos solo se incluyen al marcar
la opción correspondiente. No se adjuntan originales. Por defecto se envían la
consulta con sus instrucciones de revisión y el contexto legal registrado que
corresponde; las notas o textos pegados por el usuario son datos no confiables.
Al cambiar de caso o sesión se descartan borradores/respuestas pendientes de esa
pantalla. La autorización efectiva siempre pertenece al backend.

Límites: prompt del usuario 32 KiB; contexto legal 16 KiB y de caso 8 KiB
(máximo ocho extractos de evidencia/hallazgos, consultados con límites SQL);
prompt final 64 KiB; respuesta HTTP 256 KiB;
JSON y pipes acotados; una operación IA simultánea por proceso, sin cola interna.
Comparte las cuotas de conectores (una operación por organización, cuatro
globales y 20/minuto por organización). Un presupuesto común de hasta 10 s,
dentro del contexto de 12 s, cubre validación y red. Un watchdog hace shutdown
del socket al vencer, incluso con cabeceras/cuerpo enviados por goteo. Creación
y limpieza de recursos del SO pueden añadir tiempo; no se promete una cota de
latencia del kernel. No hay reintentos automáticos.

El request no incluye historial, `context`, chat, imágenes, URLs o herramientas.
Fija `stream=false`, `keep_alive=0`, temperatura 0, contexto 4096 y 512 tokens de
salida. El contexto/tokens y metadatos devueltos por el proveedor se descartan.
Esto limita reutilización lógica: no certifica borrado de RAM/GPU, ausencia de
cachés internas o determinismo del modelo. La desconexión tampoco acredita que
el servidor haya detenido inmediatamente su cómputo. Para varias instancias se
necesitan cuotas coordinadas y configuración del servicio de inferencia.

Los logs contienen únicamente actor, organización, caso, request ID y resultado,
sin prompts/respuestas. La interacción del expediente conserva esos textos como
registro autorizado. Un rechazo o timeout se registra como indisponibilidad, no
como conclusión forense o generación válida.

`GET /api/ai/health` es pasivo: informa `gateway_ready` según configuración y
runtime, `provider_probed=false`, `available=false` hasta una consulta explícita.
No hace inferencia encubierta ni asegura disponibilidad de Ollama. No se modifican
los históricos para añadirles etiquetas retrospectivas.

## Configuración del operador

Todo sigue deshabilitado por defecto. Primero preparar/repreparar el runtime:

```powershell
.\.venv\Scripts\python.exe scripts\prepare_worker_sandbox.py
```

En configuración del servidor OPERIA:

```dotenv
OPERIA_LOCAL_AI_ENABLED=true
OPERIA_LOCAL_AI_GATEWAY_ENABLED=true
OPERIA_LOCAL_AI_ALLOWED_MODELS=["mistral"]
```

En `Organization.settings_json`, por operador autorizado:

```json
{"connectors":{"local_ai":{"enabled":true,"models":["mistral"]}}}
```

Instalar y revisar previamente el modelo local elegido, sin habilitar descargas,
pulls, búsqueda web o modelos cloud desde la aplicación. En el servicio Ollama
usar `OLLAMA_HOST=127.0.0.1:11434` y `OLLAMA_NO_CLOUD=1`, reiniciar y verificar su
modo local. Restringir sus salidas con firewall y usar cuenta dedicada sin acceso
a expedientes. Su memoria/CPU/GPU, logs, telemetría y acceso directo desde otros
programas locales requieren controles propios del servicio/host. Los flags de
OPERIA no prueban ni cambian la configuración de un Ollama ya ejecutándose.
Los nombres cloud se rechazan, pero la allowlist de nombres no acredita por sí
sola el origen ni el contenido del modelo: debe revisarlo el operador.

No se habilitó un proveedor real durante esta entrega, no se instalaron modelos
y no se enviaron evidencias reales. No agregar excepciones globales de loopback.
Windows x64 CPython 3.12 sigue siendo el backend validado; sin runtime verificado
se rechaza la operación, sin ejecución alternativa fuera del sandbox.

## Repetición

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_local_ai_gateway.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

Las pruebas utilizan un proveedor HTTP sintético en puerto efímero y redirigen
únicamente mediante monkeypatch del test la conexión fija del broker. La aplicación
no expone esa configuración. Los workers de validación son AppContainers reales.
Se cubren controles de modelos/organizaciones/casos, datos mínimos, ausencia de
historial, fallo del sandbox, respuestas hostiles, volumen, goteo/deadline,
capacidad y manipulación del resultado de un validador comprometido.

Referencias oficiales:

- [Ollama generate: parámetros de generación](https://docs.ollama.com/api/generate)
- [Ollama FAQ: modo local, cloud y servicio](https://docs.ollama.com/faq)

## Validación final

**213 pruebas aprobadas**, cuatro advertencias de deprecación, 287,62 s, desde
el entorno Windows CPython 3.12 reconstruido con lock/hashes. Incluye 33 casos
nuevos de pasarela y toda la regresión anterior. Las advertencias corresponden
a TestClient/httpx, ReportLab/ast y dos usos de FastAPI on_event.

TypeScript/Vite 6.4.4 aprobado (1583 módulos). Sin nueva inspección visual del
navegador. pip check correcto; pip-audit y npm audit sin vulnerabilidades conocidas.
Bandit sobre operia, apps/api y scripts: cero altas/medias, 15 bajas revisadas,
sin reglas silenciadas. Las bajas son literales vacíos/bearer, imports de subprocess,
icacls fijo y el spawn deliberado de la sonda; el nuevo import de la pasarela solo
usa TimeoutExpired. Sin nuevas dependencias de aplicación.

Las 72 tablas preexistentes y todos sus valores coinciden con el respaldo anterior
y su restauración. integrity_check correcto y mismo SHA-256:
`b2aaad233d98b5f11e2b9546c1cefe5f575d214bf6943eeea86f30e155a16371`.
No se activaron proveedores reales ni se enviaron evidencias.

[Registro técnico sanitizado](audits/local-ai-gateway-20261017.json). Las políticas
actuales del operador no se modificaron y los flags siguen apagados por defecto.
