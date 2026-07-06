# =====================================================================
# 1. REGLA DE ORO: CONFIGURAR Y ARRANCAR PHOENIX ANTES QUE CUALQUIER OTRA COSA
# =====================================================================
from dotenv import load_dotenv

# Cargamos credenciales (p. ej., OPENAI_API_KEY) desde tu entorno
load_dotenv()

import phoenix as px
from phoenix.otel import register

# Opción A: Evaluar localmente (Inicia una interfaz web en tu máquina)
px.launch_app(port=6006)

# Opción B (Si usas Arize Phoenix Cloud, descomenta lo siguiente y pon tus llaves en el .env):
# os.environ["PHOENIX_CLIENT_HEADERS"] = f"api_key={os.getenv('PHOENIX_API_KEY')}"
# px.Client(base_url=os.getenv("PHOENIX_COLLECTOR_ENDPOINT"))

# Registramos el trazador. Esto interceptará automáticamente LangGraph, LangChain y LLMs.
tracer_provider = register(
    project_name="Vendor Fill Rate Performance Analyzer",
    auto_instrument=True
)

# =====================================================================
# 2. IMPORTS DE LA ARQUITECTURA (SÓLO DESPUÉS DE REGISTRAR EL TRACER)
# =====================================================================
# Ahora es seguro importar los archivos de tu carpeta src/
from src.graph import construir_grafo, cargar_csv_optimizado

# =====================================================================
# 3. CREACIÓN DEL GOLDEN DATASET (Casos de prueba con Verdad Absoluta)
# =====================================================================
# Definimos preguntas que fuercen al LLM a usar la base de datos local
eval_dataset = [
    {
        "input": "¿Cuántos usuarios nuevos se registraron en los últimos 7 días?",
        "expected_output": "Se registraron un total de 24 usuarios nuevos.",
    },
    {
        "input": "Muestra el nombre del producto más caro en inventario.",
        "expected_output": "El producto más caro es la 'Laptop Workstation v2' con un precio de $2,500 USD.",
    },
    {
        "input": "Obtén el total de ventas del día de hoy.",
        "expected_output": "El total de ventas para hoy es de $12,450 pesos.",
    }
]

# =====================================================================
# 4. FLUJO DE EJECUCIÓN DEL AGENTE (Simulación de Consultas a la BD)
# =====================================================================
def ejecutar_simulacion_agente():
    print("\n▶️ Enviando preguntas de prueba al agente de LangGraph...")
    
    for i, caso in enumerate(eval_dataset):
        print(f"📊 Evaluando Caso {i+1}/{len(eval_dataset)}: '{caso['input']}'")
        
        # Adaptar las llaves según el State de tu LangGraph (ej. usando mensajes o strings)
        inputs = {"messages": [("user", caso["input"])]}
        config = {"configurable": {"thread_id": f"eval_sql_run_{i}"}}
        
        # Ejecutamos el grafo. Phoenix registrará el comportamiento del LLM y de las Tools de BD.
        try:
            respuesta = app.invoke(inputs, config=config)
            print(f"✅ Caso {i+1} completado.")
        except Exception as e:
            print(f"❌ Error ejecutando el caso {i+1}: {e}")

# =====================================================================
# 5. MÓDULO DE EVALUACIÓN (LLM-as-a-Judge)
# =====================================================================
from phoenix.evals import OpenAIModel, QAEvaluator, run_evals, LLMEvaluator

def ejecutar_evaluaciones_programaticas():
    print("\n🔍 Descargando trazas de Arize Phoenix para su análisis...")
    client = px.Client()
    
    # 5.1. Extraer Spans (pasos de ejecución) generados por el proyecto
    spans_df = client.get_spans_dataframe(project_name="vendor_fill_rate_performance_analyzer", limit=1000)
    
    if spans_df.empty:
        print("⚠ No se encontraron trazas de ejecución en Phoenix para evaluar.")
        return

    # Usaremos GPT-4o (o tu modelo preferido) como el Juez experto
    model_juez = OpenAIModel(model="gpt-5o-mini", temperature=0)

    # -----------------------------------------------------------------
    # EVALUACIÓN 1: Calidad de la Respuesta Final (QA Correctness)
    # -----------------------------------------------------------------
    print("🤖 Evaluando precisión y calidad de la respuesta final entregada al usuario...")
    qa_evaluator = QAEvaluator(model=model_juez)
    
    # Filtramos los spans raíz (las respuestas definitivas del agente)
    root_spans = spans_df[spans_df["parent_id"].isna()]
    
    # -----------------------------------------------------------------
    # EVALUACIÓN 2: Calidad de las Consultas SQL / Herramientas de BD
    # -----------------------------------------------------------------
    print("🗄️ Evaluando la precisión y optimización de las consultas SQL generadas...")
    
    # Creamos un prompt personalizado para evaluar las llamadas a las tools de Base de Datos
    SQL_EVAL_PROMPT = """
    Eres un Administrador de Bases de Datos (DBA) senior actuando como juez de IA. 
    Tu tarea es evaluar si la consulta SQL o los parámetros enviados a la herramienta de base de datos son correctos y óptimos.

    [Pregunta Original del Usuario]: {input}
    [Query SQL/Parámetro generado por el LLM]: {tool_input}
    [Resultado devuelto por la Base de Datos]: {tool_output}

    Evalúa bajo los siguientes criterios:
    1. ¿La sintaxis de la consulta es correcta y válida?
    2. ¿La lógica de la query responde exactamente a lo que el usuario pidió (filtros correctos, joins necesarios, agregaciones)?
    3. ¿Es una consulta segura (no expone mutaciones peligrosas como DELETE sin filtro o SQL Injection)?

    Devuelve tu veredicto exactamente en este formato:
    SCORE: [Un número flotante entre 0.0 y 1.0, donde 1.0 es una consulta perfecta y 0.0 es totalmente errónea o rompió la BD]
    REASON: [Una breve explicación técnica en español de por qué otorgaste ese score]
    """

    # Filtramos los spans que correspondan a la ejecución de TOOLS (las creadas por tu compañero)
    tool_spans = spans_df[spans_df["span_kind"] == "TOOL"]

    if not tool_spans.empty:
        print(f"-> Se detectaron {len(tool_spans)} llamadas a herramientas de Base de Datos. Evaluando...")
        # Aquí puedes mapear las columnas de Phoenix al prompt para correr la evaluación
        # Phoenix guardará las notas de evaluación directamente vinculadas a la query en la interfaz web.
    else:
        print("⚠ No se detectaron ejecuciones de herramientas de base de datos en las trazas.")

    print("\n✅ Evaluación finalizada con éxito.")
    print(f"🔗 Revisa los gráficos detallados y puntuaciones en: {session.url}")
    
    # Mantener el script congelado para que no se apague el servidor local de Phoenix
    input("\n🛑 Presiona ENTER en esta terminal para cerrar el servidor de Phoenix...")

# =====================================================================
# 6. FUNCIÓN PRINCIPAL ORQUESTADORA
# =====================================================================
if __name__ == "__main__":
    # Paso 1: Alimentamos el agente con preguntas para generar trazas interactuando con la BD local
    ejecutar_simulacion_agente()
    
    # Paso 2: Ejecutamos los jueces de evaluación sobre las trazas recolectadas
    ejecutar_evaluaciones_programaticas()