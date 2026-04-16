"""
DATA PROCESSING MODULE
Funções de carregamento, limpeza, filtros e cálculos de dados
"""

import streamlit as st
import pandas as pd
import gspread
import requests
import json
import os
import re
from datetime import date, datetime
from pathlib import Path
from google.oauth2.service_account import Credentials

from .config import (
    GOOGLE_SHEETS_CREDENTIALS_PATH, 
    GOOGLE_SHEETS_CREDENTIALS_JSON,
    GOOGLE_SHEETS_ID, 
    CACHE_TTL
)
from .logger import logger, LogContext, log_erro, log_info

API_URL = os.getenv("API_URL", "https://sheet-api-6826756112.us-central1.run.app/data")


def _streamlit_secrets_exist():
    project_root = Path(__file__).resolve().parent.parent
    candidate_paths = [
        Path.home() / ".streamlit" / "secrets.toml",
        project_root / ".streamlit" / "secrets.toml",
    ]
    return any(path.exists() for path in candidate_paths)


def formatar_moeda_br(valor):
    """
    Formata valor em padrão brasileiro: R$ 1.234,56
    
    Args:
        valor (float): Valor a formatar
    
    Returns:
        str: Valor formatado em padrão BR
    """
    if valor == 0:
        return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(",", "|").replace(".", ",").replace("|", ".")


def _parse_currency_br(value):
    if pd.isna(value):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    digits = re.sub(r"[^\d,.-]", "", str(value))
    if not digits:
        return 0.0
    normalized = digits.replace(".", "").replace(",", ".")
    try:
        return float(normalized)
    except ValueError:
        return 0.0


def _parse_contact_date(value):
    """Converte 'Data de contato' no formato brasileiro dd/mm/aaaa para Timestamp."""
    if pd.isna(value):
        return pd.NaT

    # Já é datetime/Timestamp
    if isinstance(value, pd.Timestamp):
        ts = value
    elif isinstance(value, datetime):
        ts = pd.Timestamp(value)
    elif isinstance(value, date):
        ts = pd.Timestamp(value)
    else:
        ts = None

    if ts is not None:
        if ts.year < 2025 or ts.year > 2030:
            return pd.NaT
        return ts.normalize()

    # Serial do Google Sheets (número inteiro representando data)
    if isinstance(value, (int, float)) and not pd.isna(value):
        serial = int(value)
        if 30000 <= serial <= 60000:
            ts = (pd.Timestamp("1899-12-30") + pd.to_timedelta(serial, unit="D")).normalize()
            if ts.year < 2025 or ts.year > 2030:
                return pd.NaT
            return ts

    raw = re.sub(r"\s+", "", str(value).strip())
    if not raw:
        return pd.NaT

    # Formato principal: dd/mm/aaaa ou dd-mm-aaaa
    match = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})$", raw)
    if match:
        day = int(match.group(1))
        month = int(match.group(2))
        year = int(match.group(3))

        if year < 100:
            year = 2000 + year

        if year < 2025 or year > 2030:
            return pd.NaT
        if not (1 <= month <= 12 and 1 <= day <= 31):
            return pd.NaT

        try:
            return pd.Timestamp(year=year, month=month, day=day)
        except ValueError:
            return pd.NaT

    # Formato incompleto: dd/mm (sem ano) — inferir ano
    match = re.match(r"^(\d{1,2})[/-](\d{1,2})$", raw)
    if match:
        day = int(match.group(1))
        month = int(match.group(2))

        if not (1 <= month <= 12 and 1 <= day <= 31):
            return pd.NaT

        year = 2025 if month >= 11 else 2026

        try:
            return pd.Timestamp(year=year, month=month, day=day)
        except ValueError:
            return pd.NaT

    # Fallback genérico (dayfirst para formato BR)
    parsed = pd.to_datetime(raw, errors="coerce", dayfirst=True)
    if not pd.isna(parsed):
        ts = pd.Timestamp(parsed).normalize()
        if ts.year < 2025 or ts.year > 2030:
            return pd.NaT
        return ts

    return pd.NaT


