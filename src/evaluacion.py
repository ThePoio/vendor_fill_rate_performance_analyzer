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
# 2. IMPORTS DE TU ARQUITECTURA (SÓLO DESPUÉS DE REGISTRAR EL TRACER)
# =====================================================================
# Ahora es seguro importar los archivos de tu carpeta src/
from src.graph import construir_grafo, cargar_csv_optimizado

# =====================================================================
# 3. SET DE PRUEBAS (DATASET) Y FUNCIÓN DE EJECUCIÓN
# =====================================================================
def construir_dataset_de_prueba():
    """
    Casos de prueba basados en los ejemplos incluidos en prompts.py.
    """
    return [
        {
            "nombre": "Ejemplo 1 - ULTRAMED",
            "inputs": (
                "Analiza el siguiente caso y recomienda una acción:\n"
                "Vendor: ULTRAMED\n"
                "PO: 32003 | SKU: 25014 | DC: AZ\n"
                "Categoría: PERSONAL CARE | Importancia: Top 10%\n"
                "Fill Rate actual: 60%\n"
                "Promedio 4 sem: 62.9%\n"
                "Promedio 8 sem: 66.7%\n"
                "Retraso: 4.1 días\n"
                "Riesgo OOS: Y\n"
                "WOS total: 23.31 semanas\n"
                "Tiendas afectadas: 50 tiendas\n"
                "Causa raíz: Vendor capacity constraint"
            ),
            "expected_output": "Vendor Outreach"
        },
        {
            "nombre": "Ejemplo 2 - HEALTHCORP",
            "inputs": (
                "Analiza el siguiente caso y recomienda una acción:\n"
                "Vendor: HEALTHCORP\n"
                "PO: 32002 | SKU: 17331 | DC: IL\n"
                "Categoría: DIGESTIVE HEALTH | Importancia: Bottom 50%\n"
                "Fill Rate actual: 80.2%\n"
                "Promedio 4 sem: 78.8%\n"
                "Promedio 8 sem: 79.7%\n"
                "Retraso: 3.2 días\n"
                "Riesgo OOS: N\n"
                "WOS total: 57.81 semanas\n"
                "Tiendas afectadas: 293 tiendas\n"
                "Causa raíz: Vendor capacity constraint"
            ),
            "expected_output": "Escalate to Merchant"
        },
        {
            "nombre": "Ejemplo 3 - BIOMED",
            "inputs": (
                "Analiza el siguiente caso y recomienda una acción:\n"
                "Vendor: BIOMED\n"
                "PO: 32011 | SKU: 97900 | DC: NC\n"
                "Categoría: HAIR CARE | Importancia: Top 50%\n"
                "Fill Rate actual: 94.3%\n"
                "Promedio 4 sem: 95.8%\n"
                "Promedio 8 sem: 93.3%\n"
                "Retraso: 2.9 días\n"
                "Riesgo OOS: N\n"
                "WOS total: 23.19 semanas\n"
                "Tiendas afectadas: 119 tiendas\n"
                "Causa raíz: Partial shipment"
            ),
            "expected_output": "Without Exception"
        }
    ]


def ejecutar_pruebas_de_evaluacion():
    app = construir_grafo()
    contexto_bd = cargar_csv_optimizado()
    dataset_de_prueba = construir_dataset_de_prueba()
    
    print("\n▶️ Iniciando simulación del agente para capturar trazas...")
    
    for i, caso in enumerate(dataset_de_prueba):
        print(f"Procesando caso {i+1}: {caso['nombre']}")

        # Estructura alineada con EstadoProyecto en graph.py
        inputs = {
            "input": caso["inputs"],
            "contexto_bd": contexto_bd,
            "respuesta": ""
        }

        # Invocamos el grafo con el estado esperado.
        config = {"configurable": {"thread_id": f"test_run_{i}"}}
        respuesta = app.invoke(inputs, config=config)

        salida_modelo = respuesta.get("respuesta", "")
        print(f"Acción esperada: {caso['expected_output']}")
        print(f"Respuesta del modelo: {salida_modelo}\n")
        print(f"Caso {i+1} completado.")

    print("\n✅ Trazas generadas exitosamente.")
    print("🔗 Ve a tu navegador e ingresa a: http://localhost:6006")

    #Input para evitar que la ventana de Phoenix se cierre automáticamente
    input("Presiona Enter para finalizar la simulación y cerrar Phoenix...")
if __name__ == "__main__":
    ejecutar_pruebas_de_evaluacion()