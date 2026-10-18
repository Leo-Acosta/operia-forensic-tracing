# E5: laboratorio premium e incorporación revisada

Entrega local del 2026-10-18. Continúa el [proveedor CPython AST](STATIC_PROVIDER_JOBS.md)
y la [base visual E4](FRONTEND_VISUAL_BASE.md). No agrega proveedores ni dependencias.

## Flujo implementado

La navegación **Laboratorio estático** muestra el expediente autorizado, las evidencias
preservadas, disponibilidad del runtime y trabajos persistentes. Permite encolar,
consultar, cancelar según estado, revisar profesionalmente y consultar eventos e
históricos. Encolar no inicia procesos: el operador sigue ejecutando el worker aislado
documentado en la etapa anterior. La muestra nunca se ejecuta ni se consulta por red.

La pantalla usa los componentes shadcn/ui existentes, Tailwind y estilos compartidos.
Incluye estados de carga, error y vacío, etiquetas asociadas, foco en resultados y
errores, advertencia de borradores sin guardar y reflujo a una columna. Los resultados
tardíos de otro expediente o sesión se descartan. Las observaciones se muestran como
texto; no se interpreta HTML ni se abren recursos extraídos.

Solo la última revisión **aceptada**, sobre el mismo SHA-256 del resultado, habilita
la selección explícita de observaciones. La incorporación crea, en una transacción:

- Un hallazgo de confianza baja, con estado «requiere corroboracion».
- Un informe borrador nuevo, sección y versión 1.0 con contenido preservado.
- Una instantánea inmutable de organización, expediente, evidencia, fuente,
  resultado, runtime, proveedor, revisión, fundamento, actores y observaciones elegidas.
- Un evento de custodia y el registro de auditoría correspondientes.

No constituye aprobación, firma, dictamen sobre conducta ni atribución. Aceptar una
observación estática no demuestra que el código haya sido ejecutado.

## Permisos e invariantes

Las rutas se subordinan al aislamiento vigente entre organizaciones y expedientes.
La incorporación requiere simultáneamente permisos de rol `evidence:write`,
`cases:write`, `reports:write` y capacidades del expediente `analysis`, `evidence`,
`reports`. Revisar requiere su capacidad independiente `review`. Un administrador
sin concesión de expediente tampoco obtiene acceso implícito.

`POST /api/static-lab/cases/{case}/jobs/{job}/projections` recibe `review_version`
y `observation_ids`. Rechaza revisión ausente, obsoleta o rechazada, resultado alterado,
IDs ajenos o duplicados y expedientes no autorizados. La selección ordenada se resume
con SHA-256; repetir la misma selección y revisión devuelve la misma incorporación.
El bloqueo de escritura SQLite serializa la decisión y hay cuota de 1000 por expediente.
`GET` en la misma ruta consulta las incorporaciones preservadas.

Los triggers bloquean UPDATE y DELETE de la instantánea. La unidad de trabajo rechaza
editar/eliminar los hallazgos, informes, secciones y versiones vinculados. Rectificar
requiere otra revisión e incorporación; las anteriores permanecen consultables.
Esto no ofrece resistencia frente a un administrador que controle la base o el host.

El registro de informes se actualiza al entrar desde el laboratorio. Su vista previa
estática utiliza el Markdown original como texto, sin reconstruirlo desde hechos actuales
del expediente. Markdown, HTML, DOCX y PDF usan el camino de exportación de contenido
preservado. El informe integral del expediente continúa siendo un documento separado.

## Preservación y migración

La migración `20261018_0010` es aditiva e idempotente; downgrade conserva la tabla.
Se ensayaron 0008, 0009 y 0010 sobre copia: se conservaron todas las filas de las
74 tablas anteriores y sus objetos de esquema; integridad SQLite `ok`, 19 triggers
en la copia migrada. Se restauraron y verificaron por hash 116 archivos persistentes.

Respaldo privado local: `storage/temp/e5-laboratory-ui-20261018`, con base, archivos,
manifiesto y restauración. No se publica porque incluye configuración y claves.
La base habitual no se migró ni se usó para los ensayos del laboratorio. El runtime
aislado permanece en su identidad validada; su archivo de recuperación sigue en el
respaldo documentado en [la entrega anterior](STATIC_PROVIDER_JOBS.md).

## Validación y límites

La [auditoría de esta entrega](audits/e5-laboratory-interface-20261018.json) registra
los resultados de regresión, ensayo de preservación y recorrido en navegador con
fuente benigna sintética y proveedor real. Las pruebas de API incluyen aislamiento,
revocación, revisión obligatoria, selección válida, idempotencia, exportación y
conservación del informe tras una revisión posterior. Las pruebas React/axe cubren
el módulo y estados autorizado, lector y sin concesión. JSDOM no mide contraste visual.

La regresión general produjo **288 aprobadas, 1 fallo, 1 omitida y 4 advertencias**.
El fallo detectó conversión de saltos de línea al exportar Markdown en Windows.
Se corrigió con escritura de bytes UTF-8 y se revalidó la suite afectada ampliada:
**2/2 aprobadas**, incluyendo rectificación posterior y bloqueo de edición.
No se suman suites superpuestas ni se presenta la corrida anterior como una segunda
regresión completa de la corrección. La omisión requiere habilitar Ollama real.
Frontend: **52/52 aprobadas**, TypeScript y build Vite correctos.

La validación de reflujo del navegador se documenta por su ancho CSS efectivo,
no como prueba de un teléfono físico. Sigue pendiente la [matriz de NVDA, VoiceOver,
TalkBack y dispositivos reales](ASSISTIVE_ACCESSIBILITY.md). APK, PE/ELF, otros
proveedores, despliegue productivo y cierre del SaaS permanecen pendientes.

El contador de programación conserva los registros existentes; no se atribuyen
horas humanas a tiempo de pruebas o ejecución de IA.
