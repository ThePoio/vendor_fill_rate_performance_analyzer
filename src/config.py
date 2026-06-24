import os 
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI  

#Carga de la credencial del arciho .env
load_dotenv()

def inicializar_llm():
    """Inicializa el modelo de lenguaje de OpenAI utilizando la clave API almacenada en las variables de entorno."""

    #Se usara gpt-4o-mini

    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.3,
        timeout=None,
        max_retries=2,
    )