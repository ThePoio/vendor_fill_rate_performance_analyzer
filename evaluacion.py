# =====================================================================
# MÓDULO DE EVALUACIÓN — Vendor Fill Rate Performance Analyzer
# Implementa los 5 criterios de la sección 6 del README usando Arize Phoenix
# =====================================================================
from datetime import datetime, timezone

from dotenv import load_dotenv
import os
import pandas as pd

load_dotenv()
os.environ["PHOENIX_WORKING_DIR"] = "./.phoenix_data"

import phoenix as px
from phoenix.client import Client
from phoenix.otel import register
from phoenix.evals import LLM, create_classifier, evaluate_dataframe
from phoenix.evals.utils import to_annotation_dataframe

from src.chains import crear_cadena_principal
from src.reglas_negocio import (
    clasificar_tipo,
    tipo_esperado_desde_flags,
    es_po_critico,
    es_problema_recurrente,
)
from src.extraccion_llm import extraer_accion, calificar_explicacion_heuristica

# =====================================================================
# 1. PHOENIX: sesión + tracer
# =====================================================================
session = px.launch_app(port=6006, use_temp_dir=False)
tracer_provider = register(
    project_name="Vendor Fill Rate Performance Analyzer",
    auto_instrument=True,  # traza automáticamente las llamadas de langchain
)

# Umbrales de la sección 6 del README
UMBRALES = {
    "accuracy_clasificacion": 80.0,
    "accuracy_accion_llm": 70.0,
    "calidad_explicacion": 3.5,  # sobre 5 (heurístico, no reemplaza rúbrica manual)
    "cobertura_criticos": 90.0,
    "llm_as_judge": 3.5,
}

RUTA_CSV_CRUDO = "src/vendor_fill_rate_synthetic.csv"
N_CASOS_EVALUACION = 20  # limitar para no saturar el batch de prueba
COLUMNAS_NECESARIAS = [
    "PO_NBR", "VENDOR_NAME", "SKU_NBR", "DC_ID", "CATEGORY",
    "DNP_RANKING", "FILL_RATE", "AVG_FILL_RATE_4WK", "AVG_FILL_RATE_8WK",
    "RECEIPT_DELAY_DAYS", "OOS_LIKELY", "FILL_RATE_ISSUE", "LATE_ISSUE",
    "TOTAL_WEEKS_OF_SUPPLY", "STORE_COUNT", "COMBINED_CAUSE", "COMBINED_ACTION",
]


