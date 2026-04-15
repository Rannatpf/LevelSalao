from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import google.auth
from googleapiclient.discovery import build
import os

app = FastAPI()

# ============================================
# CORS (permite acesso do Streamlit)
# ============================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # depois você pode restringir
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# CONFIG (via variáveis de ambiente)
# ============================================
SHEET_ID = os.getenv("SHEET_ID", "1YR4uxDsNf-WlODmtUUJDliGETr9LGBqgcTm74YjL-7E")
RANGE_NAME = os.getenv("RANGE_NAME", "Contatos!A1:K1000")


# ============================================
# ROTAS
# ============================================
@app.get("/")
def home():
    return {"status": "API rodando 🚀"}


@app.get("/data")
def get_data():
    try:
        # autenticação automática no Cloud Run
        creds, _ = google.auth.default()
        service = build("sheets", "v4", credentials=creds)

        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=SHEET_ID, range=RANGE_NAME)
            .execute()
        )

        values = result.get("values", [])

        if not values:
            return {"erro": "Planilha vazia"}

        # DataFrame
        df = pd.DataFrame(values[1:], columns=values[0])

        # ============================================
        # TRATAMENTO DE DADOS
        # ============================================
        if "Faturamento" in df.columns:
            df["Faturamento"] = (
                df["Faturamento"]
                .astype(str)
                .str.replace("R$", "", regex=False)
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
            )
            df["Faturamento"] = pd.to_numeric(df["Faturamento"], errors="coerce")

        # colunas úteis (se existirem)
        if "Faturamento" in df.columns:
            df["is_faturado"] = df["Faturamento"].fillna(0) > 0

        if "Qualificação" in df.columns:
            df["is_qualificado"] = df["Qualificação"].notna()

        return df.fillna("").to_dict(orient="records")

    except Exception as e:
        return {"erro": str(e)}


# ============================================
# ENTRYPOINT CLOUD RUN
# ============================================
if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)