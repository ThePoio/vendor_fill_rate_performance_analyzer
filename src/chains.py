from src.config import inicializar_llm
from src.prompts import obtener_prompt_asistente
from langchain_core.output_parsers import StrOutputParser

def crear_cadena_principal():
    # Traemos el modelo y el prompt de los otros archivos
    llm = inicializar_llm()
    prompt = obtener_prompt_asistente()
    
    # El StrOutputParser asegura que el resultado sea texto limpio (string) y no un objeto complejo
    parser = StrOutputParser()
    
    # Unimos todo con el operador '|' (así funciona LangChain)
    cadena_final = prompt | llm | parser
    return cadena_final