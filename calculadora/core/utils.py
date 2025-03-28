# calculadora/core/utils.py

import os

def limpiar_pantalla():
    """
    Limpia la consola para Windows o Linux/Mac.
    """
    os.system('cls' if os.name == 'nt' else 'clear')

def leer_flotante(mensaje):
    """
    Solicita un número flotante en la consola, manejando los errores de ingreso.
    Continúa solicitando hasta que el usuario ingrese un valor numérico válido.
    """
    while True:
        valor = input(mensaje)
        # Eliminar espacios en blanco al inicio y final
        valor = valor.strip()
        
        # Validar si es un número (entero o decimal)
        try:
            # Intentar convertir a flotante
            numero = float(valor)
            return numero
        except ValueError:
            print("Error: Debe ingresar un valor numérico. Intente nuevamente.")

def format_numero(num):
    """
    Devuelve un string que:
      - Muestra num sin '.0' si es entero.
      - Muestra num con decimales si no es entero.
    """
    valor = float(num)
    if valor.is_integer():
        return str(int(valor))  # Elimina la parte decimal .0
    else:
        return str(valor)
