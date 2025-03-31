# calculadora/cli_app.py

import time
import datetime
import schedule
import threading
import os  # Para variables de entorno

from calculadora.core.export_utils import export_to_csv, export_to_excel, export_to_binary
from calculadora.core.serialization_utils import backup_user_data
from calculadora.core.utils import limpiar_pantalla, leer_flotante, format_numero
from calculadora.services.user_service import (
    validar_contrasena,
    crear_usuario_si_no_existe,
    autenticar_usuario,
    verificar_password,
    hashear_password  # Añadido
)
from calculadora.services.operation_service import realizar_operacion
from calculadora.core.export_utils import export_to_csv, export_to_excel
from calculadora.db.models import (
    crear_tablas,
    obtener_todas_las_operaciones_unidas,
    obtener_usuario_por_nombre,
    obtener_operaciones,
    obtener_todos_usuarios,
    get_connection,
    insertar_usuario,
    guardar_en_historial,    # Añadido
    obtener_historial,       # Añadido
    limpiar_historial_antiguo # Añadido
)
from calculadora.consultas import Consultas
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Cargar variables de entorno
load_dotenv()

# === HISTORIAL EN MEMORIA (se limpia cada 24h) ===
# Estructura: {user_id: [(timestamp, descripcion_operacion), ...], ...}
historial_memoria = {}

# Variables globales para usuario actual
current_user_id = None
is_superuser = False

def registrar_en_historial(user_id, descripcion):
    """
    Registra la operación en memoria (para la sesión actual) y
    en la base de datos (para persistencia).
    """
    ahora = datetime.datetime.now()
    
    # Almacenar en memoria para la sesión actual
    if user_id not in historial_memoria:
        historial_memoria[user_id] = []
    historial_memoria[user_id].append((ahora, descripcion))
    
    # Guardar en la base de datos para persistencia
    guardar_en_historial(user_id, ahora, descripcion)

def mostrar_historial_en_memoria(user_id, mostrar_todos=False):
    """
    Muestra las operaciones de las últimas 24h para el usuario seleccionado.
    Carga los datos desde la base de datos.
    """
    if mostrar_todos and is_superuser:
        # Obtener historial de todos los usuarios desde la BD
        historial_db = obtener_historial(usuario_id=None)
        
        if not historial_db:
            print("No hay operaciones en las últimas 24 horas para ningún usuario.")
            return
        
        print("=== Historial de Todos los Usuarios - Últimas 24h ===")
        
        # Agrupar por usuario para mejor visualización
        usuarios = {}
        for registro in historial_db:
            uid = registro['usuario_id']
            if uid not in usuarios:
                usuarios[uid] = {
                    'nombre': registro['usuario_nombre'],
                    'operaciones': []
                }
            usuarios[uid]['operaciones'].append((
                registro['fecha_hora'],
                registro['descripcion']
            ))
        
        # Mostrar historial agrupado por usuario
        for uid, datos in usuarios.items():
            print(f"\nOperaciones de {datos['nombre']}:")
            for fecha, desc in datos['operaciones']:
                print(f"{fecha.strftime('%Y-%m-%d %H:%M:%S')} -> {desc}")
    else:
        # Obtener historial de un usuario específico
        historial_db = obtener_historial(usuario_id=user_id)
        
        if not historial_db:
            print("No hay operaciones en las últimas 24 horas.")
            return
        
        print("=== Historial Últimas 24h ===")
        for registro in historial_db:
            fecha = registro['fecha_hora']
            desc = registro['descripcion']
            print(f"{fecha.strftime('%Y-%m-%d %H:%M:%S')} -> {desc}")

def limpiar_historial_memoria_completo():
    """
    Limpia el historial en memoria (para la sesión actual) y
    elimina registros antiguos en la base de datos.
    Se ejecuta cada 24 horas con 'schedule'.
    """
    global historial_memoria
    
    # Limpiar memoria
    historial_memoria = {}
    
    # Limpiar registros antiguos en la BD
    eliminados = limpiar_historial_antiguo()
    
    print(f"Historial en memoria limpiado. {eliminados} registros antiguos eliminados de la base de datos.")

