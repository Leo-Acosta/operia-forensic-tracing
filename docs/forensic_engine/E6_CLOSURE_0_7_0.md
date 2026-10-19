# Cierre acotado de E6 — OPERIA 0.7.0

Fecha de continuidad: 2026-10-18. Base Git `1ddf43d62b390c7eb52ca25e34bb63da2fe49a7a`.
**Cierre técnico del alcance 0.7.0**, con validación sintética y una demostración
adicional sobre un artefacto público externo. La validación con adquisiciones de
dispositivos sigue pendiente por falta de muestras, confirmada por el usuario.
No es un cierre del SaaS ni una declaración de preparación productiva.

## Alcance congelado y aceptación

Se mantienen los 13 lectores y 11 formatos existentes, sin agregar lectores,
dependencias, migraciones ni cambios de configuración de seguridad. La
[matriz final](COVERAGE_MATRIX.md) identifica cada lector, versión, formato,
límites, exclusiones y evidencia. El contenido anterior de esa matriz se preservó
íntegro en history/COVERAGE_MATRIX_before_E6_closure_0.7.0.md.
Se contrastaron sus 13 entradas contra el catálogo del código.

- Regresión backend completa: **475 aprobadas, 1 omitida, 0 fallos y 0 errores**,
  476 casos, 763.35 segundos. Cuatro advertencias de deprecación conocidas.
- Omisión: test_real_ollama_case_and_tenant_isolation requiere opt-in explícito
  del operador; no se habilitó para este cierre del motor móvil.
- Frontend: **52 aprobadas**, TypeScript/Vite correcto.
- Permisos por expediente/organización, revocación, custodia, revisión,
  integraciones, informes, exportaciones y controles Windows incluidos en la suite.
- Preservación posterior: **74 tablas y todos sus valores, esquema, 9 triggers
  y 116 archivos persistentes intactos**, integrity_check correcto y respaldo/
  restauración con SHA-256 idéntico. Sin reescritura de históricos.
- Runtime 1717d297499151af78ec5640: **694 archivos** verificados en runtime
  preparado, archivo privado y copia restaurada; anteriores retenidos.

## Investigación del timeout HTTP

Incidente previo: ReadTimeout del cliente local de 5 segundos al crear un caso
sintético en test_local_http_auth_idor_mass_assignment_and_injection. Se revisaron
el fixture de Uvicorn/HTTPX, la ruta de casos, la sesión SQLite, el middleware de
entrada y la preparación/autenticación del segundo tenant.

Se conservaron timeout, aserciones, permisos, límites y aislamiento originales.
Cinco repeticiones confirmadas pasaron: duración total del caso con fixtures de
4.211, 4.424, 3.827, 4.005 y 4.455 segundos. No son tiempos por petición ni un SLA.
La misma prueba pasó dentro de la regresión completa: 2.255 segundos incluyendo
fixture. El timeout no se reprodujo. **Causa raíz no determinada**; no se atribuye
sin evidencia a SQLite, al lector, a carga o al sistema operativo, ni se declara
corregido mediante un cambio inexistente. Se conserva como observación para E7.

El volcado de diagnóstico de 4 segundos abarca el test y sus fixtures; se observó
preparación/autenticación PBKDF2 y bucles esperando I/O. Ese volcado no equivale
al ReadTimeout de una petición de 5 segundos. Un intento inicial de cinco
repeticiones solo dejó dos XML aprobados y terminó durante diagnóstico; no se usó
como confirmación completa. La serie confirmada guardó logs y cinco XML completos.

No se agregaron reintentos que oculten el fallo ni se ampliaron timeouts para
forzar la aceptación. Si reaparece, preservar request ID y trazas de fase/SQL sin
secretos antes de modificar el producto.

## Muestras disponibles y demostración externa

Inventario de la base habitual, en modo de solo lectura: cero adquisiciones
móviles nativas y cero dispositivos registrados. El corpus tests/fixtures/native_mobile
está declarado sintético. El usuario confirmó que no hay muestras reales de
adquisiciones disponibles y pidió crear una carpeta de demostración con un
artefacto de un repositorio.

