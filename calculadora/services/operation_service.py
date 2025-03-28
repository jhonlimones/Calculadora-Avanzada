# calculadora/services/operation_service.py

from calculadora.core.operators import operators
from calculadora.db.models import insertar_operacion

def realizar_operacion(usuario_id, operando1, operador, operando2):
    """
    Realiza la operación definida por 'operador' con operando1 y operando2.
    Guarda el resultado en la DB y retorna el resultado.
    """
    if operador not in operators:
        raise ValueError("Operador inválido.")

    # Manejo de división entre cero
    if operador == '/' and operando2 == 0:
        raise ZeroDivisionError("División por cero no permitida.")

    # Para sqrt, se ignora operando2 en la lambda, pero lo enviamos igual
    resultado = operators[operador](operando1, operando2)

    # Guardamos la operación en la DB
    insertar_operacion(usuario_id, operando1, operador, operando2, resultado)

    return resultado