# Ordem cronológica dos meses na planilha (nov/2025 em diante)
_ORDEM_MESES = [
    "Novembro", "Dezembro",
    "Janeiro", "Fevereiro", "Março", "Abril",
    "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro",
]

# Mapa de normalização: variantes encontradas na planilha → nome canônico
_NORMALIZE_MES = {
    "novembro": "Novembro",
    "dezembro": "Dezembro",
    "janeiro": "Janeiro",
    "fevereiro": "Fevereiro",
    "março": "Março",
    "marco": "Março",
    "abril": "Abril",
    "maio": "Maio",
    "junho": "Junho",
    "julho": "Julho",
    "agosto": "Agosto",
    "setembro": "Setembro",
    "outubro": "Outubro",
}


def _normalizar_mes(valor):
    """Normaliza nomes de meses: remove espaços, acentos inconsistentes, capitaliza."""
    if pd.isna(valor):
        return valor
    chave = str(valor).strip().lower()
    return _NORMALIZE_MES.get(chave, str(valor).strip().title())


# URL CSV direto do Google Sheets (fallback sem credenciais)
_CSV_EXPORT_URL = (
    f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}"
    f"/gviz/tq?tqx=out:csv&sheet=Contatos"
)


@st.cache_data(ttl=CACHE_TTL)
def carregar_dados_mestre():
    """
    Carrega e processa dados do Google Sheets com validação
    
    Returns:
        pd.DataFrame: DataFrame processado com colunas calculadas
        None: Se houver erro no carregamento
    """
    try:
        log_info("Iniciando carregamento de dados da Google Sheets")
        
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        creds = None
        creds_source = None
        
        # Prioridade 1: Streamlit Secrets (gcp_service_account) - PRODUÇÃO
        secrets_available = _streamlit_secrets_exist()
        streamlit_secrets = None
        if secrets_available:
            try:
                streamlit_secrets = st.secrets
            except Exception as e:
                log_info(f"⚠ Streamlit Secrets indisponível: {e}")

        try:
            if streamlit_secrets and 'gcp_service_account' in streamlit_secrets:
                creds = Credentials.from_service_account_info(
                    streamlit_secrets["gcp_service_account"],
                    scopes=scope
                )
                creds_source = "Streamlit Secrets"
                log_info(f"✓ Credenciais carregadas de {creds_source}")
        except Exception as e:
            log_info(f"⚠ Streamlit Secrets falhou: {e}")
        
        # Prioridade 2: Variável de ambiente com JSON string
        if creds is None and GOOGLE_SHEETS_CREDENTIALS_JSON:
            try:
                creds_info = json.loads(GOOGLE_SHEETS_CREDENTIALS_JSON)
                creds = Credentials.from_service_account_info(creds_info, scopes=scope)
                creds_source = "Variável GOOGLE_SHEETS_CREDENTIALS_JSON"
                log_info(f"✓ Credenciais carregadas de {creds_source}")
            except Exception as e:
                log_info(f"⚠ JSON de ambiente falhou: {e}")
        
        # Prioridade 3: Arquivo local credentials.json - TESTE LOCAL
        if creds is None and os.path.exists(GOOGLE_SHEETS_CREDENTIALS_PATH):
            try:
                creds = Credentials.from_service_account_file(
                    GOOGLE_SHEETS_CREDENTIALS_PATH, 
                    scopes=scope
                )
                creds_source = "Arquivo local (credentials.json)"
                log_info(f"✓ Credenciais carregadas de {creds_source}")
            except Exception as e:
                log_info(f"⚠ Arquivo local falhou: {e}")
        
        # ERRO: Nenhuma fonte de credenciais funcionou
        if creds is None:
            log_info("Nenhuma credencial local encontrada. Usando CSV direto do Google Sheets como fallback.")

            try:
                import io
                response = requests.get(_CSV_EXPORT_URL, timeout=60)
                if response.status_code != 200:
                    st.error(f"Erro ao acessar planilha: {response.status_code}")
                    return None

                df = pd.read_csv(io.StringIO(response.text))
                # Normalizar nomes de colunas (remover espaços)
                df.columns = [str(col).strip() for col in df.columns]
                # Manter apenas as 11 colunas principais
                colunas_esperadas = [
                    'Mês', 'Data de contato', 'Nome', 'Whatsapp', 'Origem',
                    'Status', 'Qualificação', 'Data do Faturamento', 'Serviço',
                    'Profissional', 'Faturamento'
                ]
                colunas_presentes = [c for c in colunas_esperadas if c in df.columns]
                df = df[colunas_presentes].copy()

                # Normalizar coluna Mês
                if 'Mês' in df.columns:
                    df['Mês'] = df['Mês'].apply(_normalizar_mes)

                # Remover linhas sem nome (linhas vazias da planilha)
                if 'Nome' in df.columns:
                    df = df.dropna(subset=['Nome'])
                    df = df[df['Nome'].astype(str).str.strip() != ''].copy()

                coluna_data_contato = next((c for c in ['Data de contato', 'Data de Contato', 'Data'] if c in df.columns), None)
                coluna_data_fat = next((c for c in ['Data do Faturamento', 'Data do faturamento'] if c in df.columns), None)

                if coluna_data_contato:
                    df['Data_Ref'] = df[coluna_data_contato].apply(_parse_contact_date)
                else:
                    df['Data_Ref'] = pd.NaT

                if coluna_data_fat:
                    df['Data_Fat'] = df[coluna_data_fat].apply(_parse_contact_date)

                df = df.dropna(subset=['Data_Ref'])
                df = df.sort_values('Data_Ref')

                if 'Faturamento' in df.columns:
                    df['Faturamento_Num'] = df['Faturamento'].apply(_parse_currency_br)
                else:
                    df['Faturamento_Num'] = 0.0

                if 'Status' in df.columns:
                    status_normalizado = df['Status'].astype(str).str.lower().str.strip()
                    df['is_faturado'] = status_normalizado.eq('faturado')
                    df['is_qualificado'] = status_normalizado.isin(['qualificado', 'faturado', 'agendamento realizado', 'em andamento'])
                else:
                    df['is_faturado'] = 0
                    df['is_qualificado'] = 0

                if 'Qualificação' in df.columns:
                    qualificacao_normalizada = df['Qualificação'].astype(str).str.lower().str.strip()
                    df['is_qualificado'] = qualificacao_normalizada.eq('qualificado') | df.get('is_qualificado', False)

                df = df[df['Origem'] != 'Mídia Offline'].copy()

                if 'Data_Fat' in df.columns and 'Data_Ref' in df.columns:
                    try:
                        df['Dias_Lag'] = (df['Data_Fat'] - df['Data_Ref']).dt.days
                        df['Dias_Lag'] = df['Dias_Lag'].apply(lambda value: max(0, value) if pd.notna(value) else None)
                    except Exception:
                        df['Dias_Lag'] = None

                if df.empty:
                    base_columns = [
                        'Data_Ref', 'Faturamento_Num', 'is_faturado', 'is_qualificado', 'Dias_Lag'
                    ]
                    for column in base_columns:
                        if column not in df.columns:
                            df[column] = pd.Series(dtype='object')

                log_info(f"✓ Dados carregados via CSV direto: {len(df)} linhas")
                return df

            except Exception as e:
                error_msg = (
                    f"❌ Nenhuma fonte de credenciais disponível e o fallback da API falhou!\n\n"
                    f"**Diagnóstico:**\n"
                    f"- Streamlit Secrets config: {'✓ Detectado' if streamlit_secrets and 'gcp_service_account' in streamlit_secrets else '✗ Não encontrado'}\n"
                    f"- Env var GOOGLE_SHEETS_CREDENTIALS_JSON: {'✓ Configurado' if GOOGLE_SHEETS_CREDENTIALS_JSON else '✗ Vazio'}\n"
                    f"- Arquivo {GOOGLE_SHEETS_CREDENTIALS_PATH}: {'✓ Existe' if os.path.exists(GOOGLE_SHEETS_CREDENTIALS_PATH) else '✗ Não existe'}\n"
                    f"- API_URL: {API_URL}\n\n"
                    f"**Erro do fallback:** {str(e)}"
                )
                log_erro(error_msg)
                st.error(error_msg)
                return None
        
        try:
            client = gspread.authorize(creds)
            sheet = client.open_by_key(GOOGLE_SHEETS_ID).get_worksheet(0)
            log_info(f"✓ Conectado ao Google Sheets (ID: {GOOGLE_SHEETS_ID})")
        except Exception as e:
            error_msg = f"❌ Erro ao conectar ao Google Sheets: {str(e)}"
            log_erro(error_msg)
            st.error(error_msg)
            return None
        
        raw_values = sheet.get_all_values()
        df = pd.DataFrame(raw_values[1:], columns=raw_values[0])

        # Normalizar nomes de colunas (remover espaços)
        df.columns = [str(col).strip() for col in df.columns]

        # Limpeza de nomes de colunas duplicados
        cols = []
        count = {}
        for c in df.columns:
            count[c] = count.get(c, 0) + 1
            cols.append(f"{c}_{count[c]}" if count[c] > 1 else c)
        df.columns = cols

        # Normalizar coluna Mês (corrigir minúsculas, espaços, acentos)
        if 'Mês' in df.columns:
            df['Mês'] = df['Mês'].apply(_normalizar_mes)

        # Remover linhas sem nome (linhas vazias da planilha)
        if 'Nome' in df.columns:
            df = df[df['Nome'].astype(str).str.strip() != ''].copy()

        coluna_data_contato = next((c for c in ['Data de contato', 'Data de Contato', 'Data'] if c in df.columns), None)
        coluna_data_fat = next((c for c in ['Data do Faturamento', 'Data do faturamento'] if c in df.columns), None)

        # Processamento de datas: coluna B (Data de contato) é a fonte principal
        if coluna_data_contato:
            df['Data_Ref'] = df[coluna_data_contato].apply(_parse_contact_date)
        else:
            df['Data_Ref'] = pd.NaT

        if df['Data_Ref'].notna().any():
            df = df.dropna(subset=['Data_Ref'])
            df = df.sort_values('Data_Ref')

        # Conversão de valores monetários
        if 'Faturamento' in df.columns:
            df['Faturamento_Num'] = df['Faturamento'].apply(_parse_currency_br)
        else:
            df['Faturamento_Num'] = 0.0
        
        # Colunas booleanas
        if 'Status' in df.columns:
            status_normalizado = df['Status'].astype(str).str.lower().str.strip()
            df['is_faturado'] = status_normalizado.eq('faturado')
            df['is_qualificado'] = status_normalizado.isin(['qualificado', 'faturado', 'agendamento realizado', 'em andamento'])
        else:
            df['is_faturado'] = 0
            df['is_qualificado'] = 0

        if 'Qualificação' in df.columns:
            qualificacao_normalizada = df['Qualificação'].astype(str).str.lower().str.strip()
            df['is_qualificado'] = qualificacao_normalizada.eq('qualificado') | df.get('is_qualificado', False)
        
        # ✅ FILTRO: Remover outlier "Mídia Offline"
        df = df[df['Origem'] != 'Mídia Offline'].copy()
        
        # Análise de Lag (dias até faturamento)
        if coluna_data_fat and 'Data_Ref' in df.columns:
            try:
                df['Data_Fat'] = df[coluna_data_fat].apply(_parse_contact_date)
                df['Dias_Lag'] = (df['Data_Fat'] - df['Data_Ref']).dt.days
                df['Dias_Lag'] = df['Dias_Lag'].apply(lambda x: max(0, x) if pd.notna(x) else None)
            except Exception:
                df['Dias_Lag'] = None

        if df.empty:
            base_columns = [
                'Data_Ref', 'Faturamento_Num', 'is_faturado', 'is_qualificado', 'Dias_Lag'
            ]
            for column in base_columns:
                if column not in df.columns:
                    df[column] = pd.Series(dtype='object')
        
        return df
        
    except Exception as e:
        log_erro(f"Erro ao carregar dados: {str(e)}", exc_info=True)
        st.error(f"❌ Erro ao carregar dados: {str(e)}")
        return None


