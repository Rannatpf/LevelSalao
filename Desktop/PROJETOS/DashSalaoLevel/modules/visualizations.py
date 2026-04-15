"""
VISUALIZATIONS MODULE
Funções reutilizáveis para criar gráficos com Plotly
"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


def criar_grafico_pizza(dados, nomes_col, valores_col, titulo="", cor_paleta="Brwnyl"):
    """
    Cria gráfico de pizza (donut) padronizado
    
    Args:
        dados (pd.DataFrame): Dados para visualizar
        nomes_col (str): Coluna com rótulos
        valores_col (str): Coluna com valores
        titulo (str): Título do gráfico
        cor_paleta (str): Paleta de cores Plotly
    
    Returns:
        plotly.graph_objects.Figure: Figura do gráfico
    """
    fig = px.pie(
        dados,
        names=nomes_col,
        values=valores_col,
        hole=0.4,
        color_discrete_sequence=px.colors.sequential.get(cor_paleta)
        if hasattr(px.colors.sequential, 'get')
        else getattr(px.colors.sequential, cor_paleta.lower(), px.colors.sequential.Brwnyl)
    )
    fig.update_layout(
        template="plotly_white",
        height=350,
        title=titulo if titulo else None
    )
    return fig


def criar_grafico_barras_horizontal(dados, y_col, x_col, cor_col=None, titulo="", cor_escala="RdYlGn"):
    """
    Cria gráfico de barras horizontal com cores gradientes
    
    Args:
        dados (pd.DataFrame): Dados para visualizar
        y_col (str): Coluna para eixo Y
        x_col (str): Coluna para eixo X
        cor_col (str): Coluna para colorir (gradiente)
        titulo (str): Título do gráfico
        cor_escala (str): Escala de cores Plotly
    
    Returns:
        plotly.graph_objects.Figure: Figura do gráfico
    """
    fig = px.bar(
        dados.sort_values(x_col),
        y=y_col,
        x=x_col,
        orientation='h',
        color=cor_col,
        color_continuous_scale=cor_escala,
        title=titulo
    )
    fig.update_layout(
        template="plotly_white",
        height=400,
        showlegend=False
    )
    return fig


def criar_grafico_barras_vertical(dados, x_col, y_col, cor_col=None, titulo="", cor_escala="RdYlGn"):
    """
    Cria gráfico de barras vertical com cores gradientes
    
    Args:
        dados (pd.DataFrame): Dados para visualizar
        x_col (str): Coluna para eixo X
        y_col (str): Coluna para eixo Y
        cor_col (str): Coluna para colorir (gradiente)
        titulo (str): Título do gráfico
        cor_escala (str): Escala de cores Plotly
    
    Returns:
        plotly.graph_objects.Figure: Figura do gráfico
    """
    fig = px.bar(
        dados.nlargest(10, y_col) if len(dados) > 10 else dados,
        y=y_col,
        x=x_col,
        color=cor_col,
        color_continuous_scale=cor_escala,
        title=titulo
    )
    fig.update_layout(
        template="plotly_white",
        height=400,
        showlegend=False
    )
    return fig


def criar_grafico_scatter(dados, x_col, y_col, size_col, hover_col, cor_col, titulo=""):
    """
    Cria gráfico scatter com bolhas (bubble chart)
    
    Args:
        dados (pd.DataFrame): Dados para visualizar
        x_col (str): Coluna para eixo X
        y_col (str): Coluna para eixo Y
        size_col (str): Coluna para tamanho das bolhas
        hover_col (str): Coluna para hover info
        cor_col (str): Coluna para cor
        titulo (str): Título do gráfico
    
    Returns:
        plotly.graph_objects.Figure: Figura do gráfico
    """
    fig = px.scatter(
        dados,
        x=x_col,
        y=y_col,
        size=size_col,
        hover_data=[hover_col],
        color=cor_col,
        color_continuous_scale='RdYlGn',
        title=titulo,
        labels={x_col: x_col.replace('_', ' '), y_col: y_col.replace('_', ' ')}
    )
    fig.update_layout(
        template="plotly_white",
        height=400
    )
    return fig


def criar_grafico_histograma(x_dados, nbins=20, titulo="", xlabel=""):
    """
    Cria histograma de distribuição
    
    Args:
        x_dados (pd.Series): Dados para visualizar
        nbins (int): Número de bins
        titulo (str): Título do gráfico
        xlabel (str): Rótulo do eixo X
    
    Returns:
        plotly.graph_objects.Figure: Figura do gráfico
    """
    fig = px.histogram(
        x=x_dados,
        nbins=nbins,
        title=titulo,
        labels={'x': xlabel, 'y': 'Frequência'}
    )
    fig.update_layout(
        template="plotly_white",
        height=400,
        showlegend=False
    )
    return fig


def criar_grafico_funil(categorias, valores, cores=None, titulo=""):
    """
    Cria gráfico de funil (funnel)
    
    Args:
        categorias (list): Rótulos das etapas
        valores (list): Valores de cada etapa
        cores (list): Cores customizadas
        titulo (str): Título do gráfico
    
    Returns:
        plotly.graph_objects.Figure: Figura do gráfico
    """
    if cores is None:
        cores = ["#F1E9E0", "#D4A373", "#4A3728"]
    
    fig = go.Figure(go.Funnel(
        y=categorias,
        x=valores,
        marker={"color": cores}
    ))
    fig.update_layout(
        template="plotly_white",
        height=350,
        title=titulo if titulo else None
    )
    return fig


def criar_grafico_gauge(valor, titulo="", minimo=0, maximo=100, prefixo=""):
    """
    Cria gráfico de medidor (gauge)
    
    Args:
        valor (float): Valor a exibir
        titulo (str): Título do gráfico
        minimo (float): Valor mínimo da escala
        maximo (float): Valor máximo da escala
        prefixo (str): Prefixo do número (ex: "R$ ")
    
    Returns:
        plotly.graph_objects.Figure: Figura do gráfico
    """
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=valor,
        number={'prefix': prefixo},
        title={'text': titulo},
        gauge={
            'axis': {'range': [minimo, maximo]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [minimo, maximo/3], 'color': "lightgray"},
                {'range': [maximo/3, 2*maximo/3], 'color': "gray"},
                {'range': [2*maximo/3, maximo], 'color': "darkgray"}
            ]
        }
    ))
    fig.update_layout(height=350)
    return fig


def criar_grafico_radar(valores, categorias, titulo="", cor="rgba(76, 175, 80, 0.5)"):
    """
    Cria gráfico radar (spider)
    
    Args:
        valores (list): Valores para cada categoria
        categorias (list): Rótulos das categorias
        titulo (str): Título do gráfico
        cor (str): Cor do preenchimento
    
    Returns:
        plotly.graph_objects.Figure: Figura do gráfico
    """
    fig = go.Figure(data=go.Scatterpolar(
        r=valores,
        theta=categorias,
        fill='toself',
        marker=dict(color=cor),
        name=titulo
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, max(valores)])),
        height=400,
        title=titulo if titulo else None
    )
    return fig
