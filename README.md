# Vendor Fill Rate Performance Analyzer

> **MAS Mentor Project — Supply Chain AI**
> Agente que detecta, clasifica y explica excepciones en Purchase Orders de vendors — combinando **reglas de negocio + LLM** — y recomienda la acción correcta (Vendor Outreach vs Escalate to Merchant).

---

## 1. ¿Por qué este proyecto?

CVS recibe **miles de Purchase Orders** de vendors cada semana. Cuando un vendor no entrega el 100% de lo ordenado o llega tarde, se genera una excepción que puede causar:

- **Desabasto en tiendas** (out-of-stock).
- **Pérdida de ventas**.
- Fricción con el equipo de compras (merchant).

El problema:

- El equipo de supply chain **no puede revisar manualmente** cada PO con excepción.
- Las reglas existen, pero **solo producen flags** — no explicaciones accionables.
- El buyer necesita saber **exactamente qué acción tomar y por qué**.
- Hoy la decisión es manual, subjetiva y lenta.

Este agente automatiza la triage: clasifica cada PO, explica el problema en lenguaje natural, y recomienda la acción correcta justificada con datos del SKU, vendor e inventario.

---

## 2. Umbrales de excepción

| Métrica | Umbral | Significado |
|---|---|---|
| `FILL_RATE` | < 85% | El vendor no entregó suficiente de lo ordenado |
| `RECEIPT_DELAY_DAYS` | > 5 días | El PO llegó tarde respecto a la fecha solicitada |

Combinando ambos se obtienen 4 tipos:

```
late_only    : RECEIPT_DELAY_DAYS > 5  AND  FILL_RATE >= 85
low_fill     : FILL_RATE         < 85  AND  RECEIPT_DELAY_DAYS <= 5
both         : FILL_RATE         < 85  AND  RECEIPT_DELAY_DAYS > 5   (crítico)
clean        : FILL_RATE        >= 85  AND  RECEIPT_DELAY_DAYS <= 5
```

---

## 3. El dataset

**Archivo:** [`vendor_fill_rate_synthetic.csv`](vendor_fill_rate_synthetic.csv)

- **400 POs sintéticos**
- **54 columnas** (PO, vendor, SKU, DC, fill rate actual + histórico, retraso, inventario, DNP, margen, causa raíz, acción label)
- **12 vendors** · **10 DCs**

### Mix de escenarios

| Escenario | % aprox |
|---|---|
| Solo retraso en entrega | ~25% |
| Bajo fill rate | ~30% |
| Ambos problemas (crítico) | ~20% |
| PO limpio (sin excepción) | ~25% |

### Diccionario de palabras clave

´SKU´: Stock Keeping Unit (Unidad de Mantenimiento de Stock)

### Diccionario de campos clave

| Campo | Descripción |
|---|---|
| `PO_NBR` | Identificador del Purchase Order |
| `VENDOR_NAME`, `VENDOR_NBR` | Quién suministra |
| `SKU_NBR`, `DC_ID` | Qué producto, a qué DC |
| `FILL_RATE` | % recibido vs ordenado — umbral 85% |
| `FILL_RATE_WK_1..7` | Historial 7 semanas para tendencia |
| `RECEIPT_DELAY_DAYS` | Días de retraso — flag si > 5 |
| `AVG_FILL_RATE_4WK`, `AVG_FILL_RATE_8WK` | Tendencia de fill rate |
| `DC_BOH`, `STORE_BOH`, `TOTAL_WOS` | Inventario disponible (Balance On Hand, Weeks Of Supply) |
| `OOS_LIKELY`, `LATE_ISSUE` | Flags de riesgo ya calculados |
| `DNP_RANKING`, `SKU_AVG_MARGIN` | Importancia y rentabilidad del SKU |
| `NEW_ISSUE_FLAG` | ¿Es un problema nuevo o recurrente? |
| `STORE_COUNT` | Cuántas tiendas afectadas |
| `COMBINED_CAUSE` | Causa raíz — contexto para el LLM |
| `COMBINED_ACTION` | **Label real** — para evaluar el output del LLM |

> `COMBINED_ACTION` es el ground truth. **No** se le muestra al LLM — solo se usa para medir si el LLM tomó la decisión correcta.

---

## 4. Reglas y factores de escalamiento

### Reglas base por tipo

| Tipo | Condición | Acción sugerida |
|---|---|---|
| **Late only** | delay > 5 AND fill >= 85 | Vendor Outreach — rastrear embarque, prevenir recurrencia |
| **Low fill rate** | fill < 85 AND delay <= 5 | Vendor Outreach **o** Escalate (según DNP_RANKING y OOS_LIKELY) |
| **Both (crítico)** | fill < 85 AND delay > 5 | Escalate to Merchant — riesgo alto de OOS |
| **Clean** | fill >= 85 AND delay <= 5 | Sin excepción — usar como caso negativo en evaluación |

### Factores de escalamiento (suben prioridad a "Escalate")

- **`DNP_RANKING` Top 10%** — SKU de alta rentabilidad: escalar si hay riesgo OOS.
- **`OOS_LIKELY = Y`** — Desabasto inminente: prioridad máxima independiente del fill rate.
- **`AVG_FILL_RATE_8WK < 80`** — Problema recurrente: el LLM debe mencionarlo explícitamente.
- **`STORE_COUNT > 100`** — Impacto en muchas tiendas: aumenta urgencia.
- **`NEW_ISSUE_FLAG`** — Nuevo vs recurrente cambia el tono de la recomendación.

> **Tip de implementación:** primero implementar las reglas en Python puro (sin LLM) y verificar que la clasificación coincide con `COMBINED_ACTION` en ≥75% de los casos antes de integrar el LLM.

---

## 5. Prompt del LLM (template de referencia)

```text
### System
Eres un analista de supply chain experto en vendor compliance.
Tu objetivo es explicar excepciones de Purchase Orders de forma clara
y recomendar la acción correcta.

### User
Analiza esta excepción de PO:

Vendor: {VENDOR_NAME}
PO: {PO_NBR} | SKU: {SKU_NBR} | DC: {DC_ID}
Categoría: {CATEGORY} | Importancia: {DNP_RANKING}

Fill Rate actual:  {FILL_RATE}%
Promedio 4 sem:    {AVG_FILL_RATE_4WK}%
Retraso:           {RECEIPT_DELAY_DAYS} días
Riesgo OOS:        {OOS_LIKELY}
WOS total:         {TOTAL_WEEKS_OF_SUPPLY} semanas
Causa raíz:        {COMBINED_CAUSE}

Genera:
  (1) explicación del problema en 2-3 oraciones
  (2) acción recomendada con justificación
```

El output del LLM debe:

- Identificar claramente si es **fill rate**, **retraso** o **ambos**.
- Mencionar el impacto en inventario (WOS, OOS risk).
- Referenciar si es un problema **recurrente o nuevo**.
- Elegir entre **Vendor Outreach** o **Escalate to Merchant**.
- Justificar la acción según DNP ranking y margen.
- Tono profesional, máximo 4 oraciones.

---

## 6. Criterios de evaluación

| Dimensión | Cómo medirla | Umbral | Tipo |
|---|---|---|---|
| **Accuracy de clasificación** | % de POs donde tu tipo (late/low fill/both/clean) coincide con los flags del CSV | > 80% | Requerido |
| **Accuracy de acción LLM** | % de POs donde el LLM elige la misma acción que `COMBINED_ACTION` | > 70% | Requerido |
| **Calidad de explicación** | Rúbrica manual en 20 POs: ¿menciona causa, impacto y justifica acción? | 4/5 puntos | Requerido |
| **Cobertura de POs críticos** | Top 10% DNP con OOS=Y: % clasificados correctamente | > 90% | Requerido |
| **LLM-as-judge** | Segundo call al LLM califica explicación (correcta, clara, accionable, 0-5) | > 3.5 / 5 | Stretch |

---

## 7. Timeline sugerido

| Semana | Foco |
|---|---|
| **Sem 1** | Setup y exploración. Cargar el CSV, EDA (distribución de fill rates, causas frecuentes, top vendors), definir reglas en papel. |
| **Sem 2** | Clasificación por reglas. Implementar la lógica Python. Verificar accuracy vs `COMBINED_ACTION`. Ajustar umbrales. |
| **Sem 3** | Integración del LLM. Diseñar prompt, conectar Claude API, generar explicaciones para todos los POs. Primera evaluación. |
| **Sem 4** | Evaluación y refinamiento. Medir métricas, iterar prompt, documentar hallazgos, preparar presentación final. |

---

## 8. Stack técnico sugerido

- **pandas** — cargar el CSV y aplicar reglas de clasificación.
- **Claude API (`claude-sonnet-4-6`)** — generar explicaciones y recomendaciones.
- **Python dicts / JSON** — estructurar el output del LLM.
- **Jupyter Notebook** — exploración y documentación iterativa.
- **GitHub** — versionado y entrega.

> **No se necesita Snowflake.** Todo corre localmente con el CSV sintético. La arquitectura de producción usa las mismas reglas y prompt — la única diferencia es que la data viene de una query a Snowflake.

---

## 9. Entregables

1. **Presentación final** — slides + demo (en vivo o video). Mostrar el pipeline completo corriendo sobre el dataset.
2. **Repositorio de código** — estructurado, con README. Incluye script de clasificación, llamada al LLM y evaluación.
3. **Documentación técnica** — metodología: qué reglas se definieron, por qué, diseño del prompt e iteraciones.
4. **Data artifacts** — CSV de input + CSV de output con `PO_NBR`, clasificación, explicación del LLM y acción recomendada.
5. **Resultados de evaluación** — tabla con accuracy de clasificación, accuracy de acción, score de explicación.
6. **Hallazgos y recomendaciones** — qué aprendieron, dónde falla el LLM, mejoras al prompt, qué harían diferente en producción.

---

## 10. Contenido de este repo

| Archivo | Descripción |
|---|---|
| [`README.md`](README.md) | Este documento |
| [`vendor_fill_rate_synthetic.csv`](vendor_fill_rate_synthetic.csv) | Dataset sintético — 400 POs, 54 columnas, labels incluidos |
| [`kickoff_vendor_fill_rate.html`](kickoff_vendor_fill_rate.html) | Presentación de kickoff (ES) |
| [`kickoff_vendor_fill_rate_en.html`](kickoff_vendor_fill_rate_en.html) | Presentación de kickoff (EN) |

---

**Mentor:** Supply Chain AI — MAS Team
**Modelo sugerido:** `claude-sonnet-4-6`
