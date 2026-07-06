from src.graph import construir_grafo

def main():
    print("Inicializando Arquitectura LangGraph")
    
    app = construir_grafo()
    
    pregunta = "Acción para los PO que tuvieron problemas con el transporte?"
    print(f"\nUsuario: {pregunta}")
    
    estado_inicial = {
        "input": pregunta,
        "contexto_bd": "",
        "respuesta": ""
    }
    
    print("\nLlamando a la API de openai...")
    estado_final = app.invoke(estado_inicial)
    
    print(f"\nRespuesta de openai:\n{estado_final['respuesta']}")

if __name__ == "__main__":
    main()