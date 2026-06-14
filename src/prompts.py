from langchain_core.prompts import ChatPromptTemplate

def obtener_prompt_asistente():
    """
    [NOTA PARA CH]: Modifica el texto de aquí abajo 
    para darle la personalidad y reglas al bot.
    """
    return ChatPromptTemplate.from_messages([
        ("system", "Eres un asistente de IA experto en proyectos escolares. Responde de forma concisa."),
        ("human", "{input}")
    ])