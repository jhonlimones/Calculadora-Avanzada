# calculadora/services/user_service.py

import re
import hashlib
from calculadora.db.models import (
    insertar_usuario,
    obtener_usuario_por_nombre,
    get_connection
)

def hashear_password(password):
    """
    Hashea una contraseña generando un hash corto de 20 caracteres máximo.
    Usa truncado de SHA-256 limitado a 20 caracteres.
    
    Args:
        password: Contraseña en texto plano
        
    Returns:
        String: Hash truncado (máximo 20 caracteres)
    """
    # Hashear la contraseña usando SHA-256 (suficientemente seguro para este caso)
    # Añadimos un salt fijo para evitar ataques de diccionario
    salt = "Calc2025"  # Salt fijo para todas las contraseñas
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    # Truncamos a 20 caracteres (sigue siendo razonablemente seguro)
    return hashed[:20]

def verificar_password(password_proporcionado, password_almacenado):
    """
    Verifica si una contraseña coincide con el hash almacenado.
    Compatible con hash corto y comparación directa.
    
    Args:
        password_proporcionado: Contraseña en texto plano proporcionada por el usuario
        password_almacenado: Hash almacenado para la contraseña
        
    Returns:
        Boolean: True si la contraseña coincide, False en caso contrario
    """
    # Para contraseñas antiguas (texto plano) o hashes
    if len(password_almacenado) == 20:
        # Es un hash: generar el hash de la contraseña proporcionada y comparar
        salt = "Calc2025"  # El mismo salt usado para generar el hash
        hashed = hashlib.sha256((salt + password_proporcionado).encode()).hexdigest()[:20]
        return hashed == password_almacenado
    else:
        # Comparación directa (para contraseñas antiguas en texto plano)
        return password_proporcionado == password_almacenado

def validar_contrasena(password: str) -> bool:
    """
    Verifica que la contraseña:
      - Tenga al menos 8 caracteres
      - Contenga al menos 1 mayúscula
      - Contenga al menos 1 caracter especial (ej: . - , @ # ...)
    Retorna True si cumple, False si no.
    """
    if len(password) < 8:
        return False
    # Al menos una mayúscula y un caracter especial
    patron = r'^(?=.*[A-Z])(?=.*[\W_]).+$'
    return bool(re.search(patron, password))

def crear_usuario_si_no_existe(nombre, password, es_superusuario=False):
    """
    Intenta crear un usuario nuevo con contraseña hasheada, si no existe.
    Si ya existe, retorna el ID del usuario existente (sin modificar la contraseña).
    Permite definir si el usuario será superusuario.
    """
    usuario = obtener_usuario_por_nombre(nombre)
    if usuario is None:
        # Hashear la contraseña antes de guardarla
        password_hash = hashear_password(password)
        # Creamos el usuario con la contraseña hasheada
        user_id = insertar_usuario(nombre, password_hash, es_superusuario)
        print(f"Usuario '{nombre}' creado exitosamente.")
        return user_id, es_superusuario
    else:
        print(f"El usuario '{nombre}' ya existe. Se usará ese usuario.")
        return usuario[0], usuario[3]  # ID y es_superusuario del usuario existente

def autenticar_usuario(nombre, password):
    """
    Verifica si el usuario existe y la contraseña coincide con el hash almacenado.
    Retorna una tupla (user_id, es_superusuario) en caso de éxito, o (None, None) si no coincide.
    """
    usuario = obtener_usuario_por_nombre(nombre)
    if usuario:
        user_id, usuario_nombre, password_almacenado, es_superusuario = usuario
        # Verificar la contraseña contra el hash almacenado
        if verificar_password(password, password_almacenado):
            return user_id, es_superusuario
    return None, None

def crear_superusuario_inicial(nombre, password):
    """
    Asegura que exista al menos un superusuario en el sistema.
    Si el usuario ya existe, actualiza su flag a superusuario.
    """
    conn = get_connection()
    usuario = obtener_usuario_por_nombre(nombre)
    
    if usuario is None:
        # Hashear la contraseña antes de guardarla
        password_hash = hashear_password(password)
        # Crear el superusuario con la contraseña hasheada
        user_id = insertar_usuario(nombre, password_hash, True)
        print(f"Superusuario '{nombre}' creado exitosamente.")
        return user_id
    else:
        user_id, _, _, es_super = usuario
        if not es_super:
            # Actualizar a superusuario
            with conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE usuarios SET es_superusuario = TRUE
                        WHERE id = %s;
                    """, (user_id,))
            print(f"Usuario '{nombre}' actualizado a superusuario.")
        else:
            print(f"El usuario '{nombre}' ya es superusuario.")
        conn.close()
        return user_id

def obtener_o_crear_usuario(nombre):
    """
    LÓGICA ANTERIOR (opcional):
    Verifica si existe un usuario con 'nombre'.
    Si no existe, lo crea (SIN PEDIR CONTRASEÑA).
    """
    usuario = obtener_usuario_por_nombre(nombre)
    if usuario:
        return usuario[0]
    else:
        # Crear password temporal pero hasheado
        password_temp = "Temporal123!"
        password_hash = hashear_password(password_temp)
        # Por compatibilidad con el código original
        return insertar_usuario(nombre, password_hash)