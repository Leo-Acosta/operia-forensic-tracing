# Compatibilidad comprobable — actualizada 2026-10-18

| Plataforma | OS | Formato / lector | Prueba | Estado y límites |
|---|---|---|---|---|
| iOS | desconocido; declarado por operador | plist XML/binario de perfil / configuration-profile 1.0.0 | fixture XML original y variante binaria serializada; oráculo manual | validación sintética de estructura; no adquisición iOS real ni perfil instalado |
| Android | desconocido; declarado por operador | texto pm list packages y -f / package-inventory 1.0.0 | fixture original de 2 líneas, variantes inválidas y demo positiva/negativa | validación sintética; no cobertura de permisos ni ejecución |
| Android | desconocido; declarado por operador | texto epoch con PID/TID / logcat-epoch 1.0.0 | 3 eventos conocidos, exclusiones, fechas ambiguas, dominios positivos/negativos | validación sintética; reloj no contrastado y sin prueba de tráfico |
| iOS | sintético; 18.0 es solo texto del fixture | Info.plist XML UTF-8/binario / backup-info 1.0.0 | cinco registros y fecha UTC con oráculo manual; variantes inválidas; worker real aislado | metadatos declarados; sin backup/dispositivo real, prueba de instalación ni autenticación de la versión |
| iOS | no verificado | Manifest.plist XML UTF-8/binario / backup-manifest 1.0.0 | booleano estricto, XML/binario, tipos inválidos, canarios secretos excluidos; worker real aislado | declaración de cifrado; sin verificarlo criptográficamente, sin leer Manifest.db ni descifrar |
| iOS | no verificado | Manifest.db / backup-manifest-db 1.0.0 | imágenes originales sintéticas; campos/locadores manuales, canarios BLOB, cuotas y worker aislado real | solo declaraciones Files; sin archivos físicos, fechas ni BLOB |
| iOS/Android | no verificado | SQLite / sqlite-catalog 1.0.0 | imágenes originales sintéticas, esquemas hostiles y ambos workers de plataforma | solo catálogo de nombres/tipos de tablas e índices ordinarios; no registros |
| iOS/Android | cualquier otra combinación | backup completo, WAL/SHM, mensajes/historial SQLite, bugreport completo, CMS, cifrado o archivos comprimidos | ninguna | no soportado; no se declara analizado |

Núcleo probado en Python 3.12.14/Windows y SQLite 3.53.1 para los perfiles nuevos;
[límites detallados](E6_MANIFEST_SQLITE.md). Worker Windows local probado mediante
subprocesos propios; Linux/macOS y PostgreSQL no validados. No generalizar a todas
las versiones de OS. Las capacidades se consultan en /native/capabilities y no
dependen de descubrir ejecutables externos.

Cobertura de lectura ≠ cobertura de detección ≠ conclusión. Todos los exámenes
actuales son parciales respecto del dispositivo. Estado técnico completado con
limitaciones no oculta exclusiones ni errores de formato. Una lista vacía o un
archivo inválido no puede sostener ausencia de compromiso.

Ampliación exige muestras autorizadas, versión de OS, esquema observado, lector
versionado y resultados esperados documentados antes de habilitar el formato.

La ampliación E6 solo acredita estructura y recorrido con fixtures autorizados de
prueba. El acceso a muestras reales y la validación por versión de OS permanecen
pendientes; no se extiende esa evidencia sintética a dispositivos reales.
