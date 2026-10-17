# Calculadora de horas de continuidad

Acuerdo del usuario: 2026-10-17. Contador iniciado desde este pedido; las etapas
anteriores no tienen horas retrospectivas atribuidas.

| Concepto | Horas |
| --- | ---: |
| Estimación inicial inferior | 400 |
| Estimación inicial superior | 900 |
| Programación registrada desde el inicio del contador | 0 |
| Saldo estimado inferior: 400 − 0 | 400 |
| Saldo estimado superior: 900 − 0 | 900 |
| Próximo aviso | 60 |

La fuente de verdad es [work_hours.json](work_hours.json). Cada entrada debe indicar
horas, fecha, trabajo realizado y fuente del cómputo. Si no hay una medición fiable
o una cantidad informada por el usuario, no sumar horas por suposición. El tiempo
de IA no representa automáticamente horas de programación humana.

## Formato de los avisos

Al primer umbral:

```text
Programación acumulada: 60 h
400 − 60 = 340 h restantes
900 − 60 = 840 h restantes
Próximo aviso: 120 h acumuladas
```

Repetir al cruzar 120, 180, 240 y cada múltiplo posterior de 60. Registrar los
umbrales ya informados para evitar avisos duplicados. Son avisos al continuar el
trabajo con horas registradas, no una alarma de calendario ni un cronómetro en
segundo plano.

## Cuenta final

Al concluir realmente el proyecto, si el total registrado es `T`:

```text
Bloques completos = T // 60
Último bloque parcial = T % 60
Total = bloques completos × 60 + bloque parcial
Saldo inferior = máximo(400 − T, 0)
Saldo superior = máximo(900 − T, 0)
Exceso sobre el máximo, si corresponde = máximo(T − 900, 0)
```

Por ejemplo, 430 h equivalen a 7 × 60 + 10 h. Es un ejemplo de cálculo, no una
previsión de finalización. Dentro del rango inicial, 400 h equivalen a 6 bloques
y 40 h; 900 h equivalen a 15 bloques exactos. El remanente de la última ronda se
informa aunque no complete 60 horas.

La conclusión se determina por implementación, aceptación y pruebas del SaaS,
no por alcanzar 400 o 900 horas. Una vez verificada, mostrar el letrero acordado:
**Acabo de finalizar el programa.**