def menu_autenticacion():
    """
    Muestra un menú para registrarse o iniciar sesión. 
    Retorna una tupla (user_id, es_superusuario) si la autenticación/registro es exitoso.
    """
    while True:
        limpiar_pantalla()
        print("=== Menú de Autenticación ===")
        print("1. Registrarse")
        print("2. Iniciar Sesión")
        print("3. Salir")
        opcion = input("Seleccione una opción: ")

        if opcion == '1':
            nombre = input("Ingrese nombre de usuario: ")
            while True:
                password = input("Ingrese contraseña (min. 8, 1 mayúscula, 1 caracter especial): ")
                if validar_contrasena(password):
                    break
                else:
                    print("Contraseña no cumple los requisitos. Intente de nuevo.")
            user_id, es_super = crear_usuario_si_no_existe(nombre, password)
            return user_id, es_super

        elif opcion == '2':
            nombre = input("Ingrese nombre de usuario: ")
            password = input("Ingrese contraseña: ")
            user_id, es_super = autenticar_usuario(nombre, password)
            if user_id is not None:
                print("Autenticación exitosa.")
                time.sleep(1)  # Pequeña pausa
                return user_id, es_super
            else:
                print("Usuario/contraseña inválidos.")
                input("Presione Enter para reintentar...")
        
        elif opcion == '3':
            print("Saliendo de la aplicación...")
            exit(0)
        else:
            print("Opción inválida.")
            input("Presione Enter para continuar...")

def mostrar_todos_usuarios():
    """
    Muestra una lista de todos los usuarios registrados (solo para superusuario).
    """
    if not is_superuser:
        print("Esta función es solo para superusuarios.")
        return
    
    usuarios = obtener_todos_usuarios()
    if not usuarios:
        print("No hay usuarios registrados en el sistema.")
        return
    
    print("=== Usuarios Registrados ===")
    print(f"{'ID':<5} {'Nombre':<20} {'Superusuario':<15} {'Fecha de Creación':<20}")
    print("-" * 60)
    
    for usuario in usuarios:
        es_super = "Sí" if usuario['es_superusuario'] else "No"
        fecha = usuario['creado_en'].strftime('%Y-%m-%d %H:%M:%S') if usuario['creado_en'] else "N/A"
        print(f"{usuario['id']:<5} {usuario['nombre']:<20} {es_super:<15} {fecha:<20}")

def opcion_nueva_operacion():
    """
    Solicita datos de la operación, la ejecuta y la registra tanto en la DB como en memoria.
    Solo utiliza el usuario autenticado actualmente.
    """
    limpiar_pantalla()
    if current_user_id is None:
        print("No hay usuario autenticado. Regrese al menú principal.")
        input("Presione Enter para continuar...")
        return

    # Usamos directamente el usuario actual (ya autenticado)
    usuario_id = current_user_id

    print("\nOperadores disponibles: +, -, *, /, ^, sqrt")
    
    # Validación de operador: solo aceptar operadores válidos
    operadores_validos = ['+', '-', '*', '/', '^', 'sqrt']
    while True:
        operador = input("Operador: ").strip()
        if operador in operadores_validos:
            break
        else:
            print(f"Error: Operador inválido. Use uno de estos: {', '.join(operadores_validos)}")

    if operador == 'sqrt':
        op1 = leer_flotante("Ingrese el operando (base de la raíz): ")
        op2 = 0
    else:
        op1 = leer_flotante("Ingrese el primer operando: ")
        op2 = leer_flotante("Ingrese el segundo operando: ")

    try:
        resultado = realizar_operacion(usuario_id, op1, operador, op2)
        # Formateamos el resultado
        print(f"\nResultado: {format_numero(resultado)}")

        # Guardamos en MEMORIA y BD para historial
        descripcion_op = f"{op1} {operador} {op2} = {resultado}"
        registrar_en_historial(usuario_id, descripcion_op)

        # Preguntamos si desea continuar
        while True:
            continuar = input("\n¿Desea realizar otra operación? (s/n): ").lower()
            if continuar == 's':
                return opcion_nueva_operacion()  # Llamada recursiva para continuar
            elif continuar == 'n':
                return  # Volvemos al menú principal
            else:
                print("Por favor, ingrese 's' para continuar o 'n' para salir.")

    except ZeroDivisionError as zde:
        print(f"\nError: {zde}")
    except ValueError as ve:
        print(f"\nError: {ve}")

    input("\nPresione Enter para continuar...")

