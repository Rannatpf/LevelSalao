"""
MODULES PACKAGE
Módulos de processamento de dados, análises e visualizações
"""

from .data_processing import (
    formatar_moeda_br,
    carregar_dados_mestre,
    calcular_kpis,
    criar_filtros,
    construir_df_filtrado
)

from .analytics import (
    analisar_performance_canais,
    analisar_profissional,
    analisar_servico,
    calcular_lag_medio
)

from .visualizations import (
    criar_grafico_pizza,
    criar_grafico_barras_horizontal,
    criar_grafico_barras_vertical,
    criar_grafico_scatter,
    criar_grafico_histograma,
    criar_grafico_funil,
    criar_grafico_gauge,
    criar_grafico_radar
)

from .alerts import (
    gerar_alertas_criticos,
    gerar_recomendacoes_ia,
    calcular_receita_pendente
)

from .ui_components import (
    exibir_kpis_principais,
    exibir_kpis_secundarios,
    exibir_analise_dual,
    exibir_tabela_formatada,
    exibir_alertas,
    exibir_recomendacoes,
    exibir_header
)

__all__ = [
    # Data Processing
    'formatar_moeda_br',
    'carregar_dados_mestre',
    'calcular_kpis',
    'criar_filtros',
    'construir_df_filtrado',
    
    # Analytics
    'analisar_performance_canais',
    'analisar_profissional',
    'analisar_servico',
    'calcular_lag_medio',
    
    # Visualizations
    'criar_grafico_pizza',
    'criar_grafico_barras_horizontal',
    'criar_grafico_barras_vertical',
    'criar_grafico_scatter',
    'criar_grafico_histograma',
    'criar_grafico_funil',
    'criar_grafico_gauge',
    'criar_grafico_radar',
    
    # Alerts
    'gerar_alertas_criticos',
    'gerar_recomendacoes_ia',
    'calcular_receita_pendente',
    
    # UI Components
    'exibir_kpis_principais',
    'exibir_kpis_secundarios',
    'exibir_analise_dual',
    'exibir_tabela_formatada',
    'exibir_alertas',
    'exibir_recomendacoes',
    'exibir_header'
]
