# Ollama local: validación con datos sintéticos — 2026-10-17

Esta etapa configura el Ollama instalado en Windows para escuchar exclusivamente
en `127.0.0.1:11434`, con nube deshabilitada. Conserva los modelos existentes y
agrega `qwen2.5:0.5b` desde el registro oficial para una prueba pequeña en CPU.
Su licencia publicada es Apache 2.0 y su tamaño publicado es 398 MB:
[ficha oficial](https://ollama.com/library/qwen2.5:0.5b).
La prueba acredita integración y controles de acceso; no evalúa precisión forense.
El modelo puede alcanzar el límite de 512 tokens sin seguir el formato pedido;
la pasarela entrega texto para revisión humana, sin convertirlo en un dictamen.
Los prompts mayores o modelos más pesados pueden seguir agotando los sesenta
segundos; la operación debe fallar cerrada en ese caso.

## Configuración reproducible

En PowerShell 7, con el usuario dueño de la instalación:

```powershell
.\scripts\configure_local_ollama.ps1 -Restart
```

El script conserva las otras propiedades de `.ollama/server.json` y establece
`disable_ollama_cloud=true`. Persiste para el usuario `OLLAMA_NO_CLOUD=1`,
`OLLAMA_HOST=127.0.0.1:11434`, `OLLAMA_NUM_PARALLEL=1` y
`OLLAMA_MAX_LOADED_MODELS=1`. El reinicio es explícito: solo detiene los procesos
que escuchan en ese puerto si corresponden al ejecutable esperado de Ollama.
Los logs quedan en `storage/temp`, fuera de Git. No descarga modelos ni abre
permisos de organizaciones. Sin `-Restart`, se requiere reiniciar el servicio.

Comprobar que el listener solo tiene dirección `127.0.0.1` y que el nuevo log
incluye `Ollama cloud disabled: true`, conforme a la
[configuración oficial de Ollama](https://docs.ollama.com/faq).
El modo sin nube no equivale a un firewall de salida: la descarga explícita de
modelos sigue siendo una operación del operador. Ollama se ejecuta con la cuenta
del usuario; esta etapa no crea una cuenta de servicio dedicada ni certifica
aislamiento de su memoria o bloqueo de otros programas del mismo host.

La aplicación mantiene apagados sus flags por defecto. Para una habilitación
posterior se requieren ambos flags, allowlist global y concesión de organización
documentados en [la pasarela](LOCAL_AI_GATEWAY.md), usando el nombre exacto del
modelo elegido. La prueba cambia esas concesiones únicamente en la base temporal.
No se modificó la configuración de los expedientes reales.

## Repetir la prueba real

Instalar previamente el modelo desde el registro oficial si no está disponible:

```powershell
ollama pull qwen2.5:0.5b
$env:OPERIA_TEST_REAL_OLLAMA='1'
$env:OPERIA_TEST_OLLAMA_MODEL='qwen2.5:0.5b'
$env:OPERIA_TEST_OLLAMA_REPORT='storage/test_runs/ollama-real-report.json'
.\.venv\Scripts\python.exe -m pytest tests/test_ollama_real.py -q -p no:cacheprovider
Remove-Item Env:OPERIA_TEST_REAL_OLLAMA
Remove-Item Env:OPERIA_TEST_OLLAMA_MODEL
Remove-Item Env:OPERIA_TEST_OLLAMA_REPORT
```

El test usa autenticación y API reales con tres casos sintéticos en dos
organizaciones y SQLite temporal. No sustituye el transporte, el proveedor ni los
validadores AppContainer. Observa las solicitudes del broker para comprobar que
cada contexto contiene únicamente su marcador de caso, sin historial, herramientas
ni contexto conversacional del proveedor. Comprueba rechazo entre organizaciones
y de la organización sin concesión, luego verifica consultas autorizadas de ambas.
La primera interacción y el caso conservan sus valores tras las siguientes
consultas. El informe guarda digest, tiempos y contadores, sin prompts ni respuestas.
Sin opt-in, esta prueba se omite y la regresión usa el proveedor sintético habitual.

## Corrección hallada con el proveedor real

El timeout de conexión de dos segundos se heredaba al leer la respuesta completa.
Ahora, tras conectar, el socket usa el tiempo restante del presupuesto común.
El watchdog sigue cortando cabeceras y cuerpos por goteo al vencer el deadline.
La prueba real también mostró que diez segundos no alcanzan para el prompt y
salida en esta CPU. La ruta POST `/api/ai/assist` recibe ahora un presupuesto de
sesenta segundos, con el mismo máximo absoluto en el broker. El plazo efectivo
siempre es el menor entre el ámbito autorizado y el timeout solicitado. Las otras
rutas conservan doce segundos y el transporte HTTPS conserva su máximo de doce,
incluso dentro de un ámbito más largo. La validación mantiene sus Job limits de
CPU, memoria y procesos. No hay cola nueva, reintentos ni concurrencia adicional.
Las pruebas cubren la demora de 2,2 segundos, el máximo de sesenta y la prohibición
de extender un ámbito más corto. No se ampliaron capacidades de red de los workers
ni se agregaron excepciones de loopback.

## Resultado verificado

Ollama **0.40.5**, modelo **qwen2.5:0.5b**, digest
`a8b0c51577010a279d933d14c2a8ab4b268079d44c5c8830c0a93900f1827c67`.
Tras el reinicio reproducible, las tres generaciones tardaron 24,25, 25,469 y
22,062 segundos en el transporte real; los tres registros se completaron con
revisión humana obligatoria. `/api/ps` confirmó el modelo descargado de memoria
tras la última respuesta, sin acreditar borrado físico de RAM.

Regresión final: **216 aprobadas**, una omitida por requerir opt-in del proveedor
real y cuatro advertencias de deprecación preexistentes, en 348,27 s. La prueba
real se ejecutó aparte: **una aprobada**, 84,31 s, con tres generaciones. Build
TypeScript/Vite 6.4.4 correcto, 1583 módulos; sin nueva inspección visual.
Bandit: cero hallazgos altos/medios, 15 bajos revisados, sin errores de análisis.
No se incorporaron dependencias de aplicación.

Respaldo previo y restauración en un destino nuevo: integrity_check correcto,
las 72 tablas y todos sus valores idénticos a la base real después de las pruebas.
SHA-256 de ambos archivos:
`b2aaad233d98b5f11e2b9546c1cefe5f575d214bf6943eeea86f30e155a16371`.
No se utilizaron evidencias reales ni se modificaron concesiones de organizaciones
reales. Los históricos y los registros de auditoría anteriores se conservaron.

[Registro técnico sanitizado](audits/ollama-real-validation-20261017.json).