def calcular_kpis(df):
    """
    Calcula KPIs principais de forma centralizada
    
    Args:
        df (pd.DataFrame): DataFrame com dados de leads
    
    Returns:
        dict: Dicionário com métricas padronizadas
    """
    if df.empty:
        return {
            'leads': 0, 'qualificados': 0, 'conversoes': 0,
            'taxa_qualif': 0, 'taxa_conversao': 0,
            'faturamento_total': 0, 'ticket_medio': 0
        }
    
    leads = len(df)
    qualificados = df['is_qualificado'].sum()
    conversoes = df['is_faturado'].sum()
    faturamento = df['Faturamento_Num'].sum()
    
    taxa_qualif = (qualificados / leads * 100) if leads > 0 else 0
    taxa_conversao = (conversoes / leads * 100) if leads > 0 else 0
    ticket_medio = faturamento / conversoes if conversoes > 0 else 0
    
    return {
        'leads': leads,
        'qualificados': qualificados,
        'conversoes': conversoes,
        'taxa_qualif': taxa_qualif,
        'taxa_conversao': taxa_conversao,
        'faturamento_total': faturamento,
        'ticket_medio': ticket_medio
    }


def criar_filtros(df, chave_unica):
    """Filtros por mês e canal de aquisição."""
    col_f1, col_f2 = st.columns(2)

    # --- Filtro de Mês ---
    if 'Mês' in df.columns:
        meses_na_base = df['Mês'].dropna().astype(str).str.strip()
        meses_na_base = meses_na_base[meses_na_base != ''].unique().tolist()
        meses_ordenados = [m for m in _ORDEM_MESES if m in meses_na_base]
        for m in meses_na_base:
            if m not in meses_ordenados:
                meses_ordenados.append(m)

        meses_sel = col_f1.multiselect(
            'Meses',
            options=meses_ordenados,
            default=meses_ordenados,
            key=f'meses_{chave_unica}',
        )
    else:
        meses_sel = []

    # --- Filtro de Canal ---
    canais_disponiveis = sorted(df['Origem'].fillna('Desconhecida').unique().tolist())
    canais_sel = col_f2.multiselect(
        'Canais de Aquisição',
        options=canais_disponiveis,
        default=canais_disponiveis,
        key=f'canais_{chave_unica}',
    )

    return meses_sel, canais_sel


def construir_df_filtrado(df_raw, meses_selecionados, canais_selecionados):
    """Filtra por mês e canal de aquisição."""
    if df_raw.empty:
        return df_raw.iloc[0:0].copy()

    if not meses_selecionados:
        return df_raw.iloc[0:0].copy()

    # Filtrar pelo nome do mês
    mes_col = df_raw['Mês'].astype(str).str.strip() if 'Mês' in df_raw.columns else pd.Series(dtype=str)
    df_filtrado = df_raw[mes_col.isin(meses_selecionados)].copy()

    if canais_selecionados:
        df_filtrado = df_filtrado[df_filtrado['Origem'].isin(canais_selecionados)].copy()

    return df_filtrado
