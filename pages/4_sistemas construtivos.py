import sys
import os

# Adiciona o diretório extraído em modo frozen ao sys.path
if getattr(sys, 'frozen', False):
    sys.path.insert(0, sys._MEIPASS)
else:
    sys.path.insert(0, os.path.dirname(__file__))

# Incorpora a função resource_path (conteúdo de utils.py)
def resource_path(relative_path):
    """
    Retorna o caminho absoluto de 'relative_path', seja em desenvolvimento ou quando empacotado.
    """
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(__file__), relative_path)

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import random
from datetime import date
from PIL import Image


# =========================================
# Funções de Cores e Classificação ABC
# =========================================
def random_color():
    """Retorna uma cor aleatória no formato hexadecimal."""
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

def darken_color(hex_color, factor=0.7):
    """Retorna uma versão mais escura da cor recebida."""
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    r = int(r * factor)
    g = int(g * factor)
    b = int(b * factor)
    return "#{:02x}{:02x}{:02x}".format(r, g, b)

def classify_abc(series):
    """
    Classifica os itens de uma série em categorias ABC com base na contribuição acumulada.
    Categoria A: até 70%
    Categoria B: de 70% até 90%
    Categoria C: acima de 90%
    """
    s_sorted = series.sort_values(ascending=False)
    total = s_sorted.sum()
    cum_sum = s_sorted.cumsum()
    categories = {}
    for idx, value in s_sorted.items():
        perc = cum_sum[idx] / total
        if perc <= 0.7:
            categories[idx] = "A"
        elif perc <= 0.9:
            categories[idx] = "B"
        else:
            categories[idx] = "C"
    return categories

# Cores para as categorias ABC
abc_colors = {
    "A": {"fill": "#ff9999", "line": "#cc0000"},  # vermelho claro / escuro
    "B": {"fill": "#ffff99", "line": "#cccc00"},  # amarelo claro / escuro
    "C": {"fill": "#99ff99", "line": "#009900"}   # verde claro / escuro
}

# =========================================
# Configuração da Página e Exibição de Logos
# =========================================
st.set_page_config(
    page_icon="Home.jpg",
    layout='wide',
    page_title="Pós Obra - Sistemas Construtivos"
)

logo_horizontal_path = resource_path("LOGO_VR.png")
logo_reduzida_path   = resource_path("LOGO_VR_REDUZIDA.png")

try:
    logo_horizontal = Image.open(resource_path(logo_horizontal_path))
    logo_reduzida   = Image.open(resource_path(logo_reduzida_path))
    st.logo(image=logo_horizontal, size="large", icon_image=logo_reduzida)
except Exception as e:
    st.error(f"Não foi possível carregar as imagens: {e}")

st.markdown('<h1 style="color: orange;">Sistemas Construtivos 🏗️</h1>', unsafe_allow_html=True)
st.markdown("Página em Construção. Volte mais tarde! 🚧")

# =========================================
# Carregamento dos Dados (Planilhas)
# =========================================
@st.cache_data
def load_data():
    xls = pd.ExcelFile(resource_path("base2025.xlsx"))
    df_eng = pd.read_excel(xls, sheet_name="engenharia")
    df_dep = pd.read_excel(xls, sheet_name="departamento")
    for df_ in [df_eng, df_dep]:
        df_.columns = df_.columns.str.strip()
    return df_eng, df_dep

df_eng, df_dep = load_data()

# =========================================
# Conversão de Datas (engenharia)
# =========================================
df_eng["Data de Abertura"] = pd.to_datetime(df_eng["Data de Abertura"], dayfirst=True, errors="coerce")
df_eng["Encerramento"] = pd.to_datetime(df_eng["Encerramento"], dayfirst=True, errors="coerce")

# =========================================
# Integração com a Aba "departamento"
# =========================================
def get_column(df, expected):
    expected_normalized = expected.replace(" ", "").lower()
    for col in df.columns:
        if col.replace(" ", "").lower() == expected_normalized:
            return col
    return None

expected_cols = ["Empreendimento", "Data CVCO", "Data Entrega de Obra", "N° Unidades", "Status"]
mapping = {}
for expected in expected_cols:
    found = get_column(df_dep, expected)
    if found is None:
        st.error(f"Coluna '{expected}' não encontrada na aba 'departamento'. Colunas disponíveis: {df_dep.columns.tolist()}")
        st.stop()
    else:
        mapping[expected] = found

df_dep_renamed = df_dep.rename(columns={
    mapping["Empreendimento"]: "Empreendimento",
    mapping["Data CVCO"]: "Data CVCO",
    mapping["Data Entrega de Obra"]: "Data Entrega de Obra",
    mapping["N° Unidades"]: "N° Unidades",
    mapping["Status"]: "Status"
})

