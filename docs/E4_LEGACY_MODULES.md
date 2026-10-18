# E4: módulos heredados y accesibilidad

Validación del 2026-10-18, sobre `ca83d7e`. Se migraron las superficies heredadas
al sistema visual existente con shadcn/ui y Tailwind: dashboard, historial,
biblioteca legal, Cybercrime, medios, blockchain, IoT, catálogo de herramientas,
asistentes, seguridad de IA, usuarios, configuración, exposición, memoria y
forense móvil. Geo Trace, Geo Proximity y exportaciones conservan sus pantallas
de estado existentes con la nueva presentación; esta entrega no agrega motores
ni ejecuta conectores externos.

## Cambios

- Superficie compartida `ModuleSurface`, tarjetas claras, jerarquía consistente,
  formularios adaptables y catálogo externo integrado al mismo lenguaje visual.
- 95 controles recibieron etiquetas visibles asociadas; 139 botones y 42 paneles
  se migraron a componentes compartidos. Se conservaron las acciones y los tipos
  de envío de los formularios.
- Correcciones de contraste, texto extenso, desbordamiento, estados anunciados y
  foco al cambiar de módulo, incluida la navegación móvil.
- Los formularios combinan permisos del rol y capacidades del expediente con
  denegación por defecto. Forense móvil distingue adquisición, análisis, revisión,
  publicación y exportación. El backend sigue siendo la autoridad de acceso.
- 37 operaciones heredadas descartan resultados de un expediente o sesión anterior.
  Las descargas de exposición y forense móvil usan autorización Bearer, no-store
  y rechazo de redirecciones, sin credenciales en enlaces.

## Aceptación ejecutada

| Comprobación | Resultado |
| --- | --- |
| Frontend | 45 pruebas aprobadas, 0 fallos |
| TypeScript y compilación Vite | Correctos |
| Regresión backend | 272 aprobadas, 1 omitida, 4 advertencias conocidas |
| Auditoría npm | 0 vulnerabilidades informadas |
| Axe sobre App real | 18 vistas, más 3 paneles compartidos |
| Navegador con datos sintéticos | 18 vistas en escritorio y 18 a 480 px CSS |
| Nombres, contraste de textos medidos y reflujo | Sin fallos detectados |
| Foco tras navegación | Contenido principal |
| Escritura de formulario migrado | Sesión documental sintética guardada |
| Usuario lector | Escrituras bloqueadas en Cybercrime, medios, IoT, memoria y móvil |

La prueba omitida requiere Ollama real y activación explícita. Las advertencias
corresponden a TestClient/httpx, ReportLab y el ciclo de vida de FastAPI. El tiempo
bruto de la regresión incluye una pausa de la sesión y no representa horas de
programación humana. El contador acordado no recibe horas estimadas.

Axe en JSDOM no evalúa contraste; se complementó con muestras de estilos calculados
en navegador y revisión visual. La revisión técnica de este tramo está completada;
no equivale a certificación WCAG ni reemplaza pruebas con NVDA/JAWS y dispositivos
físicos. Los controles deshabilitados se verificaron con `:disabled`, incluyendo
la deshabilitación heredada de `fieldset`.

## Preservación

No se modificaron backend, esquema ni migraciones. Se compararon todas las filas,
incluyendo duplicados, de 74 tablas y el esquema completo con el respaldo previo:
sin diferencias. Los 9 triggers permanecen y `integrity_check` devuelve `ok`.
Los 116 archivos persistentes conservaron inventario y SHA-256. Se restauraron la
base y los archivos a una carpeta independiente y se verificaron sus hashes.

El respaldo local está en `storage/temp/e4-legacy-modules-20261017`, con ACL
restringida; no se incluye en Git y no sustituye almacenamiento WORM externo ni
un plan de recuperación ante desastres. Los históricos, informes y respaldos
anteriores se mantienen. Las pruebas de interfaz usaron una base y almacenamiento
sintéticos independientes, sin activar IA, workers ni conectores.

Evidencia resumida y sanitizada: [auditoría E4](audits/e4-legacy-modules-20261018.json).
Los resultados detallados permanecen en `storage/test_runs`, fuera de Git.
