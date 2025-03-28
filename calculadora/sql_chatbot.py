# calculadora/sql_chatbot.py

import json
import re
import hashlib
import os
import requests  # Asegúrate de importar requests para las llamadas API
from datetime import datetime, timedelta

# Configuración global
# API Key Groq
GROQ_API_KEY = os.getenv('GROQ_API_KEY', 'tu_api_key')  # Reemplazar o configurar en variables de entorno
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama3-70b-8192"  # LLaMA 3 70B 8192
CACHE_DURATION = timedelta(hours=24)  # Tiempo que se mantendrán las consultas en caché

# Configurar los headers para las llamadas API de Groq
GROQ_HEADERS = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

class QueryCache:
    """
    Sistema de caché para almacenar y recuperar consultas frecuentes.
    """
    def __init__(self, cache_file="query_cache.json"):
        self.cache_file = cache_file
        self.cache = self._load_cache()
    
    def _load_cache(self):
        """Carga el caché desde el archivo."""
        try:
            with open(self.cache_file, "r") as f:
                cache = json.load(f)
                # Convertir las fechas ISO a objetos datetime
                for key in cache:
                    cache[key]["timestamp"] = datetime.fromisoformat(cache[key]["timestamp"])
                return cache
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_cache(self):
        """Guarda el caché en el archivo."""
        # Convertir objetos datetime a cadenas ISO para serialización JSON
        serializable_cache = {}
        for key, value in self.cache.items():
            serializable_cache[key] = {
                "result": value["result"],
                "timestamp": value["timestamp"].isoformat()
            }
        
        with open(self.cache_file, "w") as f:
            json.dump(serializable_cache, f)
    
    def get(self, query_key):
        """
        Obtiene un resultado del caché si existe y no ha expirado.
        
        Args:
            query_key: Clave hash de la consulta
            
        Returns:
            El resultado cacheado o None si no existe o ha expirado
        """
        if query_key in self.cache:
            entry = self.cache[query_key]
            # Verificar si la entrada ha expirado
            if datetime.now() - entry["timestamp"] < CACHE_DURATION:
                return entry["result"]
            
            # Si expiró, eliminarla
            del self.cache[query_key]
            self._save_cache()
        
        return None
    
    def set(self, query_key, result):
        """
        Almacena un resultado en el caché.
        
        Args:
            query_key: Clave hash de la consulta
            result: Resultado a almacenar
        """
        self.cache[query_key] = {
            "result": result,
            "timestamp": datetime.now()
        }
        self._save_cache()
    
    def clear_expired(self):
        """Elimina entradas expiradas del caché."""
        current_time = datetime.now()
        expired_keys = [k for k, v in self.cache.items() 
                        if current_time - v["timestamp"] >= CACHE_DURATION]
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            self._save_cache()
            return len(expired_keys)
        return 0

class SQLSecurityValidator:
    """
    Valida consultas SQL para evitar operaciones peligrosas o no permitidas.
    Permite consultas más avanzadas para superusuarios.
    """
    def __init__(self):
        # Palabras clave bloqueadas para prevenir operaciones peligrosas
        self.blocked_keywords = [
            "DROP", "TRUNCATE", "DELETE", "UPDATE", "INSERT", "ALTER", 
            "CREATE", "GRANT", "REVOKE", "SHUTDOWN", "EXECUTE"
        ]
        
        # Tablas permitidas para consulta
        self.allowed_tables = [
            "usuarios", "operaciones", "historial_memoria"
        ]
    
    def validate_query(self, sql_query):
        """
        Valida si una consulta SQL es segura para ejecutar.
        Para superusuarios, permite consultas más avanzadas.
        
        Args:
            sql_query: Consulta SQL a validar
            
        Returns:
            Tuple (is_valid, reason, modified_query): Indica si es válida, razón si no lo es, y consulta modificada
        """
        # Convertir a mayúsculas para una comparación insensible a mayúsculas/minúsculas
        sql_upper = sql_query.upper()
        
        # 1. Verificar palabras clave bloqueadas
        for keyword in self.blocked_keywords:
            pattern = rf'\b{keyword}\b'
            if re.search(pattern, sql_upper):
                return False, f"Operación no permitida: {keyword}", None
        
        # 2. Verificar que solo se usen tablas permitidas
        # Extraer nombres de tablas de la consulta
        table_pattern = r'FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        tables = re.findall(table_pattern, sql_upper)
        
        join_pattern = r'JOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        tables.extend(re.findall(join_pattern, sql_upper))
        
        for table in tables:
            if table.lower() not in self.allowed_tables:
                return False, f"Tabla no permitida: {table}", None
        
        # 3. Verificar que sea solo una consulta
        if ";" in sql_query and sql_query.strip().count(";") > 1:
            return False, "No se permiten múltiples consultas (múltiples ';')", None
        
        # 4. Verificar límite sensible (opcional, para evitar consultas muy grandes)
        if "LIMIT" not in sql_upper and "SELECT" in sql_upper:
            # Añadir LIMIT automáticamente si no existe
            return True, "OK", sql_query + " LIMIT 100"
        
        return True, "OK", sql_query

