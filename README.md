# Calculadora Avanzada

Un sistema avanzado de calculadora con autenticación de usuarios, operaciones matemáticas, registro de historial, exportación de datos y capacidades de consulta mediante un chatbot SQL.

![Calculadora Avanzada](./public/calculadora.jpg)

## Características Principales

- **Sistema de autenticación**: Usuarios normales y superusuarios
- **Operaciones matemáticas avanzadas**: Suma, resta, multiplicación, división, potencias y raíz cuadrada
- **Registro de historial**: Almacenamiento persistente de operaciones y acciones
- **Exportación de datos**: Exportación de resultados a CSV y Excel
- **Chatbot SQL**: Interfaz de consulta en lenguaje natural (solo superusuarios)
- **Seguridad**: Contraseñas hasheadas y validación de consultas SQL

## Estructura del Proyecto

```
calculadora/
│
├── core/                       # Funcionalidades básicas
│   ├── __init__.py
│   ├── export_utils.py         # Utilidades de exportación
│   ├── operators.py            # Operadores matemáticos
│   └── utils.py                # Utilidades generales
│
├── db/                         # Capa de datos
│   ├── __init__.py
│   ├── connection.py           # Conexión a la base de datos
│   └── models.py               # Modelos y operaciones de BD
│
├── services/                   # Servicios de la aplicación
│   ├── __init__.py
│   ├── operation_service.py    # Servicio de operaciones
│   └── user_service.py         # Servicio de usuarios
│
├── __init__.py
├── cli_app.py                  # Aplicación de línea de comandos
├── consultas.py                # Consultas predefinidas
├── sql_chatbot.py              # Chatbot SQL con IA
│
├── venv/                       # Entorno virtual (no incluido en repo)
├── .env                        # Variables de entorno (no incluido en repo)
├── .gitignore                  # Archivos ignorados por git
├── main.py                     # Punto de entrada principal
├── query_cache.json            # Caché de consultas del chatbot
├── README.md                   # Documentación
└── requirements.txt            # Dependencias del proyecto
```

## Diagrama de Flujo

El siguiente diagrama muestra el flujo de trabajo de la aplicación:

```mermaid
flowchart TD
    Start([Inicio Aplicación]) --> Auth{Autenticación}
    Auth -->|Éxito| Menu[Menú Principal]
    Auth -->|Fallido| Auth
    
    %% Opciones de menú - Usuario normal
    subgraph UserOptions[Opciones para todos los usuarios]
        Op1[Nueva Operación]
        Op2[Consultas]
        Op3[Ver Historial]
        Op4[Exportar]
    end
    
    %% Opciones de menú - Superusuario
    subgraph AdminOptions[Opciones exclusivas para superusuario]
        Op5[Crear Usuario]
        Op6[Chatbot SQL]
    end
    
    %% Conexiones al menú principal
    Menu --> UserOptions
    Menu --> AdminOptions
    Menu --> Exit([Salir])
    
    %% Flujo de operación matemática
    Op1 --> OperFlow[Realizar cálculo]
    OperFlow --> SaveOp[Guardar en BD]
    SaveOp --> SaveHist[Registrar en Historial]
    SaveHist --> Menu
    
    %% Flujo de consultas
    Op2 --> QueryType{Tipo consulta}
    QueryType -->|Usuario| UserQueries[Mis operaciones]
    QueryType -->|Superusuario| AllQueries[Todas las operaciones]
    UserQueries --> ShowResults[Mostrar resultados]
    AllQueries --> ShowResults
    ShowResults --> Menu
    
    %% Flujo de historial
    Op3 --> HistType{Tipo usuario}
    HistType -->|Normal| UserHist[Mi historial]
    HistType -->|Superusuario| AllHist[Historial completo]
    UserHist --> ShowHist[Mostrar historial]
    AllHist --> ShowHist
    ShowHist --> Menu
    
    %% Flujo de exportación
    Op4 --> ExportType{Formato}
    ExportType -->|CSV| ExportCSV[Exportar CSV]
    ExportType -->|Excel| ExportExcel[Exportar Excel]
    ExportCSV --> Menu
    ExportExcel --> Menu
    
    %% Flujo de creación de usuario
    Op5 --> VerifyAuth{Verificar contraseña}
    VerifyAuth -->|Correcta| UserType{Tipo usuario}
    UserType -->|Normal| CreateUser[Crear usuario normal]
    UserType -->|Super| CreateSuper[Crear superusuario]
    CreateUser --> Menu
    CreateSuper --> Menu
    VerifyAuth -->|Incorrecta| Menu
    
    %% Flujo de chatbot SQL
    Op6 --> VerifyAuthSQL{Verificar contraseña}
    VerifyAuthSQL -->|Correcta| Chatbot[Chatbot SQL]
    VerifyAuthSQL -->|Incorrecta| Menu
    
    Chatbot --> NLQuery[Consulta en lenguaje natural]
    NLQuery --> Process[Procesar consulta]
    Process --> GenSQL[Generar SQL]
    GenSQL --> Execute[Ejecutar consulta]
    Execute --> Format[Formatear resultados]
    Format --> Chatbot
    Chatbot -->|Salir| Menu
```

**Nota**: El diagrama se visualizará correctamente cuando subas el README.md a GitHub o GitLab.

### Descripción del flujo

