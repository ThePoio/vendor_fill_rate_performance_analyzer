from typing import TypedDict
import pandas as pd
from langgraph.graph import StateGraph, START, END
from src.config import inicializar_llm
from src.prompts import obtener_prompt_asistente
from src.tools import cargar_base_datos, buscar_en_base
from langchain_core.output_parsers import StrOutputParser

class EstadoProyecto(TypedDict):
    input: str
    contexto_bd: str
    respuesta: str

# Nodo que busca datos relevantes según la pregunta
def nodo_buscar_datos(state: EstadoProyecto):
    resultado = buscar_en_base.invoke({"query": state["input"]})
    return {"contexto_bd": resultado}

def cargar_csv_optimizado():
    try:
        import pandas as pd
        df = pd.read_csv("src/vendor_fill_rate_clean.csv")
        return df.head(5).to_csv(index=False) # Caso de prueba con solo 5 filas
    except FileNotFoundError:
        return "Error: No se encontró el archivo."
    except Exception as e:
        return f"Error: {e}"

# Nodo principal
def nodo_generar_recomendacion(state: EstadoProyecto):
    llm = inicializar_llm()
    prompt = obtener_prompt_asistente()
    parser = StrOutputParser()
    
    cadena = prompt | llm | parser
    
    resultado = cadena.invoke({
        "contexto_bd": state["contexto_bd"],
        "input": state["input"]
    })
    
    return {"respuesta": resultado}

def construir_grafo():
    workflow = StateGraph(EstadoProyecto)
    
    # Dos nodos ahora
    workflow.add_node("buscador", nodo_buscar_datos)
    workflow.add_node("analista_openai", nodo_generar_recomendacion)
    
    # Flujo: inicio → busca datos → analiza → fin
    workflow.add_edge(START, "buscador")
    workflow.add_edge("buscador", "analista_openai")
    workflow.add_edge("analista_openai", END)
    
    return workflow.compile()