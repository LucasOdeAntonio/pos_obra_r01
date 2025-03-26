import sys
import os
import streamlit as st
import pandas as pd
from PIL import Image
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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

# Carregar a LOGO_VR
logo_vr_path = resource_path("LOGO_VR.png")
try:
    logo_vr = Image.open(logo_vr_path)
    st.image(logo_vr, caption="", use_container_width=False)
except Exception as e:
    st.error(f"Não foi possível carregar a imagem da LOGO_VR: {e}")

# Título da página
st.markdown('<h1 style="color: orange;">SISTEMA INTRANET - PÓS OBRA 📈</h1>', unsafe_allow_html=True)

# ========================
# FUNÇÃO PARA ENVIAR E-MAIL
# ========================
def enviar_email(nome, avaliacao, comentario):
    """
    Envia um e-mail contendo as informações de feedback.
    """
    
    # Configurações do remetente e destinatário
    email_remetente = "assistencia.tecnica@nvrempreendimentos.com.br"
    senha_remetente = "X&407377994152uk"
    email_destinatario = "lucas.oliveira@nvrempreendimentos.com.br"
    
    # Configuração do servidor SMTP para Outlook
    smtp_server = "smtp.office365.com"
    smtp_port = 587
    
    # Montar o assunto e o corpo do e-mail
    assunto = "Novo Feedback Recebido"
    corpo = (
        f"Olá,\n\n"
        f"Você recebeu um novo feedback do sistema:\n\n"
        f"Nome: {nome}\n"
        f"Avaliação: {avaliacao}\n"
        f"Comentário: {comentario}\n\n"
        f"Atenciosamente,\n"
        f"Sistema de Feedback"
    )
    
    # Criando a estrutura do e-mail (MIME)
    mensagem = MIMEMultipart("alternative")
    mensagem["Subject"] = assunto
    mensagem["From"] = email_remetente
    mensagem["To"] = email_destinatario
    
    # Anexa o texto
    parte_texto = MIMEText(corpo, "plain")
    mensagem.attach(parte_texto)
    
    # Enviar e-mail usando SMTP com TLS
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls(context=context)
            server.login(email_remetente, senha_remetente)
            server.sendmail(email_remetente, email_destinatario, mensagem.as_string())
        st.success("Feedback enviado com sucesso! Um e-mail foi enviado para o administrador.")
    except Exception as e:
        st.error(f"Falha ao enviar e-mail: {e}")

# ========================
# SEÇÃO DE FEEDBACK
# ========================
st.markdown("## Feedback - Por favor nos envie seu feedback sobre o nosso sistema!")

emoticons = {
    1: "😞 (Muito Ruim)",
    2: "😕 (Ruim)",
    3: "😐 (Regular)",
    4: "🙂 (Bom)",
    5: "😃 (Excelente)"
}

with st.form(key='feedback_form'):
    nome = st.text_input("Seu Nome")
    
    avaliacao = st.radio(
        "Avalie nosso sistema",
        options=[1, 2, 3, 4, 5],
        format_func=lambda x: emoticons[x]
    )
    
    comentario = st.text_area("Comentários adicionais")
    submit_button = st.form_submit_button(label='Enviar Feedback')

if submit_button:
    # Ao clicar, a função enviar_email é chamada para disparar o envio do e-mail
    enviar_email(nome, avaliacao, comentario)
