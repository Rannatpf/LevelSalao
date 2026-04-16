import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
import sys
import re
from pathlib import Path

CSS_PATH = Path(__file__).with_name("styles.css")
LOGO_FILE = "level-logo_azul-marinho_com-letra.webp"


def aplicar_css_premium():
    """Carrega o design system local da dashboard."""
    try:
        possible_paths = [
            CSS_PATH,
            Path.cwd() / "styles.css",
            Path(__file__).parent / "styles.css",
        ]

        for css_path in possible_paths:
            if css_path.exists():
                st.markdown(
                    f"<style>{css_path.read_text(encoding='utf-8')}</style>",
                    unsafe_allow_html=True,
                )
                break
    except Exception:
        pass


def resolver_logo_path():
    possible_paths = [
        Path(__file__).parent / "assets" / LOGO_FILE,
        Path.cwd() / "assets" / LOGO_FILE,
        Path(LOGO_FILE),
    ]

    for path in possible_paths:
        if path.exists():
            return str(path)
    return None


PAGE_ICON = resolver_logo_path() or "💇"

st.set_page_config(
    page_icon=PAGE_ICON,
    page_title="Level Salão | Dashboard de Performance",
    layout="wide",
    initial_sidebar_state="collapsed"
)


aplicar_css_premium()

# ============================================


def _normalizar_modelo_base(df):
    if df.empty:
        return None

    model_df = df.copy()
    if "Data_Ref" in model_df.columns and model_df["Data_Ref"].notna().any():
        model_df["mes_num"] = model_df["Data_Ref"].dt.month.fillna(0).astype(int)
        model_df["dia_semana"] = model_df["Data_Ref"].dt.dayofweek.fillna(0).astype(int)
        model_df["dia_mes"] = model_df["Data_Ref"].dt.day.fillna(0).astype(int)
    else:
        model_df["mes_num"] = 0
        model_df["dia_semana"] = 0
        model_df["dia_mes"] = 0

    if "is_faturado" not in model_df.columns:
        return None

    feature_cols = ["Origem", "Qualificação", "Serviço", "Profissional", "mes_num", "dia_semana", "dia_mes"]
    for column in feature_cols:
        if column not in model_df.columns:
            model_df[column] = "Desconhecido" if column in ["Origem", "Qualificação", "Serviço", "Profissional"] else 0

    model_df["ticket_base"] = model_df.get("Faturamento_Num", 0)
    return model_df, feature_cols


def gerar_insights_ia(df):
    base = _normalizar_modelo_base(df)
    if base is None:
        return None

    model_df, feature_cols = base
    target = model_df["is_faturado"].astype(int)

    if target.nunique() < 2 or len(model_df) < 20:
        return None

    X = model_df[feature_cols].copy()
    encoders = {}
    for column in ["Origem", "Qualificação", "Serviço", "Profissional"]:
        encoder = LabelEncoder()
        X[column] = encoder.fit_transform(X[column].astype(str).fillna("Desconhecido"))
        encoders[column] = encoder

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        target,
        test_size=0.25,
        random_state=42,
        stratify=target if target.nunique() > 1 else None,
    )

    model = RandomForestClassifier(
        n_estimators=250,
        random_state=42,
        class_weight="balanced_subsample",
        max_depth=7,
        min_samples_leaf=2,
    )
    model.fit(X_train, y_train)

    pred = model.predict(X_test)
    prob = model.predict_proba(X_test)[:, 1]

    final_model = RandomForestClassifier(
        n_estimators=250,
        random_state=42,
        class_weight="balanced_subsample",
        max_depth=7,
        min_samples_leaf=2,
    )
    final_model.fit(X, target)

    df_score = model_df.copy()
    df_score["Prob_Conversao"] = final_model.predict_proba(X)[:, 1]

    leads_pendentes = df_score[df_score["is_faturado"] == 0].copy()
    if not leads_pendentes.empty:
        leads_pendentes = leads_pendentes.sort_values("Prob_Conversao", ascending=False)

    ticket_medio = float(model_df.loc[model_df["is_faturado"] == 1, "Faturamento_Num"].mean() or 0)
    receita_esperada = float((leads_pendentes["Prob_Conversao"] * ticket_medio).sum()) if ticket_medio > 0 and not leads_pendentes.empty else 0.0

    importancias = pd.DataFrame({
        "Variavel": feature_cols,
        "Importancia": final_model.feature_importances_,
    }).sort_values("Importancia", ascending=True)

    canais_prioritarios = pd.DataFrame()
    if "Origem" in leads_pendentes.columns and not leads_pendentes.empty:
        canais_prioritarios = (
            leads_pendentes.groupby("Origem")
            .agg(
                Leads_Pendentes=("Prob_Conversao", "count"),
                Score_Medio=("Prob_Conversao", "mean"),
            )
            .sort_values(["Score_Medio", "Leads_Pendentes"], ascending=False)
            .reset_index()
        )

    profissionais_prioritarios = pd.DataFrame()
    if "Profissional" in leads_pendentes.columns and not leads_pendentes.empty:
        profissionais_prioritarios = (
            leads_pendentes.groupby("Profissional")
            .agg(
                Leads_Pendentes=("Prob_Conversao", "count"),
                Score_Medio=("Prob_Conversao", "mean"),
            )
            .sort_values(["Score_Medio", "Leads_Pendentes"], ascending=False)
            .reset_index()
        )

    metrics = {
        "accuracy": accuracy_score(y_test, pred),
        "precision": precision_score(y_test, pred, zero_division=0),
        "recall": recall_score(y_test, pred, zero_division=0),
        "roc_auc": roc_auc_score(y_test, prob) if y_test.nunique() > 1 else 0,
        "receita_esperada": receita_esperada,
        "ticket_medio": ticket_medio,
        "taxa_real": float(target.mean() * 100),
    }

    return {
        "metrics": metrics,
        "importancias": importancias,
        "leads_pendentes": leads_pendentes,
        "canais_prioritarios": canais_prioritarios,
        "profissionais_prioritarios": profissionais_prioritarios,
    }

