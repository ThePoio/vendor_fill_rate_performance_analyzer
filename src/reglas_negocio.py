# src/reglas_negocio.py
"""
Reglas de negocio puras (sin LLM) para clasificar el tipo de excepción de un PO.
Esto implementa el tip del README: "primero implementar las reglas en Python puro
y verificar que la clasificación coincide con los flags del CSV antes de integrar el LLM."

Se valida contra FILL_RATE_ISSUE y LATE_ISSUE, que en el dataset synthetic
están definidos exactamente como:
    FILL_RATE_ISSUE = 'Y'  <=>  FILL_RATE < 85
    LATE_ISSUE      = 'Y'  <=>  RECEIPT_DELAY_DAYS > 5
(verificado: 100% de coincidencia en las 400 filas del CSV synthetic)
"""

TIPOS_VALIDOS = ("late_only", "low_fill", "both", "clean")


def clasificar_tipo(fill_rate: float, delay_dias: float) -> str:
    """Clasifica el tipo de excepción según los umbrales del README (sección 2)."""
    fill_bajo = fill_rate < 85
    hay_retraso = delay_dias > 5

    if fill_bajo and hay_retraso:
        return "both"
    if hay_retraso:
        return "late_only"
    if fill_bajo:
        return "low_fill"
    return "clean"


def tipo_esperado_desde_flags(fill_rate_issue: str, late_issue: str) -> str:
    """Construye el 'tipo esperado' directamente desde los flags ya calculados en el CSV."""
    fill_bajo = str(fill_rate_issue).strip().upper() == "Y"
    hay_retraso = str(late_issue).strip().upper() == "Y"

    if fill_bajo and hay_retraso:
        return "both"
    if hay_retraso:
        return "late_only"
    if fill_bajo:
        return "low_fill"
    return "clean"


def es_po_critico(dnp_ranking: str, oos_likely: str) -> bool:
    """Top 10% de rentabilidad + riesgo de desabasto inminente => PO crítico (Criterio D)."""
    return (
        str(dnp_ranking).strip() == "Top 10%"
        and str(oos_likely).strip().upper() == "Y"
    )


def es_problema_recurrente(avg_fill_rate_8wk: float) -> bool:
    """Regla de negocio: promedio de 8 semanas < 80 => problema recurrente."""
    try:
        return float(avg_fill_rate_8wk) < 80
    except (TypeError, ValueError):
        return False
