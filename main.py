# main.py
from src.graph import construir_grafo, cargar_csv_optimizado

def main():
    print("Inicializando Arquitectura LangGraph")
    
    # 1. Compilar el grafo
    app = construir_grafo()
    
    # 2. Cargar los datos del CSV automáticamente
    datos_contexto = cargar_csv_optimizado()
    
    # 3. Pregunta de prueba para el test
    pregunta = "¿Cuales son los 3 principales proveedores con excepciones que puedan considerarse peligrosas o que deban tomar atencion?"
    print(f"\nUsuario: {pregunta}")
    
    # 4. Definir el estado inicial
    estado_inicial = {
        "input": pregunta,
        "contexto_bd": datos_contexto,
        "respuesta": ""
    }
    
    # 5. Ejecutar el grafo (Llamada a la API de openai)
    print("\nLlamando a la API de openai (gpt-4o-mini)...")
    estado_final = app.invoke(estado_inicial)
    
    # 6. Mostrar el resultado del test
    print(f"\nRespuesta de openai:\n{estado_final['respuesta']}")

if __name__ == "__main__":
    main()