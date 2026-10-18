# Validación de tecnologías de asistencia — 2026-10-18

## Resultado y límites

Se completaron 47 pruebas frontend y la compilación TypeScript/Vite. Incluyen axe
sobre 18 módulos y 3 paneles, aislamiento de respuestas, capacidades del expediente,
descargas y formularios. La regresión backend del mismo tramo, sin cambios de
backend posteriores, tuvo 272 aprobadas y 1 omitida (Ollama optativo).

No se ejecutó un lector de pantalla real ni un dispositivo físico. No se encontró
NVDA en las ubicaciones habituales ni procesos NVDA/Narrator o ADB disponible.
El control nativo está deshabilitado en esta sesión. El árbol accesible y axe
no sustituyen escuchar NVDA, VoiceOver o TalkBack. No se declara certificación.

## Correcciones implementadas

- El anuncio persistente de carga está fuera del contenido `aria-busy`, para
  evitar que el estado ocupado difiera su anuncio; el texto visual no se duplica.
- El contenido principal tiene como nombre su encabezado, facilitando la
  identificación de la región al recibir foco.
- La tabla de expedientes tiene una región nombrada y alcanzable con teclado
  para desplazarla horizontalmente conservando la semántica de tabla y caption.
- Foco visible del contenido, soporte de colores forzados y botones de navegación
  de al menos 44 px de altura en tamaños móviles; botones de cabecera de 44 px de
  ancho y respeto del área segura inferior del menú.

## Comprobaciones en navegador

Sin API activa y sin sesión: Enter en «Saltar al contenido» enfoca `main-content`;
Enter en Cybercrime enfoca el mismo contenido con nombre Cybercrime. Las escrituras
permanecen deshabilitadas. El menú móvil abre mediante Enter, expone su título y
descripción y enfoca «Cerrar navegación»; Escape lo cierra. No se confirmó el
retorno del foco después de completar la animación de cierre en esta ejecución.

La solicitud de viewport 320×640 produjo un ancho CSS real de 640 en este entorno:
se registró ancho de página 609, sin desbordamiento. No se acredita una prueba a
320 px. El tramo previo registró 18 vistas con datos sintéticos a 480 px CSS.

## Aceptación pendiente en equipo real

| Entorno | Recorrido | Condición de aceptación |
| --- | --- | --- |
| Windows + NVDA + navegador | Login, casos, expediente, evidencia e informes | Región y encabezado anunciados; etiquetas, errores y estado de carga inteligibles sin duplicaciones |
| Android + TalkBack | Menú, selección de caso, formularios y diálogos | Orden por gestos coherente, sin foco detrás del diálogo, cierre devuelve foco al disparador |
| iPhone + VoiceOver | Mismo recorrido y orientación horizontal/vertical | Controles operables, texto ampliado sin pérdida de acciones y áreas seguras respetadas |
| Teclado y zoom | Tabla, diálogos, 200–400 % y ancho CSS real 320 | Desplazamiento accesible, foco visible, sin trampas ni recortes de acciones |
| Usuario lector y sin concesión | Intentar escribir, exportar y cambiar de expediente | Denegación según rol/capacidad; sin datos residuales ni ampliación de acceso |

Registrar versión de SO, lector y navegador, dispositivo, caso sintético,
resultado por paso y defecto reproducible. No usar expedientes reales para estas
pruebas. Estas filas están pendientes y no son resultados aprobados.

## Preservación

Se repitió la comparación y restauración del respaldo E4: 74 tablas sin diferencias,
esquema idéntico, 9 triggers, integridad `ok`, 116 archivos con hashes idénticos.
No se cambiaron backend, permisos persistentes, custodia, informes ni históricos.
El contador de horas no recibe estimaciones sin registro humano fiable.