def opcion_consultas():
    """
    Despliega un menú de consultas (DB) adaptado según el tipo de usuario.
    """
    consultas = Consultas()

    while True:
        limpiar_pantalla()
        print("=== Menú de Consultas ===")
        
        if is_superuser:
            # Menú para superusuario
            print("1. Operaciones por Usuario (ID o Nombre)")
            print("2. Ver Todos los Usuarios Registrados")
            print("3. Operaciones por Operador")
            print("4. Mostrar Mis Operaciones")
            print("5. Volver al Menú Principal")
        else:
            # Menú para usuario normal
            print("1. Mis Operaciones")
            print("2. Mis Operaciones por Operador")
            print("3. Volver al Menú Principal")

        opcion = input("Seleccione una opción: ")
        
        # Lógica para superusuario
        if is_superuser:
            if opcion == '1':
                entrada = input("Ingrese el ID o Nombre del usuario: ").strip()
                try:
                    user_id = int(entrada)
                    limpiar_pantalla()
                    consultas.operaciones_por_usuario(user_id)
                except ValueError:
                    usuario = obtener_usuario_por_nombre(entrada)
                    if usuario:
                        user_id = usuario[0]
                        limpiar_pantalla()
                        consultas.operaciones_por_usuario(user_id)
                    else:
                        print(f"No existe un usuario con el nombre '{entrada}'.")
                input("\nPresione Enter para continuar...")
            
            elif opcion == '2':
                limpiar_pantalla()
                mostrar_todos_usuarios()
                input("\nPresione Enter para continuar...")
            
            elif opcion == '3':
                limpiar_pantalla()
                print("Operadores disponibles: +, -, *, /, ^, sqrt")
                op_seleccionado = input("Seleccione un operador: ").strip()
                consultas.operaciones_por_operador(op_seleccionado)
                input("\nPresione Enter para continuar...")
            
            elif opcion == '4':
                limpiar_pantalla()
                consultas.operaciones_por_usuario(current_user_id)
                input("\nPresione Enter para continuar...")
                
            elif opcion == '5':
                break
            else:
                print("Opción no válida.")
                input("Presione Enter para continuar...")
        
        # Lógica para usuario normal
        else:
            if opcion == '1':
                limpiar_pantalla()
                consultas.operaciones_por_usuario(current_user_id)
                input("\nPresione Enter para continuar...")
            
            elif opcion == '2':
                limpiar_pantalla()
                print("Operadores disponibles: +, -, *, /, ^, sqrt")
                op_seleccionado = input("Seleccione un operador: ").strip()
                consultas.operaciones_por_usuario_y_operador(current_user_id, op_seleccionado)
                input("\nPresione Enter para continuar...")
                
            elif opcion == '3':
                break
            else:
                print("Opción no válida.")
                input("Presione Enter para continuar...")

def opcion_ver_historial():
    """
    Muestra las operaciones de historial según el tipo de usuario.
    """
    limpiar_pantalla()
    
    if is_superuser:
        print("=== Historial ===")
        print("1. Ver mi historial")
        print("2. Ver historial de todos los usuarios")
        opcion = input("Seleccione una opción: ")
        
        if opcion == '1':
            limpiar_pantalla()
            mostrar_historial_en_memoria(current_user_id)
        elif opcion == '2':
            limpiar_pantalla()
            mostrar_historial_en_memoria(current_user_id, mostrar_todos=True)
        else:
            print("Opción no válida.")
    else:
        # Usuario normal solo ve su propio historial
        mostrar_historial_en_memoria(current_user_id)
    
    input("\nPresione Enter para continuar...")