Se creó **Muestras para Validacion** junto a new_unified_app y se descargaron
únicamente el perfil público Quad9 y su licencia desde paulmillr/encrypted-dns,
revisión **af713462bfc9b2f2ac26734e64cdb72571c7b782**. Licencia Unlicense preservada.
Original de 1805 bytes, SHA-256:
`16d21588869c2dea74a78033f50c57ed25c7745b726237b816f14eb9bb77fb59`.
Fuente fijada:
[quad9-default-https.mobileconfig](https://github.com/paulmillr/encrypted-dns/blob/af713462bfc9b2f2ac26734e64cdb72571c7b782/profiles/quad9-default-https.mobileconfig).

**Es un artefacto público real de configuración, no malware ni una adquisición de
un dispositivo.** No se instaló el perfil, ejecutó muestra, cambió DNS o consultó
el resolvedor. La descripción del archivo afirma bloqueo de malware; no se probó
esa afirmación ni se interpretó como una detección de OPERIA.

Resultado: un payload com.apple.dnsSettings.managed en /PayloadContent/0, tipo e
identificador contrastados contra XML; CLI y resultado íntegro de worker iguales.
Sin indicadores/reglas activos, cero alertas y cero eventos temporales. Los campos
DNSSettings se revisaron manualmente y permanecen fuera de interpretación del
lector de perfiles; no se añadieron capacidades implícitas al cierre de E6.

La demostración definitiva usa una base y usuarios desechables, con adquisición
nueva que registra autorización, repositorio, commit, licencia y restricciones
explícitos. Worker AppContainer/Job real, evidencia íntegra, evento de custodia,
revisión e informe/exportación preservados tras otra revisión; concesión solo
lectura, revocación y organización ajena comprobadas. La base habitual no se usó.

Los ensayos previos se conservaron como preliminares: primero se comparó la
proyección API con counts frente a la salida de CLI; el contraste definitivo
usa el resultado íntegro del worker. Se sustituyó el contexto genérico de fixtures
por una adquisición nueva con procedencia externa explícita. Un texto de fecha
demasiado largo se rechazó y se ajustó al límite de la API. No se editaron
adquisiciones ni snapshots anteriores para corregir esos ensayos.

En la carpeta solicitada se incluyen original, licencia, procedencia/hashes,
resultado CLI, script de reproducción para desarrollo, guía y resultados de la
ejecución definitiva **demostracion_aislada/verificada-b0070c9c**. El script requiere
el entorno de desarrollo y genera una carpeta nueva por ejecución. No es una
herramienta operativa de producción. Se archivó/restauró el conjunto final en el
respaldo privado de cierre, verificando hashes.

## Recuperación y pendientes explícitos

Respaldo nuevo: storage/temp/e6-closure-20261018, ACL privada, base/archivos
persistentes, runtime y copias recuperadas en destinos nuevos. El nombre interno
pre-e5.db es heredado del helper; corresponde al estado previo a este cierre,
no a una migración E5. No se borraron respaldos ni auditorías previas.

**Pendiente por falta de muestras:** adquisiciones iOS/Android autorizadas con
OS/método, hashes, referencia de autorización y oráculo manual, para validar cada
perfil contra datos de un dispositivo. La demostración pública solo amplía la
evidencia del lector de perfiles; no cambia el estado de los otros doce lectores.

**Evolución posterior:** otros esquemas/aplicaciones, bugreport Android,
WAL/SHM específico de Safari, época de fechas y asociación física. No bloquean
este alcance acotado por haberse declarado fuera de la entrega 0.7.0.

**Fuera de este cierre:** validación física de accesibilidad E4 y requisitos de
operación E7 —cuenta mínima, egreso, secretos/MFA/HTTPS, monitorización,
recuperación RPO/RTO, PostgreSQL/multiinstancia y despliegue validados—, seguidos
de E8. No se declara terminado el SaaS. El contador de horas humanas sigue en
cero por ausencia de nuevos registros; no se cargan horas de IA o pruebas.

[Auditoría de cierre](../audits/e6-closure-20261018.json). Los resultados y auditorías
anteriores permanecen como históricos.
