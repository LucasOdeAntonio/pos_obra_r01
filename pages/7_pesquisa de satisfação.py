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


# Configurando Página
st.set_page_config(
    page_icon="Home.jpg",
    layout='wide',
    page_title="Pós Obra - Pesquisa de Satistação"
)

#Logo superior no sidebar, imagem grande e reduzida.
logo_horizontal_path = resource_path("LOGO_VR.png")
logo_reduzida_path   = resource_path("LOGO_VR_REDUZIDA.png")

try:
    logo_horizontal = Image.open(resource_path(logo_horizontal_path))
    logo_reduzida   = Image.open(resource_path(logo_reduzida_path))
    st.logo(image=logo_horizontal, size="large", icon_image=logo_reduzida)
except Exception as e:
    st.error(f"Não foi possível carregar as imagens: {e}")


# CEBEÇALHO INÍCIO ===========================================================================================================================
#st.image("LOGO_VR.png", caption="") - pra adicionar imagens
st.markdown('<h1 style="color: orange;">Pesquisa de Satisfação 🔍</h1>', unsafe_allow_html=True)
#st.image("fluxograma.png", caption="")


def custom_progress_bar(value, height=20, bar_color="orange"):
    """
    Cria uma barra de progresso customizada em HTML/CSS com o rótulo centralizado.
    
    Parâmetros:
      - value: valor percentual (0 a 100)
      - height: altura da barra em pixels
      - bar_color: cor da barra (ex: "orange")
    """
    bar_html = f"""
    <div style="width: 100%; background-color: #e0e0e0; border-radius: 5px; margin: 5px 0;">
        <div style="width: {value}%; background-color: {bar_color}; height: {height}px; line-height: {height}px; border-radius: 5px; text-align: center; color: white; font-weight: bold;">
            {value}%
        </div>
    </div>
    """
    return bar_html

# Lê o arquivo Excel "base2025.xlsx", aba "nps"
df = pd.read_excel(resource_path("base2025.xlsx"), sheet_name="NPS")

# Converter a coluna "Nota" para float (tratando valores inválidos)
df["Nota"] = pd.to_numeric(df["Nota"], errors="coerce")

# Calcular a Média Satisfação usando a fórmula: (soma das notas / 4) * 2
media_satisfacao = (((df["Nota"].sum() / 4) * 2) *10)

# Exibir o Dashboard
st.title("Dashboard de Satisfação")
st.metric("Média Satisfação", f"{media_satisfacao:.2f}%")

st.write("---")
st.subheader("Notas por Pergunta")

# Para cada pergunta, exibir o nome e a barra de progresso customizada com a nota
for index, row in df.iterrows():
    pergunta = row["Pergunta"]
    nota = row["Nota"]
    
    st.write(f"**{pergunta}**")
    # Converter a nota (0 a 5) para valor percentual (0 a 100)
    progress_value = int((nota / 5.0) * 100)
    st.markdown(custom_progress_bar(progress_value), unsafe_allow_html=True)
    st.write(f"Nota: {nota:.2f} de 5.0")
