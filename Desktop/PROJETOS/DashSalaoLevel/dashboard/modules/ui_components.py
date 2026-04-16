"""
UI COMPONENTS MODULE
Elementos reutilizáveis de interface com Streamlit
"""

import streamlit as st
from .data_processing import formatar_moeda_br


def exibir_kpis_principais(kpis_atu, kpis_ant=None):
    """
    Exibe 4 métricas principais em colunas com deltas
    
    Args:
        kpis_atu (dict): KPIs atuais (leads, taxa_qualif, taxa_conversao, faturamento_total)
        kpis_ant (dict): KPIs do período anterior (opcional, para comparação)
    """
    k1, k2, k3, k4 = st.columns(4)
    
    delta_leads = f"+{kpis_atu['leads'] - kpis_ant['leads']}" if kpis_ant else None
    k1.metric("Leads", kpis_atu['leads'], delta=delta_leads)
    
    delta_qualif = f"{kpis_atu['taxa_qualif'] - kpis_ant['taxa_qualif']:.1f}%" if kpis_ant else None
    k2.metric("Qualificação", f"{kpis_atu['taxa_qualif']:.1f}%", delta=delta_qualif)
    
    delta_conv = f"{kpis_atu['taxa_conversao'] - kpis_ant['taxa_conversao']:.1f}%" if kpis_ant else None
    k3.metric("Conversão", f"{kpis_atu['taxa_conversao']:.1f}%", delta=delta_conv)
    
    delta_fat = formatar_moeda_br(kpis_atu['faturamento_total'] - kpis_ant['faturamento_total']) if kpis_ant else None
    k4.metric("Faturamento", formatar_moeda_br(kpis_atu['faturamento_total']), delta=delta_fat)


def exibir_kpis_secundarios(kpis_dict):
    """
    Exibe 4 métricas secundárias em colunas
    
    Args:
        kpis_dict (dict): Dicionário com chaves como {metrica: valor}
            Exemplo: {'Total Leads': 150, 'Conversões': 15, ...}
    """
    cols = st.columns(len(kpis_dict))
    for col, (label, valor) in zip(cols, kpis_dict.items()):
        col.metric(label, valor)


def exibir_analise_dual(titulo_esq, fig_esq, titulo_dir, fig_dir):
    """
    Exibe dois gráficos lado a lado (padrão muito repetido)
    
    Args:
        titulo_esq (str): Título coluna esquerda
        fig_esq (plotly.graph_objects.Figure): Gráfico esquerda
        titulo_dir (str): Título coluna direita
        fig_dir (plotly.graph_objects.Figure): Gráfico direita
    """
    col_esq, col_dir = st.columns(2)
    
    with col_esq:
        st.markdown(f"**{titulo_esq}**")
        st.plotly_chart(fig_esq, use_container_width=True)
    
    with col_dir:
        st.markdown(f"**{titulo_dir}**")
        st.plotly_chart(fig_dir, use_container_width=True)


def exibir_tabela_formatada(df, formatos_monetarios=None, hide_index=True):
    """
    Exibe dataframe com formatação padronizada
    
    Args:
        df (pd.DataFrame): DataFrame a exibir
        formatos_monetarios (list): Coluna com valores monetários
            Exemplo: ['Fat_Total', 'Ticket_Medio']
        hide_index (bool): Ocultar índice
    """
    if formatos_monetarios is None:
        formatos_monetarios = []
    
    # Construir função de formatação
    formato_dict = {}
    for col in formatos_monetarios:
        if col in df.columns:
            formato_dict[col] = lambda x: formatar_moeda_br(x)
    
    # Adicionar formatação de porcentagem automática
    for col in df.columns:
        if 'pct' in col.lower() or 'taxa' in col.lower():
            if col not in formato_dict:
                formato_dict[col] = '{:.1f}%'
        elif 'quantidade' in col.lower():
            if col not in formato_dict:
                formato_dict[col] = '{:.0f}'
    
    df_display = df.style.format(formato_dict)
    st.dataframe(df_display, use_container_width=True, hide_index=hide_index)


def exibir_alertas(alertas_list):
    """
    Exibe lista de alertas com styling
    
    Args:
        alertas_list (list): Lista de alertas (dicts com 'tipo', 'titulo', 'desc')
    """
    if alertas_list:
        for alerta in alertas_list:
            with st.container(border=True):
                st.markdown(f"**{alerta['tipo']} | {alerta['titulo']}**")
                st.markdown(alerta['desc'])
    else:
        st.success("✅ Nenhum alerta crítico! Performance dentro dos parâmetros.")


def exibir_recomendacoes(recomendacoes_list):
    """
    Exibe lista de recomendações com styling
    
    Args:
        recomendacoes_list (list): Lista de recomendações (dicts com 'titulo', 'acao', 'impacto')
    """
    if recomendacoes_list:
        for i, rec in enumerate(recomendacoes_list, 1):
            with st.container(border=True):
                st.markdown(f"**{i}. {rec['titulo']} {rec['impacto']}**")
                st.markdown(rec['acao'])
    else:
        st.info("💡 Sem recomendações no momento.")


def exibir_header(titulo, subtitulo, logo_path=None):
    """
    Exibe header padronizado com logo
    
    Args:
        titulo (str): Título principal
        subtitulo (str): Subtítulo
        logo_path (str): Caminho do logo (opcional)
    """
    if logo_path:
        col_logo, col_texto = st.columns([0.6, 5])
        with col_logo:
            st.image(logo_path, width=60)
        with col_texto:
            st.title(titulo)
            st.caption(subtitulo)
    else:
        st.title(titulo)
        st.caption(subtitulo)
    st.divider()