1. **Inicio y Autenticación**: La aplicación comienza con un sistema de autenticación donde el usuario debe registrarse o iniciar sesión.
2. **Menú Principal**: Tras autenticarse, se accede al menú principal con múltiples opciones.
3. **Operaciones**: El usuario puede realizar operaciones matemáticas que se guardan en la base de datos y se registran en el historial.
4. **Consultas y Exportación**: Se pueden consultar operaciones anteriores y exportar resultados.
5. **Funciones de Superusuario**: Los superusuarios tienen acceso a funcionalidades adicionales como la creación de usuarios y el chatbot SQL.
6. **Chatbot SQL**: Permite realizar consultas en lenguaje natural que se convierten en SQL y muestran resultados formateados.

## Arquitectura MCP del Chatbot SQL

El chatbot SQL implementa una arquitectura "Model-Context-Protocol" (MCP):

- **Modelo**: Representado por las operaciones de base de datos en `db/models.py` que definen la estructura de datos y lógica de negocio
- **Contexto**: Implementado en `sql_chatbot.py` que mantiene el estado de la conversación y gestiona el procesamiento de consultas en lenguaje natural
- **Protocolo**: Define las reglas de comunicación entre el usuario y el sistema, incluyendo la validación de entradas, la traducción a SQL y el formato de respuestas a través de la interfaz CLI

## Requisitos Previos

- Python 3.8+
- PostgreSQL 12+
- Cuenta en Groq (para el chatbot SQL)

## Instalación

1. Clonar el repositorio:
   ```bash
   git clone https://github.com/username/calculadora-avanzada.git
   cd calculadora-avanzada
   ```

2. Crear y activar entorno virtual:
   ```bash
   # En Windows
   python -m venv venv
   venv\Scripts\activate
   
   # En Linux/Mac
   python -m venv venv
   source venv/bin/activate
   ```

3. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```

4. Configurar la base de datos PostgreSQL:
   - Crear una base de datos llamada `calculadora`
   - Configurar las credenciales en el archivo `.env`

5. Configurar variables de entorno:
   - Copiar el archivo `.env.example` a `.env`
   - Actualizar las variables con tus credenciales:
   
   ```
   # Variables para PostgreSQL
   POSTGRES_DB=calculadora
   POSTGRES_USER=tu_usuario
   POSTGRES_PASSWORD=tu_contraseña
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   
   # API Key para Groq (necesario para el chatbot SQL)
   GROQ_API_KEY=tu_api_key_de_groq
   ```

## Uso

### Iniciar la aplicación

```bash
python main.py
```

### Autenticación

Al iniciar la aplicación, se presentará un menú de autenticación:
1. Registrarse
2. Iniciar Sesión
3. Salir

#### Requisitos de contraseña:
- Al menos 8 caracteres
- Al menos 1 mayúscula
- Al menos 1 caracter especial

### Menú Principal

Una vez autenticado, tendrás acceso al menú principal:

1. **Realizar Nueva Operación**
   - Permite realizar operaciones matemáticas: +, -, *, /, ^, sqrt
   - Los resultados se guardan automáticamente

2. **Consultas**
   - Ver operaciones realizadas
   - Filtrar por operador
   - Consultas avanzadas (superusuario)

3. **Ver Historial**
   - Acceso al historial de operaciones de las últimas 24 horas
   - Superusuarios pueden ver el historial de todos los usuarios

4. **Exportar Operaciones**
   - Exportar a formato CSV o Excel
   - Superusuarios pueden exportar todas las operaciones

5. **Crear Usuario** (solo superusuarios)
   - Crear usuarios normales o superusuarios

6. **Chatbot SQL** (solo superusuarios)
   - Realizar consultas en lenguaje natural sobre la base de datos
   - Ver SQL generado
   - Exportar resultados

### Chatbot SQL

Ejemplos de consultas para el chatbot:
- "¿Cuántas operaciones ha realizado el usuario admin?"
- "¿Cuál es el promedio de los resultados de sumas?"
- "Muéstrame las últimas 5 operaciones de todos los usuarios"
- "¿Quién ha usado más la raíz cuadrada?"
- "Exportar las operaciones del usuario admin"

Comandos especiales:
- `!nivel [basico/medio/avanzado]`: Cambia el nivel técnico de las respuestas
- `!feedback [corrección]`: Proporciona retroalimentación sobre la última respuesta
- `!cache`: Limpia el caché de consultas
- `!sql [consulta]`: Muestra el SQL generado para una consulta sin ejecutarla
- `!salir`: Volver al menú principal

## Seguridad

- Contraseñas hasheadas con SHA-256 y salt
- Validación de consultas SQL para prevenir inyecciones
- Acceso limitado a funcionalidades críticas (solo superusuarios)
- Historial persistente con limpieza automática

## Desarrollo

### Añadir nuevos operadores

Para añadir un nuevo operador matemático, modifica el archivo `core/operators.py`:

```python
operators = {
    # ... operadores existentes
    'nuevo_op': lambda a, b: # lógica del operador
}
```

### Extender el chatbot SQL

Para mejorar las capacidades del chatbot SQL, puedes:
1. Modificar los prompts en `sql_chatbot.py`
2. Añadir nuevas validaciones en `SQLSecurityValidator`
3. Mejorar el sistema de caché en `QueryCache`

## Licencia

Este proyecto está licenciado bajo los términos de la licencia MIT.
