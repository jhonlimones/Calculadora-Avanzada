# Modificaciones en consultas.py para añadir nuevas consultas

import pandas as pd
from calculadora.db.models import obtener_operaciones
from calculadora.core.utils import format_numero

class Consultas:
    def __init__(self):
        pass

    def operaciones_por_usuario(self, usuario_id):
        """
        Muestra las operaciones registradas para un usuario (por ID).
        """
        data = obtener_operaciones(usuario_id=usuario_id)
        if not data:
            print(f"No hay operaciones registradas para el usuario con ID {usuario_id}.")
            return

        df = pd.DataFrame(data)

        # Sumar antes de formatear
        total = df['resultado'].sum()

        # Formatear columnas
        df['operando1'] = df['operando1'].apply(format_numero)
        df['operando2'] = df['operando2'].apply(format_numero)
        df['resultado'] = df['resultado'].apply(format_numero)

        print("Operaciones para el usuario con ID", usuario_id)
        print(df)

        print(f"\nImporte total de operaciones: {format_numero(total)}")

    def operaciones_por_operador(self, operador):
        """
        Muestra las operaciones que utilizan el 'operador' especificado.
        """
        data = obtener_operaciones(operador=operador)
        if not data:
            print(f"No hay operaciones registradas con el operador: {operador}")
            return

        df = pd.DataFrame(data)

        # Sumar antes de formatear
        total = df['resultado'].sum()

        # Formatear columnas
        df['operando1'] = df['operando1'].apply(format_numero)
        df['operando2'] = df['operando2'].apply(format_numero)
        df['resultado'] = df['resultado'].apply(format_numero)

        print(f"\nOperaciones con el operador '{operador}':")
        print(df)

        print(f"\nImporte total de operaciones: {format_numero(total)}")
        
    def operaciones_por_usuario_y_operador(self, usuario_id, operador):
        """
        Muestra las operaciones de un usuario específico con un operador específico.
        """
        # Obtenemos todas las operaciones del usuario
        data = obtener_operaciones(usuario_id=usuario_id)
        if not data:
            print(f"No hay operaciones registradas para el usuario con ID {usuario_id}.")
            return
            
        # Filtramos por operador
        operaciones_filtradas = [op for op in data if op['operador'] == operador]
        if not operaciones_filtradas:
            print(f"No hay operaciones del usuario con ID {usuario_id} usando el operador '{operador}'.")
            return
            
        df = pd.DataFrame(operaciones_filtradas)
        
        # Sumar antes de formatear
        total = df['resultado'].sum()
        
        # Formatear columnas
        df['operando1'] = df['operando1'].apply(format_numero)
        df['operando2'] = df['operando2'].apply(format_numero)
        df['resultado'] = df['resultado'].apply(format_numero)
        
        print(f"\nOperaciones del usuario ID {usuario_id} con el operador '{operador}':")
        print(df)
        
        print(f"\nImporte total de operaciones: {format_numero(total)}")