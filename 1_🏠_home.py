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
from PIL import Image

# Configurando Página (usa resource_path para encontrar o ícone)
st.set_page_config(
    page_icon=resource_path("Home.jpg"),
    layout='wide',
    page_title="Pós Obra - Home"
)

# Carregar os logos usando resource_path e PIL
logo_horizontal_path = resource_path("LOGO_VR.png")
logo_reduzida_path   = resource_path("LOGO_VR_REDUZIDA.png")

try:
    logo_horizontal = Image.open(logo_horizontal_path)
    logo_reduzida   = Image.open(logo_reduzida_path)
    st.logo(image=logo_horizontal, size="large", icon_image=logo_reduzida)
except Exception as e:
    st.error(f"Não foi possível carregar as imagens: {e}")

# CEBEÇALHO INÍCIO
st.markdown('<h1 style="color: orange;">Painel de Resultados 📈 AHHHH</h1>', unsafe_allow_html=True)
st.markdown('''Painel para Acompanhamento de Metas Estratégicas - OKR's''')
st.markdown('''Painel de Resultados BI Até 2024 https://app.powerbi.com/view?r=eyJrIjoiYjM0YTU4OWItNGEwOS00MGZkLWE1NGMtYTQyZWM5OGYzYjNiIiwidCI6Ijk5MWEwMGM5LTY1ZGUtNDFjMS04YzUxLTI3N2Q4YzEwZmNkYSJ9''')
# CEBEÇALHO FIM

# COMO FAZER PRA VIR DE EXCEL
excel_home = resource_path("planilha_home.xlsx")
ordem_meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

try:
    df_original = pd.read_excel(excel_home)
    if all(col in df_original.columns for col in ['OBJETIVOS', 'ANO', 'MÊS']):
        df_original['MÊS'] = df_original['MÊS'].apply(lambda x: str(x).capitalize() if not pd.isna(x) else "")
        df_original['ANO'] = df_original['ANO'].apply(lambda x: str(int(x)) if not pd.isna(x) else "")
        df_original['OBJETIVOS'] = df_original['OBJETIVOS'].apply(lambda x: str(x) if not pd.isna(x) else "")
        
        df_filtered = df_original.copy()
        anos_disponiveis = sorted(df_filtered['ANO'].unique())
        ano_selecionado = st.sidebar.selectbox("Selecione o Ano", options=["Todos"] + anos_disponiveis)
        if ano_selecionado != "Todos":
            df_filtered = df_filtered[df_filtered['ANO'] == ano_selecionado]
            
        meses_disponiveis = sorted([mes for mes in df_filtered['MÊS'].unique() if mes in ordem_meses],
                                    key=lambda x: ordem_meses.index(x))
        mes_selecionado = st.sidebar.selectbox("Selecione o Mês", options=["Todos"] + meses_disponiveis)
        if mes_selecionado != "Todos":
            df_filtered = df_filtered[df_filtered['MÊS'] == mes_selecionado]
            
        objetivos_disponiveis = sorted(df_filtered['OBJETIVOS'].unique())
        objetivo_selecionado = st.sidebar.selectbox("Selecione o Objetivo", options=["Todos"] + objetivos_disponiveis)
        if objetivo_selecionado != "Todos":
            df_filtered = df_filtered[df_filtered['OBJETIVOS'] == objetivo_selecionado]
            
        if objetivo_selecionado != "Todos":
            st.markdown(f"# {objetivo_selecionado}")
        else:
            st.markdown("# Dados de Todos os Objetivos")
        st.markdown(f"Dados do Ano Selecionado: {ano_selecionado}" if ano_selecionado != "Todos" else "Dados de Todos os Anos")
        st.markdown(f"Dados do Mês Selecionado: {mes_selecionado}" if mes_selecionado != "Todos" else "Dados de Todos os Meses")
        
        csv_file = "planilha_home.csv"
        df_filtered.to_csv(csv_file, index=False, encoding='utf-8')
        st.markdown("### Objetivos e Indicadores Estratégicos")
        st.dataframe(df_filtered, use_container_width=True)
        st.success(f"Planilha salva como '{csv_file}'!")
    else:
        st.warning("As colunas 'OBJETIVOS', 'ANO' e 'MÊS' não foram encontradas na planilha. Nenhum filtro será aplicado.")
except FileNotFoundError:
    st.error("O arquivo Excel não foi encontrado. Por favor, verifique o caminho.")
except Exception as e:
    st.error(f"Ocorreu um erro: {e}")
