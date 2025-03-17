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
import plotly.express as px
import warnings
import locale
from PIL import Image

# Configurando Página
st.set_page_config(
    page_icon=resource_path("Home.jpg"),
    layout='wide',
    page_title="Pós Obra - Departamento"
)

# Configurar o locale para formato brasileiro
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    st.warning("Locale 'pt_BR.UTF-8' não disponível. Utilizando o locale padrão do sistema.")
    locale.setlocale(locale.LC_ALL, '')

# Carregar os logos usando resource_path e PIL
logo_horizontal_path = resource_path("LOGO_VR.png")
logo_reduzida_path   = resource_path("LOGO_VR_REDUZIDA.png")

try:
    logo_horizontal = Image.open(logo_horizontal_path)
    logo_reduzida   = Image.open(logo_reduzida_path)
    st.logo(image=logo_horizontal, size="large", icon_image=logo_reduzida)
except Exception as e:
    st.error(f"Não foi possível carregar as imagens: {e}")
    
# CEBEÇALHO INÍCIO ===========================================================================================================================
#st.image("LOGO_VR.png", caption="") - pra adicionar imagens
st.markdown('<h1 style="color: orange;">PAINEL do DEPARTAMENTO🚩</h1>', unsafe_allow_html=True)

st.markdown('''
       Página em Construão ''')
# CEBEÇALHO FIM ===============================================================================================================================

# BASE DO EXCEL =================================================================================================================
excel_base2025 = resource_path('base2025.xlsx')
xls = pd.ExcelFile(excel_base2025)