def opcion_exportar():
    """
    Permite exportar las operaciones a CSV, Excel o formato pickle (PKL) según el tipo de usuario.
    """
    limpiar_pantalla()
    
    if is_superuser:
        print("=== Exportar Operaciones ===")
        print("1. Exportar mis operaciones")
        print("2. Exportar todas las operaciones")
        opcion = input("Seleccione una opción: ")
        
        if opcion == '1':
            data = obtener_operaciones(usuario_id=current_user_id)
        elif opcion == '2':
            data = obtener_todas_las_operaciones_unidas()
        else:
            print("Opción no válida.")
            input("\nPresione Enter para continuar...")
            return
    else:
        # Usuario normal solo exporta sus propias operaciones
        data = obtener_operaciones(usuario_id=current_user_id)
    
    if not data:
        print("No hay operaciones registradas para exportar.")
        input("\nPresione Enter para continuar...")
        return

    print("¿En qué formato desea exportar?")
    print("1. CSV")
    print("2. Excel")
    print("3. Pickle (formato binario para respaldo)")
    eleccion = input("Seleccione una opción: ")
    
    if eleccion == '1':
        nombre_archivo = input("Ingrese nombre del archivo (o Enter para 'operaciones.csv'): ") or "operaciones.csv"
        if not nombre_archivo.endswith('.csv'):
            nombre_archivo += '.csv'
        export_to_csv(data, nombre_archivo)
    elif eleccion == '2':
        nombre_archivo = input("Ingrese nombre del archivo (o Enter para 'operaciones.xlsx'): ") or "operaciones.xlsx"
        if not nombre_archivo.endswith('.xlsx'):
            nombre_archivo += '.xlsx'
        export_to_excel(data, nombre_archivo)
    elif eleccion == '3':
        nombre_archivo = input("Ingrese nombre del archivo (o Enter para 'operaciones.pkl'): ") or "operaciones.pkl"
        if not nombre_archivo.endswith('.pkl'):
            nombre_archivo += '.pkl'
        export_to_binary(data, nombre_archivo)
    else:
        print("Opción no válida.")

    input("\nPresione Enter para continuar...")

def opcion_crear_usuario():
    """
    Permite al superusuario crear nuevos usuarios o superusuarios.
    Requiere verificación de contraseña.
    """
    limpiar_pantalla()
    if not is_superuser:
        print("Esta función es exclusiva para superusuarios.")
        input("\nPresione Enter para continuar...")
        return
    
    # Verificación de contraseña
    print("=== Verificación de Seguridad ===")
    print("Por favor, confirme su contraseña para continuar.")
    password = input("Contraseña: ")
    
    # Obtener información del usuario actual
    usuario_actual = obtener_usuario_por_nombre_y_id(current_user_id)
    if usuario_actual and verificar_password(password, usuario_actual[2]):  # Verifica con hash
        limpiar_pantalla()
        print("=== Crear Usuario ===")
        print("1. Crear Usuario Normal")
        print("2. Crear Superusuario")
        print("3. Volver al Menú Principal")
        
        opcion = input("Seleccione una opción: ")
        
        if opcion in ['1', '2']:
            es_super = (opcion == '2')
            nombre = input("Ingrese nombre para el nuevo usuario: ")
            
            # Verificar si el usuario ya existe
            usuario_existente = obtener_usuario_por_nombre(nombre)
            if usuario_existente:
                print(f"El usuario '{nombre}' ya existe.")
                input("\nPresione Enter para continuar...")
                return
            
            while True:
                password = input("Ingrese contraseña (min. 8, 1 mayúscula, 1 caracter especial): ")
                if validar_contrasena(password):
                    break
                else:
                    print("Contraseña no cumple los requisitos. Intente de nuevo.")
            
            # Crear el usuario
            user_id = insertar_usuario(nombre, hashear_password(password), es_super)
            tipo = "superusuario" if es_super else "usuario"
            print(f"El {tipo} '{nombre}' ha sido creado exitosamente.")
            
        elif opcion != '3':
            print("Opción no válida.")
        
        input("\nPresione Enter para continuar...")
    else:
        print("Contraseña incorrecta. Operación cancelada.")
        input("\nPresione Enter para continuar...")

def obtener_usuario_por_nombre_y_id(user_id):
    """
    Obtiene información de un usuario por su ID.
    """
    conn = get_connection()
    usuario = None
    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, nombre, password, es_superusuario FROM usuarios WHERE id = %s;", (user_id,))
            usuario = cur.fetchone()
    conn.close()
    return usuario

