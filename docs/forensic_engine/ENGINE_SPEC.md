# Especificación ejecutable del MVP

Versión de núcleo 0.2.0; salida `operia.forensic/1`. No es equivalente a otra
herramienta ni detector certificado de una familia de malware.

Cada lector declara identificador, versión, plataforma, formato y dependencias.
El registro verifica IDs/salidas duplicados, dependencias faltantes y ciclos antes
del análisis. El formato se selecciona expresamente; contenido incompatible se
conserva y produce cobertura no_compatible/corrupto, nunca un resultado limpio.
Estados por fuente implementados: analizado, sin_registros, no_compatible, corrupto.
No se inventan estados cifrado/sin_permiso/no_presente sin una fuente que permita
comprobarlos: contenedores cifrados, CMS y fuentes ausentes requieren lectores futuros.

Jobs: pendiente → preparando → ejecutando → completado_con_limitaciones, fallido,
cancelado o interrumpido. Completado está reservado para perfiles futuros. La
versión actual siempre conserva la limitación de una sola fuente y validación
sintética. El estado técnico no sustituye cobertura ni conclusión profesional.
Cancelación pendiente es inmediata; en ejecución se solicita y el worker mata el
árbol del subproceso. Timeout no publica resultado completado. Fallos y reinicios
conservan eventos; retry vuelve a pendiente sin borrar el historial. Nunca reintenta
un resultado completado ni modifica snapshots publicados.

Idempotencia: única adquisición por dispositivo/hash/formato y único trabajo por
adquisición/hash de configuración. La configuración incluye núcleo, Python,
formato, hash original, hash del conjunto exacto de indicadores y uso de DEMO.
Los IDs, horas de ejecución y ámbito van en el envoltorio del examen, fuera de la
salida determinista del núcleo. Repetir mismo input/configuración da mismos bytes
canónicos. No se afirma reproducibilidad entre versiones distintas de Python.

Código cero sin JSON válido, origen correcto y hash de entrada esperado no basta.
Integridad se verifica al encolar, en worker y antes de revisar/exportar. Una
coincidencia siempre es pendiente de corroboración. Detección distingue falta de
datos, falta de indicadores/reglas activas, coincidencias y sin coincidencias en
reglas aplicadas. Ninguna de ellas concluye infección automáticamente.