# =====================================================================
# 2. CONSTRUCCIÓN DEL DATASET DE PRUEBA DESDE EL CSV CRUDO
# =====================================================================
# OJO: usamos el CSV crudo (vendor_fill_rate_synthetic.csv), NO el que produce
# cargar_base_datos()/limpiar_dataset(), porque ese descarta PO_NBR y
# COMBINED_ACTION -- que son justo el ground truth que necesitamos para evaluar.
def construir_dataset_de_prueba(ruta_csv: str, n: int = N_CASOS_EVALUACION) -> list[dict]:
    df = pd.read_csv(ruta_csv)
    faltantes = [c for c in COLUMNAS_NECESARIAS if c not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas en el CSV para evaluar: {faltantes}")

    df = df[COLUMNAS_NECESARIAS].head(n)

    dataset = []
    for _, row in df.iterrows():
        contexto_bd_texto = (
            f"Vendor: {row['VENDOR_NAME']}\n"
            f"PO: {row['PO_NBR']} | SKU: {row['SKU_NBR']} | DC: {row['DC_ID']}\n"
            f"Categoría: {row['CATEGORY']} | Importancia (DNP): {row['DNP_RANKING']}\n"
            f"Fill Rate actual: {row['FILL_RATE']}%\n"
            f"Promedio 4 sem: {row['AVG_FILL_RATE_4WK']}%\n"
            f"Promedio 8 sem: {row['AVG_FILL_RATE_8WK']}%\n"
            f"Retraso: {row['RECEIPT_DELAY_DAYS']} días\n"
            f"Riesgo OOS: {row['OOS_LIKELY']}\n"
            f"WOS total: {row['TOTAL_WEEKS_OF_SUPPLY']} semanas\n"
            f"Tiendas afectadas: {row['STORE_COUNT']}\n"
            f"Causa raíz: {row['COMBINED_CAUSE']}"
        )

        dataset.append({
            "po_id": str(row["PO_NBR"]),
            "contexto_bd": contexto_bd_texto,
            "input": "Analiza este caso y genera la explicación y la acción recomendada.",
            "expected_action": row["COMBINED_ACTION"],
            "tipo_esperado_csv": tipo_esperado_desde_flags(
                row["FILL_RATE_ISSUE"], row["LATE_ISSUE"]
            ),
            "tipo_regla_python": clasificar_tipo(
                row["FILL_RATE"], row["RECEIPT_DELAY_DAYS"]
            ),
            "es_critico": es_po_critico(row["DNP_RANKING"], row["OOS_LIKELY"]),
            "es_recurrente": es_problema_recurrente(row["AVG_FILL_RATE_8WK"]),
        })
    return dataset


# =====================================================================
# 3. EJECUCIÓN DEL AGENTE (llamada directa a la cadena, caso por caso)
# =====================================================================
# Usamos crear_cadena_principal() directamente en lugar del grafo completo:
# el nodo "buscador" del grafo (buscar_en_base) está pensado para responder
# preguntas de un usuario sobre TODA la base, no para analizar un PO puntual.
# Para evaluar caso por caso, lo correcto es alimentar el contexto de esa
# fila directamente al prompt.
def ejecutar_agente_sobre_dataset(dataset: list[dict]) -> pd.DataFrame:
    cadena = crear_cadena_principal()
    resultados = []

    print("\n▶️ Ejecutando el agente sobre el dataset de prueba...")
    for caso in dataset:
        print(f"  Procesando PO {caso['po_id']}...")
        config = {"metadata": {"po_id": caso["po_id"]}, "tags": ["evaluacion"]}
        salida = cadena.invoke(
            {"contexto_bd": caso["contexto_bd"], "input": caso["input"]},
            config=config,
        )

        accion_extraida = extraer_accion(salida)
        calidad = calificar_explicacion_heuristica(salida)

        resultados.append({
            **{k: v for k, v in caso.items() if k != "contexto_bd"},
            "llm_output": salida,
            "llm_accion_extraida": accion_extraida,
            **calidad,
        })

    return pd.DataFrame(resultados)


# =====================================================================
# 4. CRITERIO A — Accuracy de clasificación (regla pura, sin LLM) >80%
# =====================================================================
def calcular_criterio_a(df: pd.DataFrame) -> float:
    coincide = df["tipo_regla_python"] == df["tipo_esperado_csv"]
    return coincide.mean() * 100


# =====================================================================
# 5. CRITERIO B — Accuracy de acción LLM vs COMBINED_ACTION >70%
# =====================================================================
def calcular_criterio_b(df: pd.DataFrame) -> dict:
    extraidas = df["llm_accion_extraida"].notna()
    n_extraidas = extraidas.sum()
    if n_extraidas == 0:
        return {"accuracy": 0.0, "cobertura_extraccion": 0.0}

    coincide = df.loc[extraidas, "llm_accion_extraida"] == df.loc[extraidas, "expected_action"]
    return {
        "accuracy": coincide.mean() * 100,
        "cobertura_extraccion": (n_extraidas / len(df)) * 100,
    }


# =====================================================================
# 6. CRITERIO D — Cobertura de POs críticos >90%
# =====================================================================
def calcular_criterio_d(df: pd.DataFrame) -> str | float:
    criticos = df[df["es_critico"]]
    if criticos.empty:
        return "N/A (no hay POs críticos en este batch)"
    extraidas = criticos["llm_accion_extraida"].notna()
    if extraidas.sum() == 0:
        return 0.0
    coincide = (
        criticos.loc[extraidas, "llm_accion_extraida"]
        == criticos.loc[extraidas, "expected_action"]
    )
    return coincide.mean() * 100


# =====================================================================
# 7. CRITERIO C — Calidad de explicación (proxy heurístico + export manual)
# =====================================================================
def calcular_criterio_c(df: pd.DataFrame, ruta_export: str = "revision_manual_20_pos.csv"):
    score_heuristico_promedio = df["score_heuristico"].mean() / 3 * 5  # normalizado a /5

    columnas_revision = [
        "po_id", "llm_output", "menciona_causa", "menciona_impacto",
        "menciona_recurrencia", "score_heuristico",
    ]
    df_revision = df[columnas_revision].copy()
    df_revision["puntaje_manual_0_a_5"] = ""  # para llenar a mano según la rúbrica del README
    df_revision.to_csv(ruta_export, index=False)

    return score_heuristico_promedio, ruta_export


# =====================================================================
# 8. CRITERIO E — LLM-as-judge sobre las trazas de Phoenix (stretch, >3.5/5)
# =====================================================================
EVAL_TEMPLATE = """
Eres un evaluador experto en cadena de suministro.
Tu tarea es calificar la explicación generada por un asistente de IA para una orden de compra (PO).
Debes evaluar si la explicación menciona la causa, el impacto y justifica la acción tomada.

Criterios de puntuación (0 a 5):
- 0: No explica nada útil.
- 1-2: Explicación vaga, falta causa o impacto.
- 3: Menciona causa e impacto, pero la justificación de la acción es débil.
- 4: Menciona causa, impacto y justifica la acción claramente.
- 5: Explicación perfecta, clara, accionable y completamente justificada.

Texto a evaluar:
{output}

Devuelve ÚNICAMENTE un número entero del 0 al 5.
"""


def calcular_criterio_e(marca_inicio=None):
    # get_spans_dataframe ya no vive en el objeto `session` en versiones
    # recientes de arize-phoenix -- ahora se consulta a través del Client.
    # IMPORTANTE: Phoenix persiste las trazas en disco entre corridas
    # (PHOENIX_WORKING_DIR + use_temp_dir=False), así que sin start_time
    # aquí se traería el histórico acumulado de TODAS las corridas anteriores,
    # no solo la actual.
    traces_df = Client().spans.get_spans_dataframe(
        project_name="Vendor Fill Rate Performance Analyzer",
        start_time=marca_inicio,
    )
    if traces_df is None or traces_df.empty:
        print("⚠️ No se encontraron trazas en Phoenix para evaluar.")
        return None

    llm_spans = traces_df[traces_df["span_kind"] == "LLM"].copy()

    if llm_spans.empty:
        print("⚠️ No se encontraron spans de LLM en las trazas para evaluar.")
        return None

    if "output" not in llm_spans.columns and "attributes.output.value" in llm_spans.columns:
        llm_spans["output"] = llm_spans["attributes.output.value"]

    eval_model = LLM(provider="openai", model="gpt-4o")
    evaluator = create_classifier(
        name="calificacion_explicacion",
        prompt_template=EVAL_TEMPLATE,
        llm=eval_model,
        choices=["0", "1", "2", "3", "4", "5"],
    )

    calificaciones = evaluate_dataframe(dataframe=llm_spans, evaluators=[evaluator])
    calificaciones_df = to_annotation_dataframe(
        dataframe=calificaciones, score_names=["calificacion_explicacion"],
    )

    # json/httpx no acepta NaN (allow_nan=False) -- lo convertimos a None (null).
    # OJO: .where(pd.notnull(df), None) por sí solo NO funciona en columnas
    # numéricas (float64) -- pandas no puede guardar None ahí y lo revierte a
    # NaN silenciosamente. Hay que forzar dtype=object primero para que el
    # None se preserve de verdad.
    calificaciones_df = calificaciones_df.astype(object).where(
        pd.notnull(calificaciones_df), None
    )
    columnas_de_valor = [
        c for c in calificaciones_df.columns
        if c not in ("context.span_id", "span_id", "name")
    ]
    n_antes = len(calificaciones_df)
    calificaciones_df = calificaciones_df.dropna(subset=columnas_de_valor, how="all")
    n_descartadas = n_antes - len(calificaciones_df)
    if n_descartadas:
        print(f"⚠️ {n_descartadas} span(s) sin calificación válida del judge, se omiten del log.")

    if calificaciones_df.empty:
        print("⚠️ Ningún span tuvo una calificación válida del LLM-judge.")
        return None

    Client().spans.log_span_annotations_dataframe(dataframe=calificaciones_df)

    promedio = pd.to_numeric(
        calificaciones.get("calificacion_explicacion.label", pd.Series(dtype=float)),
        errors="coerce",
    ).mean()
    return promedio


# =====================================================================
# 9. ORQUESTADOR PRINCIPAL
# =====================================================================
def ejecutar_pruebas_de_evaluacion():
    marca_inicio = datetime.now(timezone.utc)

    dataset = construir_dataset_de_prueba(RUTA_CSV_CRUDO, N_CASOS_EVALUACION)
    df_resultados = ejecutar_agente_sobre_dataset(dataset)

    reporte = {}
    reporte["accuracy_clasificacion"] = calcular_criterio_a(df_resultados)

    criterio_b = calcular_criterio_b(df_resultados)
    reporte["accuracy_accion_llm"] = criterio_b["accuracy"]
    reporte["cobertura_extraccion_accion"] = criterio_b["cobertura_extraccion"]

    reporte["cobertura_criticos"] = calcular_criterio_d(df_resultados)

    score_c, ruta_revision = calcular_criterio_c(df_resultados)
    reporte["calidad_explicacion_heuristica"] = score_c

    print("\n⚖️ Ejecutando LLM-as-judge sobre las trazas de Phoenix...")
    reporte["llm_as_judge"] = calcular_criterio_e(marca_inicio)

    # --- Reporte final ---
    print("\n" + "=" * 70)
    print("📊 RESULTADOS DE EVALUACIÓN (vs. umbrales del README, sección 6)")
    print("=" * 70)
    print(f"A) Accuracy de clasificación (regla pura): "
          f"{reporte['accuracy_clasificacion']:.1f}%  (umbral > {UMBRALES['accuracy_clasificacion']}%)")
    print(f"B) Accuracy de acción LLM: "
          f"{reporte['accuracy_accion_llm']:.1f}%  (umbral > {UMBRALES['accuracy_accion_llm']}%) "
          f"[extracción exitosa en {reporte['cobertura_extraccion_accion']:.1f}% de los casos]")
    cob = reporte['cobertura_criticos']
    cob_str = f"{cob:.1f}%" if isinstance(cob, (int, float)) else cob
    print(f"D) Cobertura de POs críticos: {cob_str}  (umbral > {UMBRALES['cobertura_criticos']}%)")
    print(f"C) Calidad de explicación (proxy heurístico /5): "
          f"{reporte['calidad_explicacion_heuristica']:.1f}  (umbral > {UMBRALES['calidad_explicacion']}) "
          f"-- revisar manualmente: {ruta_revision}")
    if reporte["llm_as_judge"] is not None:
        print(f"E) LLM-as-judge (stretch /5): "
              f"{reporte['llm_as_judge']:.1f}  (umbral > {UMBRALES['llm_as_judge']})")
    else:
        print("E) LLM-as-judge: no se pudo calcular (sin spans de LLM).")

    # --- Data artifact final (sección 9 del README) ---
    ruta_salida = "resultados_evaluacion.csv"
    df_resultados.drop(columns=["llm_output"]).to_csv(
        ruta_salida.replace(".csv", "_resumen.csv"), index=False
    )
    df_resultados.to_csv(ruta_salida, index=False)
    print(f"\n💾 Resultados completos guardados en: {ruta_salida}")

    print("\n🔗 Trazas completas en: http://localhost:6006")
    input("Presiona Enter para finalizar y cerrar Phoenix...")

    return reporte, df_resultados


if __name__ == "__main__":
    ejecutar_pruebas_de_evaluacion()