# ============================================
# IMPORT MODULES
# ============================================
sys.path.insert(0, str(Path(__file__).parent.resolve()))
from modules import (
    formatar_moeda_br,
    carregar_dados_mestre as carregar_dados_mestre_mod,
    calcular_kpis,
    criar_filtros,
    construir_df_filtrado,
    analisar_performance_canais,
    analisar_servico,
    calcular_lag_medio,
    criar_grafico_pizza,
    criar_grafico_barras_horizontal,
    criar_grafico_barras_vertical,
    criar_grafico_scatter,
    criar_grafico_histograma,
    criar_grafico_funil,
    criar_grafico_gauge,
    criar_grafico_radar,
    calcular_receita_pendente,
    exibir_kpis_principais,
    exibir_kpis_secundarios,
    exibir_analise_dual,
    exibir_tabela_formatada,
    exibir_header
)

# ============================================
# CARREGAMENTO
# ============================================
df_raw = carregar_dados_mestre_mod()

if df_raw is not None:
    if 'Data_Ref' not in df_raw.columns or df_raw['Data_Ref'].notna().sum() == 0:
        st.warning('Nenhuma data disponível na base carregada.')
        st.stop()

    logo_path = resolver_logo_path()

    exibir_header(
        titulo="Level Salão | Dashboard de Performance",
        subtitulo="Análise inteligente de canais, profissionais e serviços",
        logo_path=logo_path
    )

    tab_real, tab_perf, tab_servico, tab_proj = st.tabs([
        "📊 Histórico Real",
        "🎯 Performance Canais",
        "💇 Serviços & Produtos",
        "🔮 Simulador"
    ])

    # ==========================================
    # ABA 1: DADOS REAIS
    # ==========================================
    with tab_real:
        meses_real, canais_sel = criar_filtros(df_raw, "real")
        df_filtrado = construir_df_filtrado(df_raw, meses_real, canais_sel)

        kpis_atu = calcular_kpis(df_filtrado)
        exibir_kpis_principais(kpis_atu, None)
        st.divider()

        if not df_filtrado.empty:
            origens = df_filtrado['Origem'].fillna('Desconhecida').value_counts(normalize=True)
            origens_df = origens[origens >= 0.03].reset_index()
            origens_df.columns = ['Origem', 'proportion']
            outros = origens[origens < 0.03].sum()
            if outros > 0:
                origens_df = pd.concat([
                    origens_df,
                    pd.DataFrame({'Origem': ['Outros'], 'proportion': [outros]})
                ], ignore_index=True)

            fig_pizza = criar_grafico_pizza(origens_df, 'Origem', 'proportion', cor_paleta='Brwnyl')
            fig_funil = criar_grafico_funil(
                categorias=["Leads", "Qualificados", "Vendas"],
                valores=[len(df_filtrado), df_filtrado['is_qualificado'].sum(), df_filtrado['is_faturado'].sum()],
                cores=["#F1E9E0", "#D4A373", "#4A3728"]
            )

            exibir_analise_dual("📱 Origem dos Leads", fig_pizza, "🌪️ Funil de Conversão", fig_funil)
        else:
            st.warning("⚠️ Nenhum dado disponível para o filtro selecionado")

    # ==========================================
    # ABA 2: PERFORMANCE POR CANAL
    # ==========================================
    with tab_perf:
        meses_perf, canais_perf = criar_filtros(df_raw, "perf")
        df_perf = construir_df_filtrado(df_raw, meses_perf, canais_perf)

        if not df_perf.empty:
            kpis_perf = calcular_kpis(df_perf)
            exibir_kpis_secundarios({
                "Total Leads": kpis_perf['leads'],
                "Faturamentos": kpis_perf['conversoes'],
                "Faturamento Total": formatar_moeda_br(kpis_perf['faturamento_total']),
                "Ticket Médio": formatar_moeda_br(kpis_perf['ticket_medio'])
            })

            st.divider()

            canal_perf = analisar_performance_canais(df_perf)
            if not canal_perf.empty:
                fig_conv = criar_grafico_scatter(
                    dados=canal_perf,
                    x_col='Leads',
                    y_col='Taxa_Conv_Pct',
                    size_col='Conversoes',
                    hover_col='Origem',
                    cor_col='Taxa_Conv_Pct',
                    titulo=""
                )

                fig_fat = criar_grafico_barras_horizontal(
                    dados=canal_perf.sort_values('Fat_Total'),
                    y_col='Origem',
                    x_col='Fat_Total',
                    cor_col='Taxa_Conv_Pct',
                    titulo=""
                )

                exibir_analise_dual("📈 Conversão por Canal", fig_conv, "💰 Faturamento por Canal", fig_fat)

                st.divider()

                # --- Evolução mensal por canal ---
                st.subheader("📈 Evolução Mensal por Canal")
                _ORDEM_MESES = [
                    "Novembro", "Dezembro", "Janeiro", "Fevereiro",
                    "Março", "Abril", "Maio", "Junho",
                    "Julho", "Agosto", "Setembro", "Outubro",
                ]
                evo = df_perf.groupby(['Mês', 'Origem']).agg(
                    Leads=('Nome', 'count'),
                    Faturados=('is_faturado', 'sum'),
                    Faturamento=('Faturamento_Num', 'sum'),
                ).reset_index()
                evo['Taxa_Conv'] = (evo['Faturados'] / evo['Leads'] * 100).round(1)
                evo['Receita_por_Lead'] = (evo['Faturamento'] / evo['Leads']).round(2)
                meses_presentes = [m for m in _ORDEM_MESES if m in evo['Mês'].values]
                evo['Mês'] = pd.Categorical(evo['Mês'], categories=meses_presentes, ordered=True)
                evo = evo.sort_values('Mês')

                col_evo1, col_evo2 = st.columns(2)
                with col_evo1:
                    st.markdown("**Leads por Mês**")
                    fig_leads_evo = px.line(
                        evo, x='Mês', y='Leads', color='Origem',
                        markers=True, text='Leads',
                        color_discrete_sequence=px.colors.sequential.Brwnyl,
                    )
                    fig_leads_evo.update_traces(textposition='top center')
                    fig_leads_evo.update_layout(template='plotly_white', height=350, title='')
                    st.plotly_chart(fig_leads_evo, use_container_width=True)

                with col_evo2:
                    st.markdown("**Taxa de Conversão por Mês (%)**")
                    fig_conv_evo = px.line(
                        evo, x='Mês', y='Taxa_Conv', color='Origem',
                        markers=True, text='Taxa_Conv',
                        color_discrete_sequence=px.colors.sequential.Brwnyl,
                    )
                    fig_conv_evo.update_traces(textposition='top center')
                    fig_conv_evo.update_layout(template='plotly_white', height=350, title='')
                    st.plotly_chart(fig_conv_evo, use_container_width=True)

                # --- Receita por Lead por Canal ---
                st.divider()
                st.subheader("💵 Receita por Lead (Faturamento ÷ Leads)")
                rpl = canal_perf.copy()
                rpl['Receita_por_Lead'] = (rpl['Fat_Total'] / rpl['Leads']).round(2)
                rpl = rpl.sort_values('Receita_por_Lead', ascending=True)

                fig_rpl = px.bar(
                    rpl, y='Origem', x='Receita_por_Lead',
                    orientation='h', text_auto='.2f',
                    color='Receita_por_Lead',
                    color_continuous_scale='Brwnyl',
                )
                fig_rpl.update_layout(
                    template='plotly_white', height=350, title='',
                    xaxis_title='R$ por Lead', yaxis_title='',
                    showlegend=False,
                )
                st.plotly_chart(fig_rpl, use_container_width=True)

                st.divider()
                st.subheader("📊 Ranking por Impacto")
                exibir_tabela_formatada(
                    canal_perf[['Origem', 'Leads', 'Conversoes', 'Taxa_Conv_Pct', 'Fat_Total']],
                    formatos_monetarios=['Fat_Total']
                )
        else:
            st.warning("⚠️ Nenhum dado para o período selecionado")

    # ==========================================
    # ABA 3: ANÁLISE DE SERVIÇOS
    # ==========================================
    with tab_servico:
        meses_serv, canais_serv = criar_filtros(df_raw, "serv")
        df_serv_filt = construir_df_filtrado(df_raw, meses_serv, canais_serv)

        servico_stats = analisar_servico(df_serv_filt)
        if servico_stats is not None:
            st.subheader("💇 Serviços & Produtos Mais Vendidos")

            fig_serv_qtd = criar_grafico_barras_vertical(
                dados=servico_stats.nlargest(10, 'Quantidade'),
                x_col='Serviço',
                y_col='Quantidade',
                cor_col='Quantidade',
                cor_escala='Oranges',
                titulo=""
            )

            fig_serv_pizza = criar_grafico_pizza(
                dados=servico_stats.nlargest(8, 'Faturamento'),
                nomes_col='Serviço',
                valores_col='Faturamento',
                cor_paleta='Set2'
            )

            exibir_analise_dual("Quantidade Vendida", fig_serv_qtd, "Faturamento", fig_serv_pizza)

            st.divider()
            st.markdown("**Tabela Completa**")
            exibir_tabela_formatada(
                servico_stats,
                formatos_monetarios=['Faturamento', 'Ticket_Medio']
            )

            st.divider()
            lag_stats = calcular_lag_medio(df_serv_filt)
            if lag_stats:
                st.subheader("⏱️ Velocidade de Conversão (Dias até Venda)")
                exibir_kpis_secundarios({
                    "Média de Dias": f"{lag_stats['media']:.0f}",
                    "Mediana": f"{lag_stats['mediana']:.0f}",
                    "Mínimo": f"{lag_stats['min']:.0f}",
                    "Máximo": f"{lag_stats['max']:.0f}"
                })

                fig_lag = criar_grafico_histograma(
                    x_dados=lag_stats['distribuicao'],
                    nbins=20,
                    titulo="Distribuição de Dias até Faturamento",
                    xlabel="Dias"
                )
                st.plotly_chart(fig_lag, use_container_width=True)
        else:
            st.info("📊 Dados de Serviço não disponíveis neste período")

    # ==========================================
    # ABA 5: SIMULADOR
    # ==========================================
    with tab_proj:
        st.header("🔮 Simulador de Escala Estratégica")

        ultimo_mes = df_raw['Data_Ref'].max().to_period('M')
        df_base = df_raw[df_raw['Data_Ref'].dt.to_period('M') == ultimo_mes]
        kpis_base = calcular_kpis(df_base)

        col_sim_1, col_sim_2 = st.columns(2)
        scale_leads = col_sim_1.slider("Escalar Leads (%)", 0, 300, 50)
        scale_conv = col_sim_2.slider("Melhorar Conversão (%)", 0, 100, 10)

        leads_proj = int(kpis_base['leads'] * (1 + scale_leads / 100))
        conv_proj = kpis_base['taxa_conversao'] / 100 * (1 + scale_conv / 100)
        fat_proj = leads_proj * conv_proj * kpis_base['ticket_medio']

        st.markdown(f"### 🎯 Projeção baseada em {ultimo_mes.strftime('%b/%y')}")
        exibir_kpis_secundarios({
            "Leads Projetados": f"{leads_proj} (+{leads_proj - kpis_base['leads']})",
            "Conversão Alvo": f"{conv_proj * 100:.1f}%",
            "Faturamento": formatar_moeda_br(fat_proj)
        })

        st.divider()

        col_ia1, col_ia2 = st.columns(2)
        with col_ia1:
            st.subheader("💰 Receita Pendente")
            valor_pend = calcular_receita_pendente(df_raw, kpis_base['ticket_medio'])
            fig_gauge = criar_grafico_gauge(
                valor=valor_pend,
                titulo="Leads Qualificados",
                prefixo="R$ "
            )
            st.plotly_chart(fig_gauge, use_container_width=True)

        with col_ia2:
            st.subheader("💡 Drivers de Impacto")
            try:
                insights_proj = gerar_insights_ia(df_base)
                if insights_proj and not insights_proj["importancias"].empty:
                    fig_radar = criar_grafico_radar(
                        valores=insights_proj["importancias"]["Importancia"].tolist(),
                        categorias=insights_proj["importancias"]["Variavel"].tolist(),
                        titulo="Feature Importance"
                    )
                    st.plotly_chart(fig_radar, use_container_width=True)
                else:
                    st.info("Dados insuficientes para análise")
            except Exception:
                st.info("Dados insuficientes para análise")

else:
    st.error("Erro ao carregar dados da API")
