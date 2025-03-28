# main.py

"""
Punto de entrada principal para la Calculadora Avanzada.
Este script inicializa la aplicación, crea las tablas necesarias,
crea un superusuario inicial si no existe, y muestra el menú de autenticación
antes de iniciar el menú principal.
"""
from calculadora.cli_app import run_app

if __name__ == "__main__":
    run_app()