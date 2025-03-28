# calculadora/db/models.py

import datetime
from calculadora.db.connection import get_connection

def crear_tablas():
    """
    Crea las tablas 'usuarios', 'operaciones' y 'historial_memoria' si no existen.
    """
    conn = get_connection()
    with conn:
        with conn.cursor() as cur:
            # Código existente para tabla usuarios
            cur.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    nombre VARCHAR(100) NOT NULL,
                    password VARCHAR(100) NOT NULL,
                    es_superusuario BOOLEAN DEFAULT FALSE,
                    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Verificación de columna es_superusuario (código existente)
            try:
                cur.execute("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'usuarios' AND column_name = 'es_superusuario';
                """)
                if cur.fetchone() is None:
                    cur.execute("""
                        ALTER TABLE usuarios 
                        ADD COLUMN es_superusuario BOOLEAN DEFAULT FALSE;
                    """)
                    print("Se añadió la columna 'es_superusuario' a la tabla usuarios.")
            except Exception as e:
                print(f"Error al verificar la columna: {e}")
                
            # Código existente para tabla operaciones
            cur.execute("""
                CREATE TABLE IF NOT EXISTS operaciones (
                    id SERIAL PRIMARY KEY,
                    usuario_id INT NOT NULL,
                    operando1 NUMERIC NOT NULL,
                    operador VARCHAR(10) NOT NULL,
                    operando2 NUMERIC NOT NULL,
                    resultado NUMERIC NOT NULL,
                    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
                );
            """)
            
            # NUEVA TABLA para historial persistente
            cur.execute("""
                CREATE TABLE IF NOT EXISTS historial_memoria (
                    id SERIAL PRIMARY KEY,
                    usuario_id INT NOT NULL,
                    fecha_hora TIMESTAMP NOT NULL,
                    descripcion TEXT NOT NULL,
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
                );
            """)
    conn.close()

def insertar_usuario(nombre, password, es_superusuario=False):
    """
    Inserta un nuevo usuario con nombre, contraseña y flag de superusuario.
    Retorna el ID generado.
    """
    conn = get_connection()
    new_id = None
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO usuarios (nombre, password, es_superusuario) 
                VALUES (%s, %s, %s) RETURNING id;
            """, (nombre, password, es_superusuario))
            new_id = cur.fetchone()[0]
    conn.close()
    return new_id

def obtener_usuario_por_nombre(nombre):
    """
    Retorna una tupla (id, nombre, password, es_superusuario) si existe un usuario con ese nombre,
    o None si no existe.
    """
    conn = get_connection()
    usuario = None
    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, nombre, password, es_superusuario FROM usuarios WHERE nombre = %s;", (nombre,))
            usuario = cur.fetchone()
    conn.close()
    return usuario

def insertar_operacion(usuario_id, operando1, operador, operando2, resultado):
    """
    Inserta una nueva operación en la tabla 'operaciones'.
    """
    conn = get_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO operaciones (usuario_id, operando1, operador, operando2, resultado)
                VALUES (%s, %s, %s, %s, %s);
            """, (usuario_id, operando1, operador, operando2, resultado))
    conn.close()

def obtener_operaciones(usuario_id=None, operando=None, operador=None):
    """
    Retorna una lista de operaciones de la tabla 'operaciones'.
    
    Parámetros opcionales para filtrar:
     - usuario_id: Filtra por el ID del usuario.
     - operando:   Filtra donde 'operando' esté en operando1 o operando2.
     - operador:   Filtra por el operador utilizado (+, -, *, /, ^, sqrt, etc.)
    """
    conn = get_connection()
    query = "SELECT * FROM operaciones"
    params = []
    conditions = []

    if usuario_id is not None:
        conditions.append("usuario_id = %s")
        params.append(usuario_id)
    if operando is not None:
        conditions.append("(operando1 = %s OR operando2 = %s)")
        params.extend([operando, operando])
    if operador is not None:
        conditions.append("operador = %s")
        params.append(operador)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    data = []
    with conn:
        with conn.cursor() as cur:
            cur.execute(query, tuple(params))
            rows = cur.fetchall()
            cols = [desc[0] for desc in cur.description]
            for row in rows:
                registro = dict(zip(cols, row))
                data.append(registro)
    conn.close()
    return data

def obtener_todas_las_operaciones_unidas():
    """
    Retorna todas las operaciones unidas con el nombre de usuario (JOIN con la tabla 'usuarios').
    """
    conn = get_connection()
    data = []
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    o.id as operacion_id,
                    u.id as usuario_id,
                    u.nombre as usuario,
                    o.operando1,
                    o.operador,
                    o.operando2,
                    o.resultado,
                    o.creado_en as operacion_creado_en
                FROM operaciones o
                JOIN usuarios u ON o.usuario_id = u.id
                ORDER BY o.id ASC;
            """)
            rows = cur.fetchall()
            cols = [desc[0] for desc in cur.description]
            for row in rows:
                registro = dict(zip(cols, row))
                data.append(registro)
    conn.close()
    return data

def obtener_todos_usuarios():
    """
    Retorna una lista de todos los usuarios registrados.
    """
    conn = get_connection()
    usuarios = []
    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, nombre, es_superusuario, creado_en FROM usuarios ORDER BY id;")
            rows = cur.fetchall()
            cols = ["id", "nombre", "es_superusuario", "creado_en"]
            for row in rows:
                usuario = dict(zip(cols, row))
                usuarios.append(usuario)
    conn.close()
    return usuarios

def guardar_en_historial(usuario_id, fecha_hora, descripcion):
    """
    Guarda una entrada de historial en la base de datos.
    """
    conn = get_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO historial_memoria (usuario_id, fecha_hora, descripcion)
                VALUES (%s, %s, %s);
            """, (usuario_id, fecha_hora, descripcion))
    conn.close()

def obtener_historial(usuario_id=None, horas_limite=24):
    """
    Obtiene el historial de las últimas horas_limite para un usuario específico o todos.
    
    Params:
        usuario_id: ID del usuario o None para todos los usuarios
        horas_limite: Número de horas hacia atrás para filtrar
    
    Returns:
        Una lista de diccionarios con los campos: usuario_id, usuario_nombre, fecha_hora, descripcion
    """
    conn = get_connection()
    fecha_limite = datetime.datetime.now() - datetime.timedelta(hours=horas_limite)
    
    query = """
        SELECT h.id, h.usuario_id, u.nombre as usuario_nombre, h.fecha_hora, h.descripcion
        FROM historial_memoria h
        JOIN usuarios u ON h.usuario_id = u.id
        WHERE h.fecha_hora > %s
    """
    
    params = [fecha_limite]
    
    if usuario_id is not None:
        query += " AND h.usuario_id = %s"
        params.append(usuario_id)
    
    query += " ORDER BY h.fecha_hora DESC"
    
    data = []
    with conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
            cols = [desc[0] for desc in cur.description]
            for row in rows:
                registro = dict(zip(cols, row))
                data.append(registro)
    conn.close()
    return data

def limpiar_historial_antiguo(horas_limite=24):
    """
    Elimina entradas del historial más antiguas que las horas especificadas.
    """
    conn = get_connection()
    fecha_limite = datetime.datetime.now() - datetime.timedelta(hours=horas_limite)
    
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM historial_memoria
                WHERE fecha_hora < %s;
            """, (fecha_limite,))
            eliminados = cur.rowcount
    conn.close()
    
    return eliminados