def opcion_chatbot_sql():
    """
    Permite a los superusuarios hacer consultas en lenguaje natural sobre la base de datos.
    Solo accesible para superusuarios y requiere verificación de contraseña.
    """
    # Verificar que el usuario sea superusuario
    if not is_superuser:
        limpiar_pantalla()
        print("Esta función es exclusiva para superusuarios.")
        input("\nPresione Enter para continuar...")
        return
        
    limpiar_pantalla()
    
    # Verificación de contraseña
    print("=== Verificación de Seguridad ===")
    print("Por favor, confirme su contraseña para acceder al Chatbot SQL.")
    password = input("Contraseña: ")
    
    # Obtener información del usuario actual
    usuario_actual = obtener_usuario_por_nombre_y_id(current_user_id)
    if not usuario_actual or not verificar_password(password, usuario_actual[2]):  # Verifica con hash
        print("Contraseña incorrecta. Acceso denegado.")
        input("\nPresione Enter para continuar...")
        return
        
    try:
        from calculadora.sql_chatbot import SQLChatbot
        import os
    except ImportError:
        print("Error: No se pudo cargar el módulo SQLChatbot.")
        print("Asegúrese de que el archivo sql_chatbot.py esté instalado correctamente.")
        input("\nPresione Enter para continuar...")
        return
    
    # Verificar si existe la variable de entorno para OpenAI en .env
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        print("Error: No se encontró la clave API de Groq.")
        print("Asegúrese de configurar GROQ_API_KEY en su archivo .env")
        input("\nPresione Enter para continuar...")
        return
    
    limpiar_pantalla()
    print("=== Chatbot SQL (Acceso Superusuario) ===")
    print("Haz preguntas sobre tus operaciones y usuarios en lenguaje natural.")
    print("Ejemplos:")
    print("- ¿Cuántas operaciones ha realizado el usuario admin?")
    print("- ¿Cuál es el promedio de los resultados de sumas?")
    print("- Muéstrame las últimas 5 operaciones de todos los usuarios")
    print("- ¿Quién ha usado más la raíz cuadrada?")
    print("- Exportar las operaciones del usuario admin")
    print("- Muéstrame las contraseñas de todos los usuarios")
    
    print("\nConfiguraciones adicionales:")
    print("- !nivel [basico/medio/avanzado]: Cambia el nivel técnico de las respuestas")
    print("- !feedback [corrección]: Proporciona retroalimentación sobre la última respuesta")
    print("- !cache: Limpia el caché de consultas")
    print("- !sql [consulta]: Muestra el SQL generado para una consulta sin ejecutarla")
    print("- !salir: Volver al menú principal")
    
    # Inicializar chatbot con conexión a BD
    conn = get_connection()
    chatbot = SQLChatbot(conn)
    
    # Establecer nivel técnico avanzado para superusuario
    chatbot.set_tech_level("avanzado")
    
    while True:
        query = input("\n> ")
        
        # Comandos especiales
        if query.startswith("!"):
            if query.lower() == "!salir":
                break
            elif query.lower().startswith("!nivel"):
                parts = query.split()
                if len(parts) > 1 and parts[1] in ["basico", "medio", "avanzado"]:
                    response = chatbot.set_tech_level(parts[1])
                    print(response)
                else:
                    print("Uso: !nivel [basico/medio/avanzado]")
            elif query.lower() == "!cache":
                response = chatbot.clear_cache()
                print(response)
            elif query.lower().startswith("!sql"):
                # Mostrar SQL generado sin ejecutar
                natural_query = query[4:].strip()
                if natural_query:
                    try:
                        sql = chatbot.get_sql_for_query(natural_query)
                        print("\nSQL generado:")
                        print(sql)
                    except Exception as e:
                        print(f"Error al generar SQL: {e}")
                else:
                    print("Uso: !sql [consulta en lenguaje natural]")
            elif query.lower().startswith("!feedback"):
                # Obtener el resto del texto como corrección
                correction = query[9:].strip() if len(query) > 9 else None
                if correction:
                    response = chatbot.get_feedback(False, correction)
                    print("\n" + response)
                else:
                    print("¿Fue correcta la respuesta anterior? (s/n)")
                    feedback = input().lower()
                    if feedback in ["s", "si", "sí"]:
                        response = chatbot.get_feedback(True)
                    else:
                        print("Por favor, proporciona una corrección:")
                        correction = input()
                        response = chatbot.get_feedback(False, correction)
                    print("\n" + response)
            else:
                print("Comando no reconocido.")
        else:
            # Verificar si es una solicitud de exportación
            if any(word in query.lower() for word in ["exportar", "guardar", "descargar", "extraer"]):
                try:
                    print("\nProcesando solicitud de exportación...")
                    # Primero procesamos la consulta para obtener los datos
                    sql_query = chatbot.get_sql_for_query(query)
                    results = chatbot._execute_query(sql_query)
                    
                    if results["success"] and results["data"]:
                        print("\nSe han encontrado datos para exportar.")
                        print("¿En qué formato desea exportar?")
                        print("1. CSV")
                        print("2. Excel")
                        eleccion = input("Seleccione una opción: ")
                        
                        if eleccion == '1':
                            filename = input("Ingrese nombre del archivo (o Enter para 'exportacion.csv'): ") or "exportacion.csv"
                            if not filename.endswith('.csv'):
                                filename += '.csv'
                            export_to_csv(results["data"], filename)
                        elif eleccion == '2':
                            filename = input("Ingrese nombre del archivo (o Enter para 'exportacion.xlsx'): ") or "exportacion.xlsx"
                            if not filename.endswith('.xlsx'):
                                filename += '.xlsx'
                            export_to_excel(results["data"], filename)
                        else:
                            print("Opción no válida. Exportación cancelada.")
                    else:
                        if not results["success"]:
                            print(f"Error en la consulta: {results['error']}")
                        else:
                            print("No se encontraron datos para exportar.")
                except Exception as e:
                    print(f"\nError al procesar la exportación: {str(e)}")
            # Consulta para ver contraseñas (hasheadas)
            elif any(word in query.lower() for word in ["contraseña", "password", "clave"]):
                try:
                    print("\nProcesando consulta sobre contraseñas...")
                    # Generamos SQL específico para obtener información de usuarios
                    sql_query = "SELECT id, nombre, password FROM usuarios"
                    results = chatbot._execute_query(sql_query)
                    
                    if results["success"] and results["data"]:
                        print("\nInformación de contraseñas (Solo visible para superusuarios):")
                        print(f"{'ID':<5} {'Usuario':<20} {'Contraseña (Hash)':<40}")
                        print("-" * 65)
                        
                        for user in results["data"]:
                            hash_password = user['password']
                            print(f"{user['id']:<5} {user['nombre']:<20} {hash_password:<40}")
                    else:
                        if not results["success"]:
                            print(f"Error en la consulta: {results['error']}")
                        else:
                            print("No se encontraron usuarios.")
                except Exception as e:
                    print(f"\nError al procesar la consulta de contraseñas: {str(e)}")
            # Consulta normal
            else:
                try:
                    print("\nProcesando consulta...")
                    response = chatbot.process_query(query)
                    print("\n" + response)
                    
                    # Solicitar feedback automáticamente (opcional)
                    feedback = input("\n¿Fue útil esta respuesta? (s/n): ").lower()
                    if feedback not in ["s", "si", "sí"]:
                        print("¿Cómo podría mejorar? (Presiona Enter para omitir)")
                        correction = input()
                        if correction:
                            improved = chatbot.get_feedback(False, correction)
                            print("\nRespuesta mejorada:\n" + improved)
                except Exception as e:
                    print(f"\nError al procesar la consulta: {str(e)}")
                    print("Por favor, intente reformular su consulta.")
    
    conn.close()
    input("\nPresione Enter para continuar...")

