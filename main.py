from src.chains import crear_cadena_principal

def main():
    print("Inicializando el sistema...")
    cadena = crear_cadena_principal()
    
    # Prueba rápida
    pregunta = "¿Qué ventajas tiene estructurar un proyecto de software en módulos?"
    print(f"\nUser: {pregunta}")
    
    respuesta = cadena.invoke({"input": pregunta})
    print(f"\nAI: {respuesta}")

if __name__ == "__main__":
    main()