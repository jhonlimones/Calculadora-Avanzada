# calculadora/core/serialization_utils.py

import pickle
import os
from datetime import datetime

def serialize_data(data, filename):
    """
    Serializa datos en un archivo usando pickle.
    
    Args:
        data: Datos a serializar (cualquier objeto Python)
        filename: Nombre del archivo donde se guardará
    
    Returns:
        bool: True si la operación fue exitosa, False en caso contrario
    """
    try:
        with open(filename, 'wb') as f:
            pickle.dump(data, f)
        return True
    except Exception as e:
        print(f"Error al serializar datos: {e}")
        return False

def deserialize_data(filename):
    """
    Deserializa datos desde un archivo pickle.
    
    Args:
        filename: Nombre del archivo a deserializar
    
    Returns:
        El objeto deserializado o None si hay error
    """
    try:
        if not os.path.exists(filename):
            return None
        
        with open(filename, 'rb') as f:
            return pickle.load(f)
    except Exception as e:
        print(f"Error al deserializar datos: {e}")
        return None

def backup_user_data(user_id, data, backup_dir="backups"):
    """
    Crea una copia de seguridad de los datos de un usuario.
    
    Args:
        user_id: ID del usuario
        data: Datos a respaldar
        backup_dir: Directorio para las copias de seguridad
    
    Returns:
        str: Ruta del archivo de respaldo o None si hay error
    """
    try:
        # Crear directorio si no existe
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        # Generar nombre de archivo con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{backup_dir}/user_{user_id}_{timestamp}.pkl"
        
        # Serializar datos
        if serialize_data(data, filename):
            return filename
        return None
    except Exception as e:
        print(f"Error al crear copia de seguridad: {e}")
        return None