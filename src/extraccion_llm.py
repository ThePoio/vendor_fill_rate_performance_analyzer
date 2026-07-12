# src/extraccion_llm.py
"""
Extrae información estructurada del texto libre que genera el LLM, para poder
calcular métricas de forma confiable (evita el bug de comparar el output crudo
completo contra el label esperado).
"""
import re

# Variantes que el prompt puede generar (nota: prompts.py mezcla "Without Exception"
# en inglés con "Sin excepción" en el Ejemplo 3 -- normalizamos ambas).
ACCIONES = {
    "Without Exception": [
        r"without exception",
        r"sin excepci[oó]n",
        r"no requiere ninguna acci[oó]n",
    ],
    "Vendor Outreach": [
        r"vendor outreach",
    ],
    "Escalate to Merchant": [
        r"escalate to merchant",
        r"escalar? al? merchant",
    ],
}


def extraer_accion(texto: str) -> str | None:
    """
    Busca la acción canónica mencionada en el texto del LLM.
    Devuelve None si no se encuentra ninguna, o si se detecta más de una
    (ambiguo -> mejor no adivinar).
    """
    if not texto:
        return None

    texto_norm = texto.lower()
    encontradas = []
    for accion, patrones in ACCIONES.items():
        if any(re.search(p, texto_norm) for p in patrones):
            encontradas.append(accion)

    if len(encontradas) == 1:
        return encontradas[0]
    if len(encontradas) > 1:
        # Ambigüedad real: el modelo mencionó más de una acción canónica.
        # Nos quedamos con la última mención (suele ser la recomendación final).
        posiciones = {
            accion: max(
                (m.start() for p in ACCIONES[accion] for m in re.finditer(p, texto_norm)),
                default=-1,
            )
            for accion in encontradas
        }
        return max(posiciones, key=posiciones.get)
    return None


# --- Criterio C: heurística de calidad de explicación (proxy automático) ------
# El README pide una "rúbrica manual en 20 POs". Esto NO reemplaza esa revisión
# humana -- es un chequeo automático rápido para pre-filtrar y dar una señal
# aproximada mientras se hace la revisión manual real.

PALABRAS_CAUSA = [
    "causa", "constraint", "shortage", "retraso", "transportation",
    "manufactur", "capacity", "shipment", "issue",
]
PALABRAS_IMPACTO = [
    "inventario", "wos", "semanas de inventario", "desabasto", "oos",
    "tiendas", "stock",
]
PALABRAS_RECURRENCIA = [
    "recurrente", "nuevo problema", "reincidente", "histórico", "tendencia",
]


def calificar_explicacion_heuristica(texto: str) -> dict:
    """Proxy automático (0-3) de si la explicación toca causa, impacto y recurrencia."""
    if not texto:
        return {"menciona_causa": False, "menciona_impacto": False,
                "menciona_recurrencia": False, "score_heuristico": 0}

    texto_norm = texto.lower()
    menciona_causa = any(p in texto_norm for p in PALABRAS_CAUSA)
    menciona_impacto = any(p in texto_norm for p in PALABRAS_IMPACTO)
    menciona_recurrencia = any(p in texto_norm for p in PALABRAS_RECURRENCIA)

    return {
        "menciona_causa": menciona_causa,
        "menciona_impacto": menciona_impacto,
        "menciona_recurrencia": menciona_recurrencia,
        "score_heuristico": sum([menciona_causa, menciona_impacto, menciona_recurrencia]),
    }
