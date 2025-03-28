# script_migrar_passwords.py
from calculadora.db.connection import get_connection
import hashlib

def hashear_password_corto(password):
    """
    Versión que genera un hash de exactamente 20 caracteres.
    """
    # Salt fijo para mantener compatibilidad
    salt = "Calc2025"
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    # Truncamos a 20 caracteres
    return hashed[:20]

def migrar_passwords():
    """
    Migra las contraseñas existentes en texto plano a formato hash de 20 caracteres.
    """
    conn = get_connection()
    usuarios_migrados = 0
    
    with conn:
        with conn.cursor() as cur:
            # Obtener usuarios con contraseñas en texto plano
            cur.execute("SELECT id, nombre, password FROM usuarios")
            usuarios = cur.fetchall()
            
            for user_id, nombre, password in usuarios:
                # Si la contraseña no tiene exactamente 20 caracteres, asumimos que no está hasheada
                if len(password) != 20:
                    try:
                        # Hashear la contraseña usando formato corto de 20 caracteres
                        password_hash = hashear_password_corto(password)
                        
                        # Verificar longitud
                        assert len(password_hash) == 20, f"Hash de longitud incorrecta: {len(password_hash)}"
                            
                        # Actualizar en la base de datos
                        cur.execute(
                            "UPDATE usuarios SET password = %s WHERE id = %s",
                            (password_hash, user_id)
                        )
                        
                        usuarios_migrados += 1
                        print(f"Migrada contraseña para el usuario: {nombre}")
                        
                    except Exception as e:
                        print(f"Error al migrar usuario {nombre}: {e}")
    
    conn.close()
    print(f"Migración completada. {usuarios_migrados} contraseñas actualizadas.")

if __name__ == "__main__":
    migrar_passwords()