# src/graph.py
from typing import TypedDict
import pandas as pd
from langgraph.graph import StateGraph, START, END
from src.config import inicializar_llm
from src.prompts import obtener_prompt_asistente
from langchain_core.output_parsers import StrOutputParser

# 1. Definimos el Estado Global del Grafo (la pizarra de datos)
class EstadoProyecto(TypedDict):
    input: str          # La pregunta del usuario
    contexto_bd: str    # Los datos extraídos y filtrados del CSV
    respuesta: str      # La respuesta final generada por openai

def cargar_csv_optimizado():
    try:
        import pandas as pd
        df = pd.read_csv("src/vendor_fill_rate_clean.csv")
        return df.head(5).to_csv(index=False) # Caso de prueba con solo 5 filas
    except FileNotFoundError:
        return "Error: No se encontró el archivo."
    except Exception as e:
        return f"Error: {e}"

# 2. Definimos el Nodo Principal
def nodo_generar_recomendacion(state: EstadoProyecto):
    # Invocamos la configuración de openai y el prompt del Integrante A
    llm = inicializar_llm()
    prompt = obtener_prompt_asistente()
    parser = StrOutputParser()
    
    # Orquestamos la cadena interna de este nodo
    cadena = prompt | llm | parser
    
    # Ejecutamos la llamada a la API usando los datos del Estado del grafo
    resultado = cadena.invoke({
        "contexto_bd": state["contexto_bd"],
        "input": state["input"]
    })
    
    # Retornamos el cambio para actualizar la pizarra (Estado)
    return {"respuesta": resultado}

# 3. Construcción y compilación del Grafo
def construir_grafo():
    workflow = StateGraph(EstadoProyecto)
    
    # Añadimos nuestro nodo de análisis
    workflow.add_node("analista_openai", nodo_generar_recomendacion)
    
    # Definimos el flujo lineal inicial: Inicio -> Nodo -> Fin
    workflow.add_edge(START, "analista_openai")
    workflow.add_edge("analista_openai", END)
    
    # Compilamos la aplicación de LangGraph
    return workflow.compile()