def opcion_backup():
    """
    Permite al superusuario crear copias de seguridad de los datos.
    """
    limpiar_pantalla()
    if not is_superuser:
        print("Esta función es exclusiva para superusuarios.")
        input("\nPresione Enter para continuar...")
        return
    
    print("=== Backup de Datos ===")
    print("1. Backup de mi historial")
    print("2. Backup de todos los usuarios")
    print("3. Volver al Menú Principal")
    
    opcion = input("Seleccione una opción: ")
    
    if opcion == '1':
        # Obtener datos del usuario actual
        operaciones = obtener_operaciones(usuario_id=current_user_id)
        historial = obtener_historial(usuario_id=current_user_id)
        
        datos = {
            "operaciones": operaciones,
            "historial": historial,
            "fecha_backup": datetime.datetime.now()
        }
        
        filename = backup_user_data(current_user_id, datos)
        if filename:
            print(f"Backup creado exitosamente: {filename}")
        else:
            print("Error al crear el backup.")
            
    elif opcion == '2':
        # Obtener datos de todos los usuarios
        operaciones = obtener_todas_las_operaciones_unidas()
        usuarios = obtener_todos_usuarios()
        historial = obtener_historial()
        
        datos = {
            "operaciones": operaciones,
            "usuarios": usuarios,
            "historial": historial,
            "fecha_backup": datetime.datetime.now()
        }
        
        filename = backup_user_data("all", datos, "backups_admin")
        if filename:
            print(f"Backup global creado exitosamente: {filename}")
        else:
            print("Error al crear el backup global.")
    elif opcion == '3':
        return  # Volver al menú principal
    else:
        print("Opción no válida.")
    
    input("\nPresione Enter para continuar...")

