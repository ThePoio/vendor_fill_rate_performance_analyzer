from dotenv import load_dotenv
load_dotenv()

from src.tools import cargar_base_datos, buscar_en_base, memoria_contexto


# Prueba 1 - carga
print("=== TOOL 1: CARGA ===")
print(cargar_base_datos.invoke({}))

# Prueba filtro numérico
print("=== FILTRO NUMÉRICO ===")
print(buscar_en_base.invoke({"query": "proveedores con fill rate menor a 85"}))

# Prueba filtro de texto
print("=== FILTRO TEXTO ===")
print(buscar_en_base.invoke({"query": "problemas de clima"}))

# Prueba query ambigua
print("=== QUERY AMBIGUA ===")
print(buscar_en_base.invoke({"query": "proveedores peligrosos"}))

# Prueba 3 - memoria
print("=== TOOL 3: MEMORIA ===")
print(memoria_contexto.invoke({"info": "El proveedor ULTRAMED tiene retraso frecuente"}))