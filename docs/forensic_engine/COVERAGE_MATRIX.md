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
| iOS | no verificado | conjunto Manifest.db/WAL/SHM / manifest-wal-set 1.0.0 | SQLite real con datos sintéticos, dos commits, corrupción, crecimiento y truncamiento; worker aislado real | Files del último commit más procedencia; sin BLOB ni archivos físicos |
| iOS/Android | no verificado | conjunto SQLite/WAL/SHM / sqlite-wal-set 1.0.0 | oráculo SQLite nativo, checksum WAL little/big, SHM de cabecera little/big, cola no comprometida y ambos workers | solo catálogo y procedencia; SHM auxiliar, sin tablas hash/locks; no hardware big-endian |
| iOS | no verificado | selección lógica / backup-logical-files 1.0.0 | cuatro archivos sintéticos, once artefactos/canarios, omisiones, directorio, XML/binario, texto, SQLite y dos workers con manifiesto principal/WAL | hasta 32 copias explícitas; escalares plist, líneas UTF-8 y catálogo; sin BLOB/UID, NSKeyedArchiver, filas SQLite, recorrido de directorios ni asociación física autenticada |
| iOS/Android | cualquier otra combinación | backup completo, WAL/SHM fuera del perfil, mensajes/historial SQLite, bugreport completo, CMS, cifrado o archivos comprimidos | ninguna | no soportado; no se declara analizado |

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

Motor 0.4.0: [conjuntos preservados WAL/SHM](E6_WAL_SHM.md), máximo 1024 frames,
SHM opcional de un bloque y paquete completo de hasta 5 MiB. El soporte acotado
no convierte los lectores de imagen principal anteriores en lectores de sidecars.

Motor 0.5.0: [selección lógica preservada](E6_IOS_LOGICAL_FILES.md), paquete total
de 5 MiB y hasta 256 KiB por archivo. La selección no acredita backup completo,
ausencia de archivos omitidos ni validación por versión de OS.

Motor 0.6.0: [JSON lógico estructurado](E6_IOS_LOGICAL_JSON.md), UTF-8 con raíz objeto/array, 64 KiB, 24 niveles, 1024 nodos y 128 valores/exclusiones; sin semántica de aplicaciones ni cronología inferida.
