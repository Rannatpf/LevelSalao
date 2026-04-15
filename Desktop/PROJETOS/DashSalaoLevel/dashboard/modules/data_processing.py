"""
DATA PROCESSING MODULE
Funções de carregamento, limpeza, filtros e cálculos de dados
"""

import streamlit as st
import pandas as pd
import gspread
import json
import os
import re
from pathlib import Path
from google.oauth2.service_account import Credentials

from .config import (
    GOOGLE_SHEETS_CREDENTIALS_PATH, 
    GOOGLE_SHEETS_CREDENTIALS_JSON,
    GOOGLE_SHEETS_ID, 
    CACHE_TTL
)
from .logger import logger, LogContext, log_erro, log_info


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


def _infer_default_year(df):
    for column in ["Data do Faturamento", "Data de contato"]:
        if column in df.columns:
            years = df[column].astype(str).str.extract(r"(\d{4})")[0].dropna()
            if not years.empty:
                return int(years.mode().iloc[0])
    return pd.Timestamp.now().year


def _parse_sheet_date(value, default_year):
    if pd.isna(value):
        return pd.NaT

    text = str(value).strip()
    if not text:
        return pd.NaT

    if re.search(r"\d{4}", text):
        return pd.to_datetime(text, dayfirst=True, errors="coerce")

    return pd.to_datetime(f"{text}/{default_year}", dayfirst=True, errors="coerce")


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
            error_msg = (
                f"❌ Nenhuma fonte de credenciais disponível!\n\n"
                f"**Diagnóstico:**\n"
                f"- Streamlit Secrets config: {'✓ Detectado' if streamlit_secrets and 'gcp_service_account' in streamlit_secrets else '✗ Não encontrado'}\n"
                f"- Env var GOOGLE_SHEETS_CREDENTIALS_JSON: {'✓ Configurado' if GOOGLE_SHEETS_CREDENTIALS_JSON else '✗ Vazio'}\n"
                f"- Arquivo {GOOGLE_SHEETS_CREDENTIALS_PATH}: {'✓ Existe' if os.path.exists(GOOGLE_SHEETS_CREDENTIALS_PATH) else '✗ Não existe'}\n\n"
                f"**Solução para Streamlit Cloud:**\n"
                f"1. Vá para https://share.streamlit.io → seu app → Settings → Secrets\n"
                f"2. Cole toda a estrutura `[gcp_service_account]` com a chave privada\n"
                f"3. Clique em Save\n"
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

        # Limpeza de nomes de colunas duplicados
        cols = []
        count = {}
        for c in df.columns:
            count[c] = count.get(c, 0) + 1
            cols.append(f"{c}_{count[c]}" if count[c] > 1 else c)
        df.columns = cols

        default_year = _infer_default_year(df)

        # Processamento de datas baseado no formato real da planilha
        if 'Data de contato' in df.columns:
            df['Data_Ref'] = df['Data de contato'].apply(lambda value: _parse_sheet_date(value, default_year))
        else:
            df['Data_Ref'] = pd.NaT
        
        def ajustar_ano(dt):
            if pd.isnull(dt): 
                return dt
            return dt.replace(year=2025) if dt.month >= 11 else dt.replace(year=2026)
        
        df['Data_Ref'] = df['Data_Ref'].apply(ajustar_ano)

        if df['Data_Ref'].notna().any():
            df = df.dropna(subset=['Data_Ref'])
            df['Mes_Ano_Label'] = df['Data_Ref'].dt.strftime('%b/%y')
            df['Periodo_Order'] = df['Data_Ref'].dt.to_period('M')
            df = df.sort_values('Data_Ref')
        elif 'Mês' in df.columns:
            df['Mes_Ano_Label'] = df['Mês'].astype(str).str.strip()
            df['Periodo_Order'] = pd.RangeIndex(start=0, stop=len(df), step=1)
        else:
            df['Mes_Ano_Label'] = 'Sem período'
            df['Periodo_Order'] = pd.RangeIndex(start=0, stop=len(df), step=1)

        if 'Mes_Ano_Label' not in df.columns:
            df['Mes_Ano_Label'] = pd.Series(dtype='object')
        if 'Periodo_Order' not in df.columns:
            df['Periodo_Order'] = pd.Series(dtype='period[M]')

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
        if 'Data do Faturamento' in df.columns and 'Data de contato' in df.columns:
            try:
                df['Data_Fat'] = df['Data do Faturamento'].apply(lambda value: _parse_sheet_date(value, default_year))
                df['Dias_Lag'] = (df['Data_Fat'] - df['Data_Ref']).dt.days
                df['Dias_Lag'] = df['Dias_Lag'].apply(lambda x: max(0, x) if pd.notna(x) else None)
            except:
                df['Dias_Lag'] = None

        if df.empty:
            base_columns = [
                'Data_Ref', 'Mes_Ano_Label', 'Periodo_Order', 'Faturamento_Num',
                'is_faturado', 'is_qualificado', 'Dias_Lag'
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


def criar_filtros(df, periodos_list, chave_unica):
    """
    Cria filtros reutilizáveis para período e canais
    Evita duplicação de código entre abas
    
    Args:
        df (pd.DataFrame): DataFrame com dados
        periodos_list (list): Lista de períodos disponíveis
        chave_unica (str): Identificador único para o widget
    
    Returns:
        tuple: (meses_selecionados, canais_selecionados)
    """
    import datetime

    col_f1, col_f2 = st.columns([1, 2])

    # Default: nov/2025 até hoje
    corte = pd.Period('2025-11', 'M')
    hoje = pd.Period(datetime.date.today(), 'M')
    labels_default = periodos_list[-1:]
    try:
        if 'Periodo_Order' in df.columns:
            periodos_map = df[['Periodo_Order', 'Mes_Ano_Label']].drop_duplicates()
            candidatos = periodos_map[
                (periodos_map['Periodo_Order'] >= corte) &
                (periodos_map['Periodo_Order'] <= hoje)
            ]['Mes_Ano_Label'].tolist()
            candidatos = [l for l in candidatos if l in periodos_list]
            if candidatos:
                labels_default = candidatos
    except Exception:
        pass

    meses_sel = col_f1.multiselect(
        "Filtrar Período",
        periodos_list,
        default=labels_default,
        key=f"periodo_{chave_unica}"
    )
    
    canais_disponiveis = sorted(df['Origem'].unique())
    canais_sel = col_f2.multiselect(
        "Canais de Origem",
        canais_disponiveis,
        default=canais_disponiveis,
        key=f"canais_{chave_unica}"
    )
    
    return meses_sel, canais_sel


def construir_df_filtrado(df_raw, periodos_selecionados, canais_selecionados):
    """
    Constrói DataFrame filtrado baseado em período e canais
    Função auxiliar unificada para evitar repetição
    
    Args:
        df_raw (pd.DataFrame): DataFrame bruto/original
        periodos_selecionados (list): Períodos escolhidos
        canais_selecionados (list): Canais escolhidos
    
    Returns:
        pd.DataFrame: DataFrame filtrado
    """
    return df_raw[
        (df_raw['Mes_Ano_Label'].isin(periodos_selecionados)) & 
        (df_raw['Origem'].isin(canais_selecionados))
    ]
