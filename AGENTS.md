# Acuerdos de continuidad de OPERIA

## Contador de horas solicitado por el usuario

Leer y mantener `docs/WORK_HOURS.md` y `docs/work_hours.json` al continuar el proyecto.
El usuario pidió registrar este acuerdo como forma de trabajo el 2026-10-17.

- Presupuesto estimado de referencia: entre 400 y 900 horas de programación.
- Inicio del contador: este pedido, con cero horas registradas. No atribuir horas
  retrospectivas a las etapas anteriores sin datos o confirmación del usuario.
- Contabilizar solo horas respaldadas por registros de trabajo o informadas por
  el usuario. Identificar la fuente de cada entrada. No inventar horas, convertir
  tokens en horas ni equiparar tiempo de ejecución de IA con esfuerzo humano.
- Mantener las entradas anteriores del registro; agregar las nuevas y recalcular
  el acumulado y el siguiente umbral. Las correcciones deben quedar documentadas.
- Cada vez que el acumulado cruce un múltiplo de 60 horas, avisar al usuario en la
  respuesta de ese trabajo con formato de calculadora: acumulado y operaciones
  `400 − acumulado` y `900 − acumulado`, mostrando ambos saldos estimados. Si se
  cruzan varios umbrales, informar todos. Registrar el último umbral informado.
- Mostrar cero cuando el saldo inferior resulte negativo; aclarar que superar
  400 horas no equivale a terminar. Si se superan 900, mostrar el exceso y revisar
  la estimación. No confundir presupuesto consumido con avance funcional.
- Al terminar realmente el SaaS, presentar la cuenta final de horas registradas,
  cantidad de bloques completos de 60 y el bloque parcial restante, aunque tenga
  menos de 60 horas, junto con la comparación con el rango inicial.
- Solo cuando el proyecto esté efectivamente concluido y validado, mostrar
  exactamente este letrero: **Acabo de finalizar el programa.**
- El aviso depende del trabajo y de las horas registradas: no crear un recordatorio
  cada 60 horas de reloj ni prometer seguimiento autónomo mientras no se trabaja.

Este acuerdo no sustituye las condiciones de aceptación, seguridad, custodia,
aislamiento, preservación de históricos ni las pruebas de cada etapa.
