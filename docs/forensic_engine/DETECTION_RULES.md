# Semántica original de indicadores y reglas

Conjunto `operia.indicators/1`: schema, source, terms, version, limitations e items.
Cada ítem: id único, type, value y match. Entre 1 y 500 ítems/256 KiB. Se conservan
bytes exactos, hash y versión; no se actualizan en sitio ni se descargan fuentes.
La validación estructural no certifica calidad, actualidad o condiciones jurídicas
de una fuente declarada por el operador. STIX2 no está implementado.

| Tipo | Comparación |
|---|---|
| domain | IDNA, minúsculas y eliminación de punto final; exact o subdomains con frontera de etiqueta |
| ip | representación canónica IPv4/IPv6 de ipaddress; igualdad |
| sha256 | 64 hex, minúsculas; hash del archivo fuente, no hash inventado del registro |
| url | HTTP(S) sin credenciales; host/scheme normalizados, puerto por defecto omitido, path vacío=/; preserva mayúsculas de ruta, orden de query, fragmento y escapes |
| package, profile_identifier, path | igualdad sensible a mayúsculas; no resuelve rutas en el sistema |

Dominio/IP se comparan con el host de URLs **mencionadas** en logcat. No se buscan
subcadenas en cualquier campo. No hay descargas, resolución DNS, navegación ni
interpretación del texto como instrucciones. Regex, expresiones STIX, eval/exec,
Python embebido y comandos aportados por clientes se rechazan/no se ofrecen.

Dos reglas declarativas originales opcionales (desactivadas por defecto):
- operia.demo.package/1.0.0: package_inventory.package == invalid.operia.synthetic.
- operia.demo.profile/1.0.0: configuration_payload.profile_identifier == invalid.operia.synthetic.

Las definiciones completas (autoría/procedencia, requerimientos, igualdad,
fundamento, alternativas benignas y límites) están en detection.py y en cada
resultado que las utiliza. Son pruebas sintéticas, no firmas de amenazas reales.
Ambas tienen gravedad informativa; no generan conclusión de compromiso.
La API no admite plugins o nuevas reglas ejecutables. Un editor de reglas
declarativas versionadas es trabajo posterior.

Pruebas propias: positivos, negativos benignos, fronteras de dominios, IPv6,
URL sensible a ruta/query, duplicados y rechazo de expresiones no soportadas.
Los duplicados idénticos conservan referencias pero no multiplican alertas ni
eventos. No hay correlación causal o atribución automática.
Las coincidencias de SHA-256 del mismo archivo se agrupan en una alerta con sus
referencias, aunque ese archivo produzca muchos registros. Solo reglas DEMO nunca
habilitan una conclusión profesional de ausencia de indicios.
