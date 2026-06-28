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
    """Lee el CSV, filtra las columnas clave y lo convierte a formato JSON para la API."""
    try:
        df = pd.read_csv("data/vendor_fill_rate_synthetic.csv")
        
        # Convertimos a JSON string (es el formato más ligero y limpio para enviar por API)
        return df.to_json(orient="records", force_ascii=False)
    except Exception as e:
        return f"Error cargando base de datos: {e}"

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