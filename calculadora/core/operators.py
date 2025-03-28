# calculadora/core/operators.py

import math

operators = {
    '+': lambda a, b: a + b,
    '-': lambda a, b: a - b,
    '*': lambda a, b: a * b,
    '/': lambda a, b: a / b if b != 0 else float('inf'),
    '^': lambda a, b: a ** b,             # Potencia
    'sqrt': lambda a, _: math.sqrt(a)     # Raíz cuadrada (unario, segundo parámetro ignorado)
}
