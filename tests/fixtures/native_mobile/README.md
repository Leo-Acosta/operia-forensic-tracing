# Corpus sintético original

Estos archivos se crearon para las pruebas de este cambio. No provienen de un
dispositivo, cliente, motor externo ni feed. No contienen muestras de spyware.
No instalar profile.plist: es texto de prueba del lector, no un perfil validado
para instalación. La política de distribución del proyecto la decide su titular.

Referencias de estructura (consultadas 2026-10-16): Apple Device Management
TopLevel/payloads y Python plistlib; Android Developers adb package manager y
logcat epoch. Los documentos y sus condiciones son ajenos a estos fixtures.

Oráculo manual:
- profile.plist: un payload, localizador /PayloadContent/0, identificador
  invalid.operia.synthetic, sin fecha de evento. Una alerta DEMO solo si se activa.
- packages.txt: dos paquetes, líneas 1 y 2; una alerta DEMO opcional.
- logcat-epoch.txt: tres eventos, líneas 2,3,4, UTC 2023-11-14T22:13:20.000000Z,
  22:13:20.123000Z y 22:13:21.999999Z. La línea de cabecera no es un evento.
- indicators.json: un dominio sintético con subdominios. Dos coincidencias en el
  log, ninguna infección demostrada. Sin consultas de red.
