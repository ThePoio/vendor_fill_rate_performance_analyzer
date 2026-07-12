import os 
from dotenv import load_dotenv, find_dotenv
from langchain_openai import ChatOpenAI  

#Carga de la credencial del arciho .env
load_dotenv(find_dotenv())

def inicializar_llm():
    """Inicializa el modelo de lenguaje de OpenAI utilizando la clave API almacenada en las variables de entorno."""

    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        raise ValueError(
            "❌ ERROR CRÍTICO: No se pudo leer 'OPENAI_API_KEY'.\n"
            "Posibles causas:\n"
            "1. El archivo no se llama exactamente '.env'\n"
            "2. Estás ejecutando el comando desde la carpeta incorrecta.\n"
            " Ruta actual de ejecución: " + os.getcwd()
        )
    #Se usara gpt-5.4-nano

    return ChatOpenAI(
        model="gpt-5.4-nano",
        temperature=0.3,
        timeout=None,
        max_retries=2,
    )