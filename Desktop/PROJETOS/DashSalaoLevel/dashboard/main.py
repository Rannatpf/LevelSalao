import streamlit as st
import pandas as pd
import requests

# ============================================
# CONFIGURAÇÃO
# ============================================
st.set_page_config(
    page_title="Dashboard de Performance",
    layout="wide"
)

# 🔥 TROQUE PELA URL DO CLOUD RUN
API_URL = "https://SUA-URL-DO-CLOUD-RUN/data"


# ============================================
# FUNÇÃO DE CARGA DE DADOS
# ============================================
@st.cache_data(ttl=300)
def carregar_dados():
    try:
        response = requests.get(API_URL, timeout=10)
        data = response.json()

        if isinstance(data, dict) and "erro" in data:
            st.error(f"Erro da API: {data['erro']}")
            return pd.DataFrame()

        return pd.DataFrame(data)

    except Exception as e:
        st.error(f"Erro ao conectar API: {e}")
        return pd.DataFrame()


# ============================================
# HEADER
# ============================================
st.title("📊 Dashboard de Performance")
st.caption("Análise de leads, conversões e faturamento")

# ============================================
# LOAD DATA
# ============================================
df = carregar_dados()

if df.empty:
    st.warning("⚠️ Nenhum dado carregado")
    st.stop()


# ============================================
# TRATAMENTO BÁSICO
# ============================================
if "Faturamento" in df.columns:
    df["Faturamento"] = pd.to_numeric(df["Faturamento"], errors="coerce")

if "is_faturado" not in df.columns:
    df["is_faturado"] = df["Faturamento"].fillna(0) > 0


# ============================================
# KPIs
# ============================================
total_leads = len(df)
total_vendas = df["is_faturado"].sum()
faturamento_total = df["Faturamento"].sum()
ticket_medio = faturamento_total / total_vendas if total_vendas > 0 else 0
taxa_conv = (total_vendas / total_leads) * 100 if total_leads > 0 else 0

col1, col2, col3, col4 = st.columns(4)

col1.metric("Leads", total_leads)
col2.metric("Vendas", int(total_vendas))
col3.metric("Conversão", f"{taxa_conv:.1f}%")
col4.metric("Faturamento", f"R$ {faturamento_total:,.2f}")


st.divider()

# ============================================
# FILTROS
# ============================================
if "Origem" in df.columns:
    canais = st.multiselect(
        "Filtrar por Origem",
        options=df["Origem"].dropna().unique(),
        default=df["Origem"].dropna().unique()
    )
    df = df[df["Origem"].isin(canais)]


# ============================================
# GRÁFICOS
# ============================================
st.subheader("📊 Faturamento por Origem")

if "Origem" in df.columns:
    agrupado = (
        df.groupby("Origem")["Faturamento"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )

    st.bar_chart(agrupado.set_index("Origem"))


st.subheader("🎯 Conversão por Origem")

if "Origem" in df.columns:
    conv = (
        df.groupby("Origem")["is_faturado"]
        .mean()
        .sort_values(ascending=False)
        .reset_index()
    )

    conv["is_faturado"] = conv["is_faturado"] * 100

    st.bar_chart(conv.set_index("Origem"))


# ============================================
# TABELA
# ============================================
st.subheader("📋 Dados Detalhados")
st.dataframe(df, use_container_width=True)