df_eng = df_eng.merge(
    df_dep_renamed[["Empreendimento", "Data CVCO", "Data Entrega de Obra", "N° Unidades", "Status"]],
    on="Empreendimento",
    how="left",
    suffixes=("", "_dep")
)

# Converter "Data CVCO" para datetime
df_eng["Data CVCO"] = pd.to_datetime(df_eng["Data CVCO"], dayfirst=True, errors="coerce")

# =========================================
# Cálculos Iniciais (Tempo de Encerramento e Dias em Aberto)
# =========================================
df_eng["Tempo de Encerramento"] = (df_eng["Encerramento"] - df_eng["Data de Abertura"]).dt.days
hoje = pd.to_datetime(date.today())
df_eng["Dias em Aberto"] = np.where(
    df_eng["Encerramento"].isna(),
    (hoje - df_eng["Data de Abertura"]).dt.days,
    df_eng["Tempo de Encerramento"]
)
total_solicitacoes = df_eng["N°"].count()

# =========================================
# Criação de Colunas Derivadas: Separação da "Garantia Solicitada"
# =========================================
def split_garantia(value):
    """
    Separa a coluna "Garantia Solicitada" em:
      - Grupo Construtivo: tudo que estiver antes do "-" (ou a frase inteira, se não houver "-")
      - Sistema Construtivo: tudo que estiver depois do "-", se existir.
    """
    if pd.isna(value):
        return pd.Series([np.nan, np.nan])
    if "-" in value:
        parts = value.split("-", 1)
        return pd.Series([parts[0].strip(), parts[1].strip()])
    else:
        return pd.Series([value.strip(), ""])

df_eng[["Grupo Construtivo", "Sistema Construtivo"]] = df_eng["Garantia Solicitada"].apply(split_garantia)

# =========================================
# Interface de Filtros
# =========================================
st.markdown("## Filtros")

# Row1 com divisão [2, 1, 1, 1]
row1 = st.columns([2, 1, 1, 1])
with row1[0]:
    empreendimento_filter = st.multiselect("Empreendimento", options=sorted(df_eng["Empreendimento"].unique()), default=[])
with row1[1]:
    ano_filter = st.multiselect("Ano de Abertura", options=sorted(df_eng["Data de Abertura"].dt.year.unique()), default=[])
with row1[2]:
    meses = {1:"Janeiro", 2:"Fevereiro", 3:"Março", 4:"Abril", 5:"Maio", 6:"Junho",
             7:"Julho", 8:"Agosto", 9:"Setembro", 10:"Outubro", 11:"Novembro", 12:"Dezembro"}
    mes_filter_options = [meses[m] for m in sorted(df_eng["Data de Abertura"].dt.month.unique())]
    mes_filter = st.multiselect("Mês de Abertura", options=mes_filter_options, default=[])
with row1[3]:
    if "Responsável" in df_eng.columns:
    responsavel_options = sorted(df_eng["Responsável"].dropna().astype(str).unique())
    else:
        responsavel_options = []
    responsavel_filter = st.multiselect("Responsável", options=responsavel_options, default=[])

# Row2 para os demais filtros
row2 = st.columns(3)
with row2[0]:
    grupo_filter = st.multiselect("Grupo Construtivo", options=sorted(df_eng["Grupo Construtivo"].dropna().unique()), default=[])
with row2[1]:
    sistema_filter = st.multiselect("Sistema Construtivo", options=sorted(df_eng["Sistema Construtivo"].dropna().unique()), default=[])
with row2[2]:
    fcr_filter = st.multiselect("FCR", options=sorted(df_eng["FCR"].dropna().unique()) if "FCR" in df_eng.columns else [], default=[])

# =========================================
# Aplicação dos Filtros no DataFrame
# =========================================
df_filtered = df_eng.copy()
if empreendimento_filter:
    df_filtered = df_filtered[df_filtered["Empreendimento"].isin(empreendimento_filter)]
if ano_filter:
    df_filtered = df_filtered[df_filtered["Data de Abertura"].dt.year.isin(ano_filter)]
if mes_filter:
    meses_invertido = {v: k for k, v in meses.items()}
    mes_numeros = [meses_invertido[m] for m in mes_filter]
    df_filtered = df_filtered[df_filtered["Data de Abertura"].dt.month.isin(mes_numeros)]
if responsavel_filter:
    df_filtered = df_filtered[df_filtered["Responsável"].isin(responsavel_filter)]
if grupo_filter:
    df_filtered = df_filtered[df_filtered["Grupo Construtivo"].isin(grupo_filter)]
if sistema_filter:
    df_filtered = df_filtered[df_filtered["Sistema Construtivo"].isin(sistema_filter)]
if fcr_filter:
    df_filtered = df_filtered[df_filtered["FCR"].isin(fcr_filter)]

# Considerar somente registros com Status "Concluída"
df_filtered = df_filtered[df_filtered["Status"] == "Concluída"]

st.markdown("### Dados Filtrados")
st.dataframe(df_filtered)

# =========================================
# Cálculo das Métricas (MTBF, MTTR e Disponibilidade)
# =========================================
def compute_metrics(group):
    """
    Calcula as métricas para o grupo (ou sistema) considerando:
      - T_disponível: diferença entre a última "Data de Abertura" e a menor "Data CVCO", convertida para horas.
      - T_parada: soma, em horas, de (Encerramento - Data de Abertura) para cada ocorrência.
      - MTBF: (T_disponível - T_parada) / número de ocorrências.
      - MTTR: T_parada / número de ocorrências.
      - Disponibilidade: MTBF/(MTBF+MTTR)*100%.
    """
    available_hours = (group["Data de Abertura"].max() - group["Data CVCO"].min()).total_seconds() / 3600
    downtime_hours = group.apply(lambda row: (row["Encerramento"] - row["Data de Abertura"]).total_seconds() / 3600, axis=1).sum()
    occurrences = group.shape[0]
    mtbf = (available_hours - downtime_hours) / occurrences
    mttr = downtime_hours / occurrences
    dispon = (mtbf / (mtbf + mttr)) * 100 if (mtbf + mttr) > 0 else np.nan
    return pd.Series({"MTBF": mtbf, "MTTR": mttr, "Disponibilidade": dispon})

# Recalcular métricas para cada grupo e sistema
metrics_group = df_filtered.groupby("Grupo Construtivo").apply(compute_metrics)
metrics_system = df_filtered.groupby("Sistema Construtivo").apply(compute_metrics)

# Para curvas ABC, contagens de ocorrências
contagem_group = df_filtered["Grupo Construtivo"].value_counts()
contagem_system = df_filtered["Sistema Construtivo"].value_counts()

def add_border(fig):
    for trace in fig.data:
        if hasattr(trace, "marker") and "color" in trace.marker:
            trace.marker.line.width = 1
    return fig

# =========================================
# Geração dos Gráficos
# =========================================
st.markdown("## Gráficos")

# --- Fig1: MTBF por Grupo Construtivo ---
top_option_fig1 = st.selectbox("Selecione top para MTBF por Grupo Construtivo", 
                                 options=["Todos", "Top 5", "Top 10", "Top 20"],
                                 index=0, key="fig1")
mtbf_group_plot = metrics_group["MTBF"].copy()
if top_option_fig1 != "Todos":
    n = int(top_option_fig1.split()[1])
    mtbf_group_plot = mtbf_group_plot.sort_values(ascending=False).head(n)
fig1 = px.bar(
    x=mtbf_group_plot.index,
    y=mtbf_group_plot.values,
    labels={"x": "Grupo Construtivo", "y": "MTBF (horas)"},
    title="MTBF por Grupo Construtivo"
)
n_bars = len(mtbf_group_plot.index)
colors = [random_color() for _ in range(n_bars)]
line_colors = [darken_color(c) for c in colors]
fig1.update_traces(marker_color=colors, marker_line_color=line_colors, marker_line_width=1)
st.plotly_chart(fig1, use_container_width=True)

# --- Fig2: MTBF por Sistema Construtivo ---
top_option_fig2 = st.selectbox("Selecione top para MTBF por Sistema Construtivo", 
                                 options=["Todos", "Top 5", "Top 10", "Top 20"],
                                 index=0, key="fig2")
mtbf_system_plot = metrics_system["MTBF"].copy()
if top_option_fig2 != "Todos":
    n = int(top_option_fig2.split()[1])
    mtbf_system_plot = mtbf_system_plot.sort_values(ascending=False).head(n)
fig2 = px.bar(
    x=mtbf_system_plot.index,
    y=mtbf_system_plot.values,
    labels={"x": "Sistema Construtivo", "y": "MTBF (horas)"},
    title="MTBF por Sistema Construtivo"
)
n_bars = len(mtbf_system_plot.index)
colors = [random_color() for _ in range(n_bars)]
line_colors = [darken_color(c) for c in colors]
fig2.update_traces(marker_color=colors, marker_line_color=line_colors, marker_line_width=1)
st.plotly_chart(fig2, use_container_width=True)

# --- Fig3: MTTR por Grupo Construtivo (com Disponibilidade) ---
top_option_fig3 = st.selectbox("Selecione top para MTTR por Grupo Construtivo", 
                                 options=["Todos", "Top 5", "Top 10", "Top 20"],
                                 index=0, key="fig3")
mttr_group_plot = metrics_group["MTTR"].copy()
disp_group_plot = metrics_group["Disponibilidade"].copy()
if top_option_fig3 != "Todos":
    n = int(top_option_fig3.split()[1])
    mttr_group_plot = mttr_group_plot.sort_values(ascending=False).head(n)
    disp_group_plot = disp_group_plot.loc[mttr_group_plot.index]
fig3 = px.bar(
    x=mttr_group_plot.index,
    y=mttr_group_plot.values,
    labels={"x": "Grupo Construtivo", "y": "MTTR (horas)"},
    title="MTTR por Grupo Construtivo"
)
fig3.update_traces(text=disp_group_plot.values, textposition='outside')
n_bars = len(mttr_group_plot.index)
colors = [random_color() for _ in range(n_bars)]
line_colors = [darken_color(c) for c in colors]
fig3.update_traces(marker_color=colors, marker_line_color=line_colors, marker_line_width=1)
st.plotly_chart(fig3, use_container_width=True)

# --- Fig4: MTTR por Sistema Construtivo (com Disponibilidade) ---
top_option_fig4 = st.selectbox("Selecione top para MTTR por Sistema Construtivo", 
                                 options=["Todos", "Top 5", "Top 10", "Top 20"],
                                 index=0, key="fig4")
mttr_system_plot = metrics_system["MTTR"].copy()
disp_system_plot = metrics_system["Disponibilidade"].copy()
if top_option_fig4 != "Todos":
    n = int(top_option_fig4.split()[1])
    mttr_system_plot = mttr_system_plot.sort_values(ascending=False).head(n)
    disp_system_plot = disp_system_plot.loc[mttr_system_plot.index]
fig4 = px.bar(
    x=mttr_system_plot.index,
    y=mttr_system_plot.values,
    labels={"x": "Sistema Construtivo", "y": "MTTR (horas)"},
    title="MTTR por Sistema Construtivo"
)
fig4.update_traces(text=disp_system_plot.values, textposition='outside')
n_bars = len(mttr_system_plot.index)
colors = [random_color() for _ in range(n_bars)]
line_colors = [darken_color(c) for c in colors]
fig4.update_traces(marker_color=colors, marker_line_color=line_colors, marker_line_width=1)
st.plotly_chart(fig4, use_container_width=True)

# --- Fig5: Curva ABC por Grupo Construtivo (Incidências) ---
top_option_fig5 = st.selectbox("Selecione top para Curva ABC por Grupo Construtivo", 
                                 options=["Todos", "Top 5", "Top 10", "Top 20"],
                                 index=0, key="fig5")
contagem_group_plot = contagem_group.copy()
if top_option_fig5 != "Todos":
    n = int(top_option_fig5.split()[1])
    contagem_group_plot = contagem_group_plot.head(n)
fig5 = px.bar(
    x=contagem_group_plot.index,
    y=contagem_group_plot.values,
    labels={"x": "Grupo Construtivo", "y": "Contagem de Incidências"},
    title="Curva ABC por Grupo Construtivo"
)
abc_class_group = classify_abc(contagem_group_plot)
colors = [abc_colors[abc_class_group[idx]]["fill"] for idx in contagem_group_plot.index]
line_colors = [abc_colors[abc_class_group[idx]]["line"] for idx in contagem_group_plot.index]
fig5.update_traces(marker_color=colors, marker_line_color=line_colors, marker_line_width=1)
st.plotly_chart(fig5, use_container_width=True)

# --- Fig6: Curva ABC por Sistema Construtivo (Incidências) ---
top_option_fig6 = st.selectbox("Selecione top para Curva ABC por Sistema Construtivo", 
                                 options=["Todos", "Top 5", "Top 10", "Top 20"],
                                 index=0, key="fig6")
contagem_system_plot = contagem_system.copy()
if top_option_fig6 != "Todos":
    n = int(top_option_fig6.split()[1])
    contagem_system_plot = contagem_system_plot.head(n)
fig6 = px.bar(
    x=contagem_system_plot.index,
    y=contagem_system_plot.values,
    labels={"x": "Sistema Construtivo", "y": "Contagem de Incidências"},
    title="Curva ABC por Sistema Construtivo"
)
abc_class_system = classify_abc(contagem_system_plot)
colors = [abc_colors[abc_class_system[idx]]["fill"] for idx in contagem_system_plot.index]
line_colors = [abc_colors[abc_class_system[idx]]["line"] for idx in contagem_system_plot.index]
fig6.update_traces(marker_color=colors, marker_line_color=line_colors, marker_line_width=1)
st.plotly_chart(fig6, use_container_width=True)
