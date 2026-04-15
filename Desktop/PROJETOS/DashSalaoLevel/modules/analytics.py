"""
ANALYTICS MODULE
Análises por categoria: canais, profissionais, serviços e lag
"""

import pandas as pd


def analisar_performance_canais(df):
    """
    Análise vetorizada de performance por canal (GROUPBY - Otimizado)
    Em vez de loop for, usa groupby nativo do pandas (~10x mais rápido)
    
    Args:
        df (pd.DataFrame): DataFrame com dados de leads
    
    Returns:
        pd.DataFrame: Estatísticas por canal ordenadas por impacto
    """
    if df.empty:
        return pd.DataFrame()
    
    # ✅ VETORIZADO: groupby em vez de loop
    canal_stats = df.groupby('Origem').agg({
        'is_faturado': ['sum', 'count', 'mean'],
        'Faturamento_Num': ['sum', 'mean']
    }).round(2)
    
    canal_stats.columns = ['Conversoes', 'Leads', 'Taxa_Conv', 'Fat_Total', 'Ticket_Medio']
    canal_stats['Taxa_Conv_Pct'] = canal_stats['Taxa_Conv'] * 100
    canal_stats['Impacto'] = canal_stats['Leads'] * canal_stats['Taxa_Conv']
    
    return canal_stats.sort_values('Impacto', ascending=False).reset_index()


def analisar_profissional(df):
    """
    NOVA ANÁLISE: Performance por Profissional
    Identifica quem converte melhor
    
    Args:
        df (pd.DataFrame): DataFrame com dados de leads
    
    Returns:
        pd.DataFrame: Estatísticas por profissional ou None
    """
    if 'Profissional' not in df.columns or df['Profissional'].isna().all():
        return None
    
    prof_stats = df.groupby('Profissional').agg({
        'is_faturado': ['sum', 'count', 'mean'],
        'Faturamento_Num': ['sum', 'mean']
    }).round(2)
    
    prof_stats.columns = ['Conversoes', 'Leads', 'Taxa_Conv', 'Fat_Total', 'Ticket_Medio']
    prof_stats['Taxa_Conv_Pct'] = prof_stats['Taxa_Conv'] * 100
    
    return prof_stats.sort_values('Conversoes', ascending=False).reset_index()


def analisar_servico(df):
    """
    NOVA ANÁLISE: Performance por Serviço
    Identifica produtos mais vendidos
    
    Args:
        df (pd.DataFrame): DataFrame com dados de leads
    
    Returns:
        pd.DataFrame: Estatísticas por serviço ou None
    """
    if 'Serviço' not in df.columns or df['Serviço'].isna().all():
        return None
    
    df_servico = df[df['is_faturado'] == 1].copy()
    if df_servico.empty:
        return None
    
    servico_stats = df_servico.groupby('Serviço').agg({
        'Faturamento_Num': ['count', 'sum', 'mean']
    }).round(2)
    
    servico_stats.columns = ['Quantidade', 'Faturamento', 'Ticket_Medio']
    
    return servico_stats.sort_values('Faturamento', ascending=False).reset_index()


def calcular_lag_medio(df):
    """
    NOVA ANÁLISE: Dias médios entre contato e faturamento
    Identifica velocidade de conversão
    
    Args:
        df (pd.DataFrame): DataFrame com dados de leads
    
    Returns:
        dict: Estatísticas de lag (média, mediana, min, max, distribuição) ou None
    """
    if 'Dias_Lag' not in df.columns:
        return None
    
    df_faturam = df[df['is_faturado'] == 1].copy()
    if df_faturam.empty:
        return None
    
    lag_valid = df_faturam['Dias_Lag'].dropna()
    if lag_valid.empty:
        return None
    
    return {
        'media': lag_valid.mean(),
        'mediana': lag_valid.median(),
        'min': lag_valid.min(),
        'max': lag_valid.max(),
        'distribuicao': lag_valid
    }
