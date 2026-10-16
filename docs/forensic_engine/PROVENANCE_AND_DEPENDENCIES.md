# Procedencia y componentes

El propietario cambió el alcance de integración externa a implementación propia.
Existe exposición previa al ecosistema/código de MVT en el contexto del proyecto;
en esta conversación constan consultas a documentación/licencia y referencias a
código. No se realizó ni se afirma un clean-room formal. El alcance de exposición
de otros participantes no se auditó. No se certifica independencia jurídica,
titularidad exclusiva, ausencia de patentes ni libertad de operación.

Este núcleo se implementó a partir de requisitos del propietario, documentación
de formatos de plataformas y fixtures originales. No usa MVT, su implementación,
pruebas, reglas, indicadores, licencia, dependencias ni recursos. No se instaló,
ejecutó ni descargó ese motor en esta transición. Los archivos del piloto previo
son código propio de OPERIA y se conservan solo para consulta histórica; sus
reportes no se usan como verdad de referencia del motor nuevo.

Fuentes consultadas el 2026-10-16 (especificaciones/conceptos; no cuerpos copiados):
- Apple: https://developer.apple.com/documentation/devicemanagement/toplevel
- Apple: https://support.apple.com/guide/deployment/intro-to-device-management-payloads-depd73c1b83c/web
- Python 3.12 plistlib: https://docs.python.org/3.12/library/plistlib.html
- Android adb/pm: https://developer.android.com/tools/adb
- Android logcat/epoch: https://developer.android.com/tools/logcat?hl=en
- AOSP PackageManagerShellCommand (formato de salida; sin copiar implementación):
  https://android.googlesource.com/platform/frameworks/base/+/refs/heads/main/services/core/java/com/android/server/pm/PackageManagerShellCommand.java

El núcleo agrega **cero dependencias de terceros**: usa Python stdlib (incluidos
plistlib, Expat, ipaddress, urllib.parse, JSON y hashing). Python tiene sus propias
licencias/avisos, también para componentes incorporados. La aplicación y worker
reutilizan FastAPI/Pydantic/SQLAlchemy/React/Vite ya presentes, con obligaciones
independientes del código nuevo. No se cambió la licencia del repositorio ni se
insertó una cesión/copyright definitivo. El titular debe decidir distribución.

DEPENDENCIES.json inventaría las versiones y metadatos de licencia del entorno de
Python y package-lock del frontend. No es una auditoría legal ni un SBOM firmado;
metadatos ausentes se marcan desconocidos y deben revisarse antes de distribución.
Recrear el inventario al cambiar dependencias. No incorpora datos de casos ni secretos.

No se usan marcas/logos ajenos ni se sugiere respaldo, certificación o equivalencia.
No hay feeds por defecto. Cada conjunto aportado exige fuente y condiciones
declaradas; la evaluación independiente de esas condiciones sigue a cargo del operador.