class SQLChatbot:
    def __init__(self, db_connection, api_key=GROQ_API_KEY, user_tech_level="medio"):
        """
        Inicializa el chatbot SQL.
        
        Args:
            db_connection: Conexión a la base de datos
            api_key: Clave API para Groq
            user_tech_level: Nivel técnico del usuario ('basico', 'medio', 'avanzado')
        """
        self.db_connection = db_connection
        self.chat_history = []
        self.cache = QueryCache()
        self.security = SQLSecurityValidator()
        self.user_tech_level = user_tech_level
        
        # Obtener esquema de base de datos
        self.db_schema = self._get_db_schema()
        
    def _get_db_schema(self):
        """Obtiene el esquema de la base de datos."""
        cursor = self.db_connection.cursor()
        # Consulta para obtener información sobre tablas y columnas
        cursor.execute("""
            SELECT table_name, column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'public'
            AND table_name IN ('usuarios', 'operaciones', 'historial_memoria')
            ORDER BY table_name, ordinal_position;
        """)
        
        schema = {}
        for table_name, column_name, data_type in cursor.fetchall():
            if table_name not in schema:
                schema[table_name] = []
            schema[table_name].append({"column": column_name, "type": data_type})
            
        return schema
    
    def _call_llm(self, prompt, system_message, temperature=0.1):
        """
        Llama al modelo LLM de Groq y fuerza respuestas en español.
        
        Args:
            prompt: Texto del prompt
            system_message: Mensaje del sistema para contextualizar
            temperature: Temperatura para el modelo (0.0 - 1.0)
            
        Returns:
            Respuesta del modelo
        """
        try:
            # Modificar el system_message para enfatizar respuesta en español
            enhanced_system = system_message + "\n\nIMPORTANTE: DEBES RESPONDER SIEMPRE EN ESPAÑOL. TODA TU RESPUESTA DEBE ESTAR EN ESPAÑOL."
            
            # Añadir instrucción explícita al final del prompt
            enhanced_prompt = prompt + "\n\nResponde completamente en español."
            
            # Preparar los datos para la API de Groq
            data = {
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": enhanced_system},
                    {"role": "user", "content": enhanced_prompt}
                ],
                "temperature": temperature
            }
            
            # Hacer la llamada a la API
            response = requests.post(GROQ_API_URL, headers=GROQ_HEADERS, json=data)
            
            # Verificar si la respuesta fue exitosa
            if response.status_code == 200:
                # Extraer y devolver el texto de la respuesta
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                # Manejar error de la API
                error_msg = f"Error en la API de Groq: {response.status_code} - {response.text}"
                print(error_msg)
                return f"Lo siento, no pude procesar tu consulta. Error: {response.status_code}"
                
        except Exception as e:
            # Si falla por completo, entregar un fallback básico
            print(f"Error al llamar a la API de Groq: {str(e)}")
            return f"Lo siento, no pude procesar tu consulta en este momento. Error: {str(e)}"
        
    def _add_spanish_instruction(self, prompt):
        """
        Añade instrucciones explícitas para responder en español.
        
        Args:
            prompt: El prompt original
            
        Returns:
            Prompt modificado con instrucciones para responder en español
        """
        # Añadir instrucción al final del prompt
        if prompt.strip().endswith('.'):
            modified_prompt = f"{prompt} Responde siempre en español."
        else:
            modified_prompt = f"{prompt} Responde siempre en español."
        
        return modified_prompt
        
    def _analyze_intent(self, user_input):
        """
        Analiza la intención del usuario para entender su consulta.
        
        Args:
            user_input: Consulta en lenguaje natural
            
        Returns:
            JSON con la interpretación de la intención
        """
        # Generar clave para caché
        cache_key = hashlib.md5(f"intent:{user_input}".encode()).hexdigest()
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        system_message = """
        Eres un asistente especializado en entender consultas en lenguaje natural para una calculadora avanzada 
        con capacidades SQL. Identifica qué tabla(s) y tipo de operación (SELECT, COUNT, AVG, etc.) 
        quiere realizar el usuario. Responde con un JSON.
    
        Importante: SIEMPRE responde en español, independientemente del idioma de la consulta.
        """
        
        prompt = f"""
        Analiza la siguiente consulta del usuario:
        
        "{user_input}"
        
        Responde con un JSON que contenga:
        1. Las tablas involucradas
        2. El tipo de operación
        3. Filtros o condiciones
        4. Nivel de confianza (0-1)
        """
        
        result = self._call_llm(prompt, system_message)
        # Guardar en caché para futuras consultas similares
        self.cache.set(cache_key, result)
        result = self._call_llm(self._add_spanish_instruction(prompt), system_message)
        return result
    
    def _generate_sql(self, user_input, intent):
        """
        Genera una consulta SQL basada en la entrada del usuario.
        Permite consultas más avanzadas.
        
        Args:
            user_input: Consulta en lenguaje natural
            intent: Intención detectada
            
        Returns:
            Código SQL generado
        """
        # Generar clave para caché
        cache_key = hashlib.md5(f"sql:{user_input}".encode()).hexdigest()
        cached = self.cache.get(cache_key)
        if cached:
            return cached
            
        schema_info = "\n".join([
            f"Tabla: {table_name}\nColumnas: {', '.join([c['column'] + ' (' + c['type'] + ')' for c in cols])}"
            for table_name, cols in self.db_schema.items()
        ])
        
        # Permitimos consultas más avanzadas
        system_message = """
        Eres un experto en SQL. Tu tarea es generar consultas SQL avanzadas basadas en 
        peticiones en lenguaje natural. Genera SOLO código SQL sin explicaciones.
        
        IMPORTANTE:
        1. Usa solo consultas SELECT para preservar la seguridad de los datos
        2. Puedes usar JOINS complejos, subconsultas, funciones de agregación y ventana
        3. Puedes usar GROUP BY, HAVING, ORDER BY, y otras cláusulas avanzadas
        4. Nunca uses DELETE, INSERT, UPDATE, DROP, ALTER u otras operaciones de modificación
        """
        
        prompt = f"""
        Esquema de la base de datos:
        {schema_info}
        
        Intención del usuario detectada:
        {intent}
        
        Consulta original del usuario:
        "{user_input}"
        
        Genera una consulta SQL que satisfaga esta petición. Puedes usar características avanzadas
        como JOINS, subconsultas, funciones de agregación, y más. Solo incluye el código SQL, nada más.
        """
        
        result = self._call_llm(prompt, system_message)
        # Limpiar el resultado (eliminar comillas, bloques de código, etc.)
        result = result.replace('```sql', '').replace('```', '').strip()
        
        # Guardar en caché para futuras consultas similares
        self.cache.set(cache_key, result)
        result = self._call_llm(self._add_spanish_instruction(prompt), system_message)
        return result
    
    def _execute_query(self, sql_query):
        """
        Ejecuta la consulta SQL de manera segura.
        
        Args:
            sql_query: Consulta SQL a ejecutar
            
        Returns:
            Diccionario con los resultados o error
        """
        # Validar seguridad de la consulta
        is_valid, reason, modified_query = self.security.validate_query(sql_query)
        
        if not is_valid:
            return {
                "success": False, 
                "error": f"Consulta rechazada por seguridad: {reason}",
                "query": sql_query
            }
        
        # Usar la consulta modificada si fue necesario añadir LIMIT
        sql_query = modified_query if modified_query else sql_query
        
        # Generar clave para caché
        cache_key = hashlib.md5(f"exec:{sql_query}".encode()).hexdigest()
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        try:
            cursor = self.db_connection.cursor()
            cursor.execute(sql_query)
            
            # Si no hay resultados, devolver mensaje apropiado
            if cursor.description is None:
                return {"success": True, "data": [], "query": sql_query, "message": "La consulta no devolvió resultados."}
            
            columns = [desc[0] for desc in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            result = {"success": True, "data": results, "query": sql_query}
            # Guardar en caché para futuras consultas idénticas
            self.cache.set(cache_key, result)
            return result
        except Exception as e:
            return {"success": False, "error": str(e), "query": sql_query}
    
    def _format_response(self, results, original_query):
        """
        Formatea la respuesta según el nivel técnico del usuario.
        
        Args:
            results: Resultados de la consulta
            original_query: Consulta original del usuario
            
        Returns:
            Respuesta formateada en lenguaje natural
        """
        # Ajustar contenido según nivel técnico
        technical_detail = {
            "basico": "Explica los resultados de forma simple, evitando términos técnicos. SIEMPRE responde en español.",
            "medio": "Equilibra los detalles técnicos con explicaciones accesibles. SIEMPRE responde en español.",
            "avanzado": "Incluye detalles técnicos relevantes y términos SQL específicos. SIEMPRE responde en español."
        }
        
        system_message = f"""
        Eres un asistente que explica resultados de consultas SQL en lenguaje natural.
        {technical_detail.get(self.user_tech_level, "medio")}
        IMPORTANTE: SIEMPRE responde en español, independientemente del idioma de la consulta.
        """
        
        if results["success"]:
            # Si hay demasiados resultados, mostrar solo algunos
            if len(results["data"]) > 5:
                data_str = "\n".join([str(row) for row in results["data"][:5]])
                data_str += f"\n... y {len(results['data']) - 5} resultados más"
            else:
                data_str = "\n".join([str(row) for row in results["data"]])
                
            prompt = f"""
            Consulta original: "{original_query}"
            
            SQL ejecutado: {results["query"]}
            
            Resultados: 
            {data_str}
            
            Explica estos resultados en lenguaje natural, destacando información 
            relevante y patrones interesantes.
            """
        else:
            prompt = f"""
            Consulta original: "{original_query}"
            
            SQL que falló: {results["query"]}
            
            Error: {results["error"]}
            
            Explica este error en términos simples y sugiere cómo el usuario 
            podría reformular su consulta.
            """
            
        return self._call_llm(self._add_spanish_instruction(prompt), system_message, temperature=0.7)
    
    def process_query(self, user_input):
        """
        Procesa una consulta en lenguaje natural.
        
        Args:
            user_input: Consulta en lenguaje natural
            
        Returns:
            Respuesta en lenguaje natural
        """
        # Paso 1: Análisis de la consulta
        intent = self._analyze_intent(user_input)
        
        # Paso 2: Generación de SQL
        sql_query = self._generate_sql(user_input, intent)
        
        # Paso 3: Ejecución
        results = self._execute_query(sql_query)
        
        # Paso 4: Presentación de resultados
        response = self._format_response(results, user_input)
        
        # Guardar en historial
        self.chat_history.append({
            "query": user_input, 
            "sql": sql_query,
            "response": response,
            "timestamp": datetime.now().isoformat()
        })
        
        return response
    
    def get_feedback(self, is_correct, correction=None):
        """
        Procesa el feedback del usuario para mejorar futuras respuestas.
        
        Args:
            is_correct: Si la interpretación fue correcta
            correction: Corrección proporcionada por el usuario
        """
        if not self.chat_history:
            return "No hay consultas recientes para corregir."
        
        last_query = self.chat_history[-1]
        
        if is_correct:
            # Si fue correcto, no hay acción adicional
            return "¡Gracias por la confirmación!"
        
        if correction:
            # Agregar la corrección al historial
            self.chat_history[-1]["correction"] = correction
            
            # Usar la corrección para generar una mejor respuesta
            system_message = """
            Eres un asistente que aprende de las correcciones. 
            Analiza la consulta original, tu respuesta anterior, y la corrección del usuario.
            Proporciona una respuesta mejorada basada en esta retroalimentación.

            IMPORTANTE: SIEMPRE responde en español, independientemente del idioma de la consulta o corrección.
            """
            
            prompt = f"""
            Consulta original: "{last_query['query']}"
            
            Tu respuesta anterior: "{last_query['response']}"
            
            Corrección del usuario: "{correction}"
            
            Proporciona una respuesta mejorada que aborde la corrección del usuario.
            """
            
            improved_response = self._call_llm(prompt, system_message, temperature=0.5)
            self.chat_history[-1]["improved_response"] = improved_response
            
            improved_response = self._call_llm(self._add_spanish_instruction(prompt), system_message, temperature=0.5)
            return improved_response
        
        return "Gracias por la retroalimentación. ¿Cómo podría mejorar mi respuesta?"
    
    def set_tech_level(self, level):
        """
        Actualiza el nivel técnico del usuario.
        
        Args:
            level: Nivel técnico ('basico', 'medio', 'avanzado')
        """
        if level in ["basico", "medio", "avanzado"]:
            self.user_tech_level = level
            return f"Nivel técnico actualizado a: {level}"
        return "Nivel técnico no válido. Use 'basico', 'medio' o 'avanzado'."
    
    def clear_cache(self):
        """Limpia el caché de consultas."""
        self.cache = QueryCache()
        return "Caché limpiado correctamente."
        
    def get_sql_for_query(self, user_input):
        """
        Método auxiliar para obtener directamente el SQL generado para una consulta.
        Útil para depuración o para mostrar el SQL al usuario.
        
        Args:
            user_input: Consulta en lenguaje natural
            
        Returns:
            String con la consulta SQL generada
        """
        intent = self._analyze_intent(user_input)
        sql = self._generate_sql(user_input, intent)
        return sql
    