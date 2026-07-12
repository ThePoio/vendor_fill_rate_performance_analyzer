# src/tools.py
import pandas as pd
from langchain_core.tools import tool

@tool
def cargar_base_datos() -> str:
    """Carga y limpia la base de datos de proveedores."""
    try:
        df = pd.read_csv("src/vendor_fill_rate_synthetic.csv")

        columnas = [
            "VENDOR_NAME", "SKU_NBR", "DC_ID", "CATEGORY",
            "DNP_RANKING", "FILL_RATE", "TOTAL_WEEKS_OF_SUPPLY",
            "RECEIPT_DELAY_DAYS", "OOS_LIKELY", "FILL_RATE_ISSUE",
            "AVG_FILL_RATE_4WK", "AVG_RECEIPT_DELAY_4WK",
            "AVG_FILL_RATE_8WK", "AVG_RECEIPT_DELAY_8WK",
            "STORE_COUNT", "COMBINED_CAUSE"
        ]
        df = df[columnas]

        df["COMBINED_CAUSE"] = df["COMBINED_CAUSE"].str.strip()

        df.to_csv("src/vendor_fill_rate_clean.csv", index=False)

        return df.to_csv(index=False)

    except FileNotFoundError:
        return "Error: No se encontró el archivo."
    except Exception as e:
        return f"Error: {e}"

@tool
def buscar_en_base(query: str) -> str:
    """Busca proveedores relevantes en la base de datos según la pregunta del usuario."""
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import StrOutputParser
        import json
        from src.prompts import obtener_prompt_filtros

        df = pd.read_csv("src/vendor_fill_rate_clean.csv")
        
        causas = str(df["COMBINED_CAUSE"].unique().tolist())
        categorias = str(df["CATEGORY"].unique().tolist())
        proveedores = str(df["VENDOR_NAME"].unique().tolist())
        
        llm = ChatOpenAI(model="gpt-4o", temperature=0, max_tokens=500)
        
        prompt_filtro = obtener_prompt_filtros(causas, categorias, proveedores)
        cadena_filtro = prompt_filtro | llm | StrOutputParser()
        resultado_filtro = cadena_filtro.invoke({"query": query})
        
        resultado_filtro = resultado_filtro.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        print(f"Filtro generado: {resultado_filtro}")

        data = json.loads(resultado_filtro)

        filtros = data.get("filtros", [])
        limite = data.get("limite", 5)
        ordenar_por = data.get("ordenar_por", None)

        for filtro in filtros:
            if filtro["tipo"] == "ninguno":
                continue
            elif filtro["tipo"] == "numerico":
                col = filtro["columna"]
                op = filtro["operador"]
                val = filtro["valor"]
                if op == ">":
                    df = df[df[col] > val]
                elif op == "<":
                    df = df[df[col] < val]
                elif op == ">=":
                    df = df[df[col] >= val]
                elif op == "<=":
                    df = df[df[col] <= val]
                elif op == "==":
                    df = df[df[col] == val]
            elif filtro["tipo"] == "texto":
                col = filtro["columna"]
                val = filtro["valor"]
                df = df[df[col].str.contains(val, case=False, na=False)]

        if ordenar_por:
            col = ordenar_por["columna"]
            direccion = ordenar_por.get("direccion", "desc") == "asc"
            df = df.sort_values(col, ascending=direccion)

        if df.empty:
            return "No se encontraron resultados para ese filtro."

        return df.head(limite).to_csv(index=False)
        print(f"Filtro aplicado: {data}")

    except Exception as e:
        return f"Error: {e}"
    
@tool
def memoria_contexto(info: str) -> str:
    """Guarda información relevante para el contexto de la conversación."""
    return f"Contexto guardado: {info}"