import pandas as pd

def limpiar_dataset(ruta_entrada, ruta_salida):
    
    df = pd.read_csv(ruta_entrada)

    # Columnas utilizadas (se pueden modificar)
    columnas = [
        "VENDOR_NAME", "SKU_NBR", "DC_ID", "CATEGORY",
        "DNP_RANKING", "FILL_RATE", "TOTAL_WEEKS_OF_SUPPLY",
        "RECEIPT_DELAY_DAYS", "OOS_LIKELY", "FILL_RATE_ISSUE",
        "AVG_FILL_RATE_4WK", "AVG_RECEIPT_DELAY_4WK",
        "AVG_FILL_RATE_8WK", "AVG_RECEIPT_DELAY_8WK",
        "STORE_COUNT", "COMBINED_CAUSE"
    ]
    df = df[columnas]

    # Estandariza texto
    df["COMBINED_CAUSE"] = df["COMBINED_CAUSE"].str.strip()

    df.to_csv(ruta_salida, index=False)

if __name__ == "__main__":
    limpiar_dataset(
        "src/vendor_fill_rate_synthetic.csv",
        "src/vendor_fill_rate_clean.csv"
    )