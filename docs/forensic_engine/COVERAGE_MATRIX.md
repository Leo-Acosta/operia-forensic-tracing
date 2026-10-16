# Compatibilidad comprobable — 2026-10-16

| Plataforma | OS | Formato / lector | Prueba | Estado y límites |
|---|---|---|---|---|
| iOS | desconocido; declarado por operador | plist XML/binario de perfil / configuration-profile 1.0.0 | fixture XML original y variante binaria serializada; oráculo manual | validación sintética de estructura; no adquisición iOS real ni perfil instalado |
| Android | desconocido; declarado por operador | texto pm list packages y -f / package-inventory 1.0.0 | fixture original de 2 líneas, variantes inválidas y demo positiva/negativa | validación sintética; no cobertura de permisos ni ejecución |
| Android | desconocido; declarado por operador | texto epoch con PID/TID / logcat-epoch 1.0.0 | 3 eventos conocidos, exclusiones, fechas ambiguas, dominios positivos/negativos | validación sintética; reloj no contrastado y sin prueba de tráfico |
| iOS/Android | cualquier otra combinación | backup completo, Manifest.db, mensajes/historial SQLite, bugreport completo, CMS, cifrado o archivos comprimidos | ninguna | no soportado; no se declara analizado |

Núcleo probado en Python 3.12.14/Windows. Worker Windows local probado mediante
subprocesos propios; Linux/macOS y PostgreSQL no validados. No generalizar a todas
las versiones de OS. Las capacidades se consultan en /native/capabilities y no
dependen de descubrir ejecutables externos.

Cobertura de lectura ≠ cobertura de detección ≠ conclusión. Todos los exámenes
actuales son parciales respecto del dispositivo. Estado técnico completado con
limitaciones no oculta exclusiones ni errores de formato. Una lista vacía o un
archivo inválido no puede sostener ausencia de compromiso.

Ampliación exige muestras autorizadas, versión de OS, esquema observado, lector
versionado y resultados esperados documentados antes de habilitar el formato.