try:
    # Carregar a aba 'departamento' do Excel
    df_departamento = pd.read_excel(xls, sheet_name='departamento')

    # Garantir que as colunas "Data CVCO" e "Data Entrega de obra" estejam em formato datetime
    df_departamento['Data CVCO'] = pd.to_datetime(df_departamento['Data CVCO'], errors='coerce')
    df_departamento['Data Entrega de obra'] = pd.to_datetime(df_departamento['Data Entrega de obra'], errors='coerce')

    # Formatar as colunas de data para o formato dd/mm/aaaa
    df_departamento['Data CVCO'] = df_departamento['Data CVCO'].dt.strftime('%d/%m/%Y')  # Data no formato dd/mm/aaaa
    df_departamento['Data Entrega de obra'] = df_departamento['Data Entrega de obra'].dt.strftime('%d/%m/%Y')  # Data no formato dd/mm/aaaa

    # Filtro de múltiplas seleções para 'Obra Nome' na sidebar
    obras_disponiveis = df_departamento['Empreendimento'].unique().tolist()
    obra_nome_selecionadas = st.sidebar.multiselect("Filtrar por Obra Nome:", obras_disponiveis, default=[])

    # Filtro de "Status" na sidebar com as opções únicas da coluna "Status"
    status_disponiveis = df_departamento['Status'].unique().tolist()
    status_selecionados = st.sidebar.multiselect("Filtrar por Status:", status_disponiveis, default=[])

    # Aplicando os filtros selecionados
    if obra_nome_selecionadas:
        df_departamento = df_departamento[df_departamento['Empreendimento'].isin(obra_nome_selecionadas)]

    if status_selecionados:
        df_departamento = df_departamento[df_departamento['Status'].isin(status_selecionados)]

    # Exibindo apenas até a coluna "Despesa Total Manut"
    df_departamento = df_departamento.loc[:, :'Despesa Manutenção']

    # Verificar se as colunas de "N° Unidades" e "Orçamento (1,5%)" são numéricas
    df_departamento['N° Unidades'] = pd.to_numeric(df_departamento['N° Unidades'], errors='coerce')
    df_departamento['Orçamento (1,5%)'] = pd.to_numeric(df_departamento['Orçamento (1,5%)'], errors='coerce')

    # Exibindo o DataFrame no Streamlit
    st.dataframe(df_departamento, use_container_width=True)

    # Criar o gráfico de colunas para "N° Unidades" ao longo do tempo (soma acumulada)
    if 'N° Unidades' in df_departamento.columns and 'Data Entrega de obra' in df_departamento.columns:
        # Agrupar por Mês e Ano
        df_departamento['Ano-Mês'] = pd.to_datetime(df_departamento['Data Entrega de obra']).dt.to_period('M')

        # Agrupar a soma do "N° Unidades" por ano e mês
        df_unidades_mensal = df_departamento.groupby('Ano-Mês')['N° Unidades'].sum().reset_index()

        # Calcular a soma acumulada
        df_unidades_mensal['Soma Acumulada'] = df_unidades_mensal['N° Unidades'].cumsum()

        # Criar as 4 colunas para o layout conforme solicitado
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

        # Primeira coluna - Filtro de "Data de Início" (25% da tela)
        with col1:
            data_inicio = st.date_input(
                "Selecione a data de início", 
                value=None,  # Definindo o valor padrão como None
                min_value=df_unidades_mensal['Ano-Mês'].min().to_timestamp(), 
                max_value=df_unidades_mensal['Ano-Mês'].max().to_timestamp(),
                format="DD/MM/YYYY"
            )
            
        # Segunda coluna - Filtro de "Data de Fim" (25% da tela)
        with col2:
            data_fim = st.date_input(
                "Selecione a data de fim", 
                value=None,  # Definindo o valor padrão como None
                min_value=df_unidades_mensal['Ano-Mês'].min().to_timestamp(), 
                max_value=df_unidades_mensal['Ano-Mês'].max().to_timestamp(),
                format="DD/MM/YYYY"
            )

        # Terceira coluna - Box de "Total de Unidades" (25% da tela)
        with col3:
            total_unidades = df_departamento['N° Unidades'].sum()
            st.metric("N° Total de Unidades", total_unidades)

        # Quarta coluna - Box de "Total Orçamento" (25% da tela)
        with col4:
            # Garantir que os valores de "Orçamento (1,5%)" sejam numéricos
            orcamento_total = df_departamento['Orçamento (1,5%)'].sum()

            # Verificar se orcamento_total é um valor numérico
            if pd.notnull(orcamento_total):
                orcamento_formatado = locale.currency(orcamento_total, grouping=True, symbol="R$")
                st.metric("Total de Orçamento (1,5%)", orcamento_formatado)

            else:
                st.metric("Total de Orçamento (1,5%)", f"R$ 0,00")


        # Criar nova subdivisão dentro de col1 e col2 para o gráfico ocupar 50% do espaço
        col1_2, col3_4 = st.columns([1, 1])  # O gráfico ocupará col1_2, enquanto col3_4 ficará vazio

        with col1_2:
            # Exibindo o intervalo de datas selecionadas
            data_inicio = pd.to_datetime(data_inicio).strftime('%d/%m/%Y')
            data_fim = pd.to_datetime(data_fim).strftime('%d/%m/%Y')
            st.write(f"Período selecionado: {data_inicio} até {data_fim}")

            # Filtrando os dados para o gráfico de acordo com o intervalo de datas selecionado
            df_unidades_mensal = df_unidades_mensal[
                (df_unidades_mensal['Ano-Mês'].dt.to_timestamp() >= pd.to_datetime(data_inicio)) & 
                (df_unidades_mensal['Ano-Mês'].dt.to_timestamp() <= pd.to_datetime(data_fim))
            ]

            # Convertendo a coluna 'Ano-Mês' para datetime para uso no gráfico
            df_unidades_mensal['Ano-Mês'] = df_unidades_mensal['Ano-Mês'].dt.to_timestamp()

            # Criando o gráfico de barras para a soma acumulada
            fig_acumulado = px.bar(
                df_unidades_mensal, 
                x='Ano-Mês', 
                y='Soma Acumulada',
                title='Soma Acumulada do Número de Unidades ao Longo do Tempo',
                labels={'Ano-Mês': 'Mês/Ano', 'Soma Acumulada': 'Soma Acumulada de Unidades'},
                text='Soma Acumulada'  # Adiciona os rótulos sobre as barras
            )

            # Ajustando a exibição dos rótulos nas barras
            fig_acumulado.update_traces(texttemplate='%{text}', textposition='outside', showlegend=False)

            # Exibindo o gráfico de barras, agora com largura ajustada para ocupar as duas primeiras colunas
            st.plotly_chart(fig_acumulado, use_container_width=True)

    # Salvando o conteúdo como CSV
    csv_file = 'base2025.csv'
    df_departamento.to_csv(csv_file, index=False, encoding='utf-8')  # Salva sem o índice e com codificação UTF-8

    st.success(f"Planilha salva como '{csv_file}'!")

except FileNotFoundError:
    st.error("O arquivo Excel não foi encontrado. Por favor, verifique o caminho.")
except Exception as e:
    st.error(f"Ocorreu um erro: {e}")
