# E4: base visual premium

Implementación local del 2026-10-17, sobre `711181d`. Cubre navegación, listado de
casos y estructura del expediente. Los demás módulos conservan sus flujos y se
migrarán gradualmente. No representa la conclusión de todo E4 ni del SaaS.

## Diseño y estructura

- Shell con barra lateral azul profundo, acento dorado, contexto del expediente,
  cuenta y menú móvil con Sheet. Inicio en Casos, conservando todos los módulos.
- Listado con búsqueda por código, título o tipo (sin distinguir tildes), filtros
  de estado, orden, tabla y tarjetas. Contadores calculados sobre casos recibidos.
- Expediente con cabecera, selector, estado, fechas y contadores reales; pestañas
  Radix, panel de permisos existente y acciones sujetas a capacidades.
- Estados diferenciados de carga, error, falta de sesión y resultado vacío.
  Protección de borradores al navegar: continuar editando o descartar.
- Tokens compartidos, tipografía del sistema, foco visible, enlace al contenido,
  soporte de movimiento reducido y tablas con desplazamiento local en móvil.

`src/design-system.css` organiza las capas Tailwind y el CSS anterior para evitar
que los estilos globales antiguos sobrescriban componentes. `styles.css` permanece
intacto. Componentes en `src/components/{layout,cases,ui}`, utilidades en `src/lib`.
El bundle separa React y Radix del código de aplicación.

## Dependencias y procedencia

Tailwind y su plugin Vite `4.3.3`, Radix `1.8.1`, CVA `0.7.1`, clsx `2.1.1` y
tailwind-merge `3.7.0`, fijados en package.json/lockfile. Ocho componentes shadcn/ui
new-york-v4 vendorizados: Button, Badge, Card, Input, Tabs, Sheet, Skeleton y Dialog.
`apps/web/shadcn-provenance.json` registra fuentes y SHA-256 del registro original;
`SHADCN-LICENSE.md` conserva la licencia MIT. Imports adaptados a los alias locales.
No se incorporan fuentes remotas, imágenes externas ni servicios de telemetría.

Referencias oficiales: [shadcn con Vite](https://ui.shadcn.com/docs/installation/vite),
[Tailwind con Vite](https://tailwindcss.com/docs/installation/using-vite) y
[shadcn/Tailwind v4](https://ui.shadcn.com/docs/tailwind-v4).

## Permisos y preservación

La autorización continúa en el backend E3. La interfaz consulta
`/cases/{id}/access/me` y combina capacidades del expediente con permisos del rol;
ocultar o deshabilitar un control no sustituye esa autorización. El contexto de
capacidades exige coincidencia de caso y sesión. Las respuestas tardías se
descartan al cambiar de sesión o expediente y se limpian colecciones y borradores.
Sin sesión no se muestran casos ni contadores anteriores.

Participantes, evidencias, rectificaciones y exportación del expediente respetan
sus capacidades. Auditoría requiere su permiso de rol. El PDF del expediente se
descarga con Bearer, sin caché, y comprueba nuevamente el contexto antes de ofrecer
el archivo. No se agregaron edición ni eliminación de eventos de custodia.

No hay cambios de backend ni migraciones. Se compararon todas las filas de las
74 tablas y el esquema con el respaldo previo: idénticos, incluidos los nueve
triggers de custodia y acceso. Los 116 archivos persistentes y su inventario
conservan sus SHA-256. Se restauraron base y archivos en destinos nuevos y se
verificó integridad. Los respaldos locales quedan en
`storage/temp/e4-visual-base-20261017`, con ACL restringida; contienen datos privados,
están ignorados por Git y no son un respaldo externo cifrado ni almacenamiento WORM.

## Aceptación ejecutada

| Verificación | Resultado |
| --- | --- |
| Backend completo, runtime auditado | 272 aprobadas, 1 omitida, 4 advertencias; 521,86 s |
| Frontend, código real TS/TSX y render estático | 11 aprobadas |
| TypeScript + Vite | Correcto, 1702 módulos; bloque principal 360,72 kB |
| npm audit final | 0 vulnerabilidades notificadas |
| Restauración y preservación | 74 tablas, 116 archivos, 9 triggers intactos |

La omitida requiere activar expresamente Ollama. Las advertencias del backend son
deprecaciones conocidas; el runner frontend usa VM Modules experimental de Node
solo para pruebas. Los tests incluyen respuestas de sesión tardías, búsqueda,
filtros sin mutación, fechas inválidas, lectura, ausencia de sesión y estados UI.

En navegador local se usó una base y storage independientes, exclusivamente con
datos sintéticos: administrador, lector con un expediente y analista sin
concesiones. Se comprobaron búsqueda, filtro cerrado, tabla/tarjetas, contadores,
cambio de sesión, acciones de lectura, pestañas por teclado, menú móvil con Escape
y retorno de foco, y conservación/descarte de borrador sin enviar rectificaciones.
Anchos CSS comprobados: 480, 780, 1170 y 2560 px; la emulación del navegador ajustó las
dimensiones solicitadas. Se guardaron capturas de escritorio y móvil sintéticas. Esto no certifica
WCAG, dispositivos físicos ni todos los formularios heredados.

Evidencia resumida sin datos privados:
[auditoría E4](audits/e4-visual-base-20261017.json). Los resultados brutos y fixtures
quedan en `storage/test_runs`, ignorados por Git. No se cargan horas estimadas al
contador: sigue en cero a falta de una medición de programación verificable.

## Repetición y continuidad

Desde la raíz del repositorio:

```powershell
npm --prefix apps/web test
npm --prefix apps/web run build
storage/test_runs/audited-runtime/Scripts/python.exe -m pytest -q
npm --prefix apps/web audit
```

Para desarrollo, usar la API local configurada y `npm --prefix apps/web run dev`.
Para una demostración, usar un entorno sintético con base, storage y clave propios;
no reutilizar credenciales ni expedientes reales para capturas. Los servidores de
validación E4 se cierran al terminar y no son servicios instalados.

Rollback del aspecto: revertir el commit frontend y reinstalar desde su lockfile;
no restaurar la base para deshacer un cambio visual. No sobrescribir una base con
registros posteriores. Conservar respaldos e informes anteriores.

Próximo tramo E4: extender los componentes al alta de evidencias, formularios,
hallazgos e informes; completar revisión de accesibilidad y pruebas de recorridos
largos con roles distintos. También quedan vistas heredadas y enlaces de exportación
fuera del expediente por migrar. Las limitaciones de revocación ya recibida, WORM,
operación multiusuario y preparación SaaS mantienen las condiciones anteriores.