def main_menu():
    """
    Punto de entrada para manejar el menú principal.
    Se llama tras la autenticación.
    """
    global current_user_id, is_superuser

    while True:
        limpiar_pantalla()
        print("=== Menú Principal ===")
        print("1. Realizar Nueva Operación")
        print("2. Consultas")
        print("3. Ver mi Historial de las últimas 24h")
        print("4. Exportar Operaciones")
        
        # Opciones solo para superusuarios
        if is_superuser:
            print("5. Crear Usuario")
            print("6. Chatbot SQL")  # Disponible solo para superusuario
            print("7. Backup de Datos")  # Nueva opción
            print("8. Salir o Cambiar Sesión")  # Corregido de 7 a 8
        else:
            # Usuarios normales no ven la opción de chatbot
            print("5. Salir o Cambiar Sesión")

        opcion = input("Seleccione una opción: ")
        
        if opcion == '1':
            opcion_nueva_operacion()
        elif opcion == '2':
            opcion_consultas()
        elif opcion == '3':
            opcion_ver_historial()
        elif opcion == '4':
            opcion_exportar()
        elif opcion == '5' and is_superuser:
            opcion_crear_usuario()
        elif opcion == '6' and is_superuser:
            opcion_chatbot_sql()
        elif opcion == '7' and is_superuser:  # Opción para Backup de Datos
            opcion_backup()
        elif (opcion == '8' and is_superuser) or (opcion == '5' and not is_superuser):  # Corregido de 7 a 8
            print("\n1. Salir de la aplicación")
            print("2. Cambiar de sesión")
            sub_opcion = input("Seleccione una opción: ")
            
            if sub_opcion == '1':
                print("Saliendo de la aplicación. ¡Hasta pronto!")
                break
            elif sub_opcion == '2':
                print("Cambiando de sesión...")
                # Reseteamos las variables de sesión
                current_user_id = None
                is_superuser = False
                # Volvemos al menú de autenticación
                current_user_id, is_superuser = menu_autenticacion()
            else:
                print("Opción no válida.")
                input("Presione Enter para continuar...")
        else:
            print("Opción no válida, intente de nuevo.")
            input("Presione Enter para continuar...")

def run_app():
    """
    Punto de entrada principal de la aplicación.
    """
    global current_user_id, is_superuser
    
    crear_tablas()
    
    # Programar limpieza del historial en memoria cada 24 horas
    schedule.every(24).hours.do(limpiar_historial_memoria_completo)

    # 1) Autenticación
    current_user_id, is_superuser = menu_autenticacion()

    # 2) Iniciamos bucle de la app (main_menu), corriendo schedule en un hilo simple
    def schedule_loop():
        while True:
            schedule.run_pending()
            time.sleep(60)  # Cada 60s revisamos si toca limpiar

    t = threading.Thread(target=schedule_loop, daemon=True)
    t.start()

    # 3) Llamamos al main_menu principal, donde se usa el current_user_id
    main_menu()

if __name__ == "__main__":
    run_app()