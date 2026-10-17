# E4: evidencias, formularios e informes

Tramo implementado el 2026-10-17, sobre `83ac684`. Extiende la base shadcn/ui y
Tailwind a los recorridos de evidencia, operación y control documental. No cambia
el backend, los permisos E3, el esquema ni los históricos de la instalación real.

## Cambios entregados

- Inventario de evidencias con búsqueda, metadatos, estado registrado y SHA-256
  diferenciado de la comprobación de integridad. Carga compartida entre Evidencia
  y Flujo Operativo, con archivo obligatorio y estados de trabajo.
- Registro de informes con versión y estado reales, consulta de vista previa y
  descarga autorizada. Se conserva el checklist profesional, las contradicciones,
  los anexos, la rúbrica y el versionado existentes.
- Formularios operativos con etiquetas visibles asociadas por ID, campos
  obligatorios, ayuda descriptiva y grupos deshabilitados según permisos. Incluye
  alta de caso, participantes, evidencia, custodia, cuantificación y resumen.
- Edición de participantes/evidencia y rectificación de custodia en diálogos Radix
  con título, descripción, foco inicial, contención del foco, Escape, cancelación
  y retorno al botón que los abrió. Los errores se anuncian dentro del diálogo.
- El hash y el estado de integridad son de consulta en el editor de evidencia;
  verificar el archivo utiliza la API. Rectificar custodia agrega un evento:
  no se incorporan controles para editar ni eliminar eventos originales.
- Descargas con Bearer y `no-store`, rechazo de redirects y comprobación del
  contexto antes/después de recibir bytes. Las URLs no llevan tokens. Los enlaces
  del flujo usan el mismo mecanismo; desde Historial se abre el expediente y sus
  informes antes de exportar. Se eliminó una función de informes antigua sin uso.

Componentes: `components/evidence/evidence-workspace.tsx`,
`components/reports/report-register.tsx`, `components/forms/form-field.tsx`.
Estilos compartidos en `record-workspaces.css`, dentro de las capas de la base E4.
Los controles de cierre de Dialog y Sheet ahora se anuncian en español; su
adaptación queda registrada en la procedencia de los componentes vendorizados.

## Autorización y concurrencia

Los botones combinan permiso de rol y capacidad del expediente: evidencia para
carga/verificación, export para descargas, reports para redacción, review para
revisión y approve/export para sellado. Las denegaciones siguen siendo impuestas
por la API: deshabilitar un botón no sustituye la autorización del servidor.

Las operaciones de estos recorridos capturan sesión y generación del expediente
para descartar resultados tardíos. Al cambiar contexto se limpian los borradores
de evidencia y custodia. La navegación advierte sobre archivos/cargas pendientes
y cambios del resumen, además de los editores existentes. El cierre explícito del
diálogo cancela el borrador. Una operación ya enviada puede concluir en el servidor
para su expediente original; descartar su respuesta no revierte una escritura.

La validación detectó ráfagas de consultas que podían alcanzar el límite de ocho
solicitudes de la API. El cliente ahora admite cuatro solicitudes API simultáneas,
manteniendo el turno hasta terminar de leer el cuerpo y liberándolo en errores.
Una solicitud en cola de una sesión anterior se descarta antes de enviarse,
incluidas mutaciones. No se elevaron límites ni desactivaron protecciones del
servidor. El cambio entre módulos reutiliza el contexto cargado y evita recargas
que borraban una vista previa; la actualización explícita sigue disponible en Casos.

## Pruebas y preservación

| Comprobación | Resultado |
| --- | --- |
| Regresión backend en runtime auditado | 272 aprobadas, 1 omitida, 4 advertencias; 626,79 s |
| Frontend | 22 aprobadas, incluyendo sesiones, cola, descargas y accesibilidad |
| TypeScript y Vite | Correcto; 1706 módulos, bloque de aplicación 378,08 kB |
| npm audit | Cero vulnerabilidades notificadas |
| Datos reales | 74 tablas y esquema idénticos, 116 archivos intactos, 9 triggers |
| Restauración local | Base y archivos restaurados en destinos nuevos y verificados |

La omitida del backend exige activar Ollama expresamente. Las advertencias son
deprecaciones conocidas. Las pruebas frontend utilizan VM Modules experimental
de Node solo en el runner; axe-core y jsdom son dependencias de desarrollo fijadas.

Se ejecutó axe sobre el render real de inventario (consulta/carga), registro de
informes y campo de archivo, con reglas WCAG 2 A/AA y 2.1 A/AA: cero infracciones.
JSDOM no valida contraste visual: esa regla se excluye expresamente. También se
comprobaron nombres accesibles de todos los campos del Flujo Operativo y de los
recorridos intervenidos en el navegador, foco del editor y retorno al cancelar.
Se corrigió un aviso de permisos con contraste insuficiente y se agregó una prueba
de regresión de su relación de contraste AA (al menos 4,5:1). El foco pasa al
contenido principal al cambiar de módulo. La base conserva enlace
para saltar navegación, indicadores de foco, movimiento reducido y reflujo móvil.

El laboratorio usó otra base y otro storage con datos sintéticos en localhost.
Un administrador cargó un archivo, verificó su integridad y descargó bytes
idénticos al original. Guardó un resumen con una nueva versión: la versión previa
sigue intacta. La carga agregó un evento de custodia; los dos eventos previos y
sus entradas de ledger permanecen idénticos. El lector conserva consulta y no
puede cargar, verificar, editar, aprobar ni exportar. Se comprobó reflujo del
informe a 480 px CSS, sin desbordamiento horizontal de la página.

El respaldo previo permanece en `storage/temp/e4-evidence-reports-20261017`,
protegido por ACL local y excluido de Git. No es WORM ni recuperación externa
cifrada. No se sobrescribió ningún respaldo anterior. Evidencia resumida sin
datos privados: [auditoría del tramo](audits/e4-evidence-reports-20261017.json).

La captura gráfica del navegador devolvió errores durante esta ronda. Se validaron
DOM, nombres accesibles, foco, colores computados y geometría responsive; no se
entrega una captura anterior como prueba del nuevo diseño. Los servidores y
pestañas de laboratorio se cerraron al finalizar.

## Alcance de accesibilidad y continuidad

Quedan cerradas las correcciones funcionales comprobadas de los recorridos E4
intervenidos; esto no equivale a una certificación WCAG de todo OPERIA. Los módulos
heredados fuera de estos recorridos conservan su interfaz y necesitan su propia
revisión. Falta la certificación con lectores de pantalla reales (NVDA/JAWS),
dispositivos físicos y evaluación visual completa de contraste y zoom.

Repetir desde la raíz:

```powershell
npm --prefix apps/web test
npm --prefix apps/web run build
npm --prefix apps/web audit
storage/test_runs/audited-runtime/Scripts/python.exe -m pytest -q
```

Rollback visual mediante reversión de los commits y reinstalación del lockfile;
no restaurar la base para revertir CSS o componentes. Se mantiene el contador de
programación sin cargos estimados: no hubo una medición fiable de horas humanas.
