import os 
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic  

#Carga de la credencial del arciho .env
load_dotenv()

def inicializar_llm():
    """Inicializa el modelo de lenguaje de Anthropic utilizando la clave API almacenada en las variables de entorno."""

    #Se usara claude-3-5-sonnet

    return ChatAnthropic(
        model="claude-3-5-sonnet",
        temperature=0.3,
        timeout=None,
        max_retries=2,
    )