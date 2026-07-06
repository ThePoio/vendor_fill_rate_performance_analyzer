# src/tools.py
import pandas as pd
from langchain_core.tools import tool

@tool
def cargar_base_datos() -> str:
    """Carga la base de datos de proveedores."""
    try:
        df = pd.read_csv("src/vendor_fill_rate_clean.csv")
        return df
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

        df = pd.read_csv("src/vendor_fill_rate_clean.csv")
        
        causas = str(df["COMBINED_CAUSE"].unique().tolist())
        categorias = str(df["CATEGORY"].unique().tolist())
        proveedores = str(df["VENDOR_NAME"].unique().tolist())
        
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=300)
        
        system_msg = (

    "Eres un asistente que genera filtros para buscar en un DataFrame de proveedores.\n\n"
    "Valores reales disponibles en el CSV:\n"
    "- COMBINED_CAUSE: " + causas + "\n"
    "- CATEGORY: " + categorias + "\n"
    "- VENDOR_NAME: " + proveedores + "\n\n"
    "Columnas numéricas: FILL_RATE, RECEIPT_DELAY_DAYS, TOTAL_WEEKS_OF_SUPPLY, "
    "AVG_FILL_RATE_4WK, AVG_FILL_RATE_8WK, AVG_RECEIPT_DELAY_4WK, AVG_RECEIPT_DELAY_8WK, STORE_COUNT.\n\n"
    "Responde SOLO con una lista JSON válida sin backticks ni markdown.\n"
    "Cada elemento debe tener: tipo, columna, operador y valor para numéricos.\n"
    "Para texto: tipo, columna y valor.\n"
    "Si no hay filtro: lista con un elemento de tipo ninguno.\n"
    "Usa EXACTAMENTE los valores del CSV para filtros de texto.\n"
    "Si la pregunta es ambigua o no encaja exactamente con una columna, "
    "sigue las reglas de negocio: busca el filtro más parecido al contexto de la pregunta. "
    "Por ejemplo, si preguntan por proveedores peligrosos o en riesgo, "
    "filtra por indicadores negativos como FILL_RATE bajo o RECEIPT_DELAY_DAYS alto. "
    "NUNCA respondas: tipo ninguno. si la pregunta implica buscar algo en los datos."
                      
        )

        prompt_filtro = ChatPromptTemplate.from_messages([
            ("system", system_msg),
            ("human", "{query}")
        ])

        cadena_filtro = prompt_filtro | llm | StrOutputParser()
        resultado_filtro = cadena_filtro.invoke({"query": query})
        
        # Limpia backticks por si acaso
        resultado_filtro = resultado_filtro.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        print(f"Filtro generado: {resultado_filtro}")

        filtros = json.loads(resultado_filtro)

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

        if df.empty:
            return "No se encontraron resultados para ese filtro."

        return df.head(10).to_csv(index=False)

    except Exception as e:
        return f"Error: {e}"
    
@tool
def memoria_contexto(info: str) -> str:
    """Guarda información relevante para el contexto de la conversación."""
    return f"Contexto guardado: {info}"