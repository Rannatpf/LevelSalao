"""
ALERTS MODULE
Sistema de alertas críticos e recomendações de IA
"""

import pandas as pd


def gerar_alertas_criticos(df):
    """
    Análise de dados e geração de alertas críticos
    
    Args:
        df (pd.DataFrame): DataFrame com dados de leads
    
    Returns:
        list: Lista de dicionários com alertas
    """
    alertas_list = []
    
    if len(df) == 0:
        return alertas_list

    # Conversão geral baixa
    conv_geral = df['is_faturado'].mean() * 100 if len(df) > 0 else 0
    if conv_geral < 10:
        alertas_list.append({
            'tipo': '🟠 AVISO',
            'titulo': 'Conversão Geral Baixa',
            'desc': f'Taxa de {conv_geral:.1f}% abaixo de 10%. Intensifique follow-up.',
            'prioridade': 1
        })

    # Leads qualificados parados
    if 'is_qualificado' in df.columns:
        qualificados_nao_faturados = df[(df['is_qualificado'] == 1) & (df['is_faturado'] == 0)]
        if len(qualificados_nao_faturados) >= 8:
            alertas_list.append({
                'tipo': '🔴 CRÍTICO',
                'titulo': 'Fila de Qualificados em Aberto',
                'desc': f'{len(qualificados_nao_faturados)} leads qualificados ainda sem faturamento. Priorize os contatos mais quentes.',
                'prioridade': 0
            })

    # Lag alto
    if 'Dias_Lag' in df.columns:
        lag_medio = df[df['is_faturado'] == 1]['Dias_Lag'].dropna().mean()
        if pd.notna(lag_medio) and lag_medio > 7:
            alertas_list.append({
                'tipo': '🟡 ATENÇÃO',
                'titulo': 'Ciclo de Venda Lento',
                'desc': f'Lag médio de {lag_medio:.0f} dias até o faturamento. Ajuste cadência de follow-up.',
                'prioridade': 2
            })
    
    # Análise por canal
    for canal in df['Origem'].fillna('Desconhecida').unique():
        df_canal = df[df['Origem'] == canal]
        if len(df_canal) >= 5:
            taxa_conv = df_canal['is_faturado'].mean() * 100
            if taxa_conv < 5:
                alertas_list.append({
                    'tipo': '🟡 ATENÇÃO',
                    'titulo': f'Canal {canal}: Conversão Baixa',
                    'desc': f'Taxa de apenas {taxa_conv:.1f}%. Revise estratégia.',
                    'prioridade': 2
                })
    
    return sorted(alertas_list, key=lambda x: x['prioridade'])


def gerar_recomendacoes_ia(df):
    """
    Gera recomendações baseadas em análise de dados
    
    Args:
        df (pd.DataFrame): DataFrame com dados de leads
    
    Returns:
        list: Lista de recomendações estratégicas
    """
    recomendacoes = []
    
    if len(df) == 0:
        return recomendacoes
    
    # Recomendação 1: Priorizar melhor canal
    try:
        melhor_canal = df.groupby('Origem')['is_faturado'].mean().idxmax()
        melhor_taxa = df.groupby('Origem')['is_faturado'].mean().max() * 100
        
        if melhor_taxa > 15:
            recomendacoes.append({
                'titulo': f'📈 Priorize {melhor_canal}',
                'acao': f'Taxa {melhor_taxa:.1f}%. Aumente investimento aqui.',
                'impacto': '💰 Alto'
            })
    except:
        pass

    # Recomendação 1b: Replicar profissionais que convertem mais
    try:
        if 'Profissional' in df.columns:
            melhor_prof = df.groupby('Profissional')['is_faturado'].mean().idxmax()
            melhor_prof_taxa = df.groupby('Profissional')['is_faturado'].mean().max() * 100
            if melhor_prof_taxa > 15:
                recomendacoes.append({
                    'titulo': f'✂️ Replicar padrão de {melhor_prof}',
                    'acao': f'Esse profissional converte {melhor_prof_taxa:.1f}%. Use-o como referência de abordagem.',
                    'impacto': '💰 Alto'
                })
    except:
        pass
    
    # Recomendação 2: Qualificação baixa
    try:
        taxa_qualif = df['is_qualificado'].mean() * 100
        if taxa_qualif < 30:
            recomendacoes.append({
                'titulo': f'🎯 Melhore Qualificação',
                'acao': f'Apenas {taxa_qualif:.1f}% dos leads qualificados. Revise critérios.',
                'impacto': '⚠️ Médio'
            })
    except:
        pass

    # Recomendação 2b: Reduzir lead time
    try:
        if 'Dias_Lag' in df.columns:
            lag_medio = df[df['is_faturado'] == 1]['Dias_Lag'].dropna().mean()
            if pd.notna(lag_medio) and lag_medio > 7:
                recomendacoes.append({
                    'titulo': f'⏳ Encurte o ciclo de venda',
                    'acao': f'Lag médio de {lag_medio:.0f} dias. Use follow-up mais agressivo nas primeiras 72 horas.',
                    'impacto': '📅 Médio'
                })
    except:
        pass
    
    # Recomendação 3: Lag alto (muitos dias até venda)
    try:
        if 'Dias_Lag' in df.columns:
            df_vendas = df[df['is_faturado'] == 1]
            if len(df_vendas) > 0:
                lag_medio = df_vendas['Dias_Lag'].dropna().mean()
                if lag_medio > 7:
                    recomendacoes.append({
                        'titulo': f'⏰ Acelere Conversões',
                        'acao': f'Lag médio de {lag_medio:.0f} dias. Aumente follow-up.',
                        'impacto': '📅 Médio'
                    })
    except:
        pass
    
    return recomendacoes


def calcular_receita_pendente(df, ticket_medio):
    """
    Calcula receita em aberto (leads qualificados não faturados)
    
    Args:
        df (pd.DataFrame): DataFrame com dados
        ticket_medio (float): Ticket médio do período
    
    Returns:
        float: Receita pendente estimada
    """
    leads_pendentes = len(df[(df['is_qualificado'] == 1) & (df['is_faturado'] == 0)])
    return leads_pendentes * ticket_medio
