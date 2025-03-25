import sys
import os

# Adiciona o diretório extraído em modo frozen ao sys.path
if getattr(sys, 'frozen', False):
    sys.path.insert(0, sys._MEIPASS)
else:
    sys.path.insert(0, os.path.dirname(__file__))

def resource_path(relative_path):
    """
    Retorna o caminho absoluto de 'relative_path', seja em desenvolvimento ou quando empacotado.
    """
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(__file__), relative_path)

import streamlit as st
import pandas as pd
import datetime
import base64
import plotly.express as px
import plotly.graph_objects as go
import os
from io import BytesIO
from PIL import Image

# ------------------------------------------------------------------------------
# Configuração da página
# ------------------------------------------------------------------------------
st.set_page_config(
    page_icon=resource_path("Home.jpg"),
    layout='wide',
    page_title="Pós Obra - Contrapartidas"
)

# Carregar logos
logo_horizontal_path = resource_path("LOGO_VR.png")
logo_reduzida_path = resource_path("LOGO_VR_REDUZIDA.png")
try:
    logo_horizontal = Image.open(logo_horizontal_path)
    logo_reduzida = Image.open(logo_reduzida_path)
    st.logo(image=logo_horizontal, size="large", icon_image=logo_reduzida)
except Exception as e:
    st.error(f"Não foi possível carregar as imagens: {e}")

# ------------------------------------------------------------------------------
# Credenciais
# ------------------------------------------------------------------------------
USERS = {
    "lucas.oliveira": "lucas123",
    "sergio.lopes": "sergio123"
}

# ------------------------------------------------------------------------------
# Colunas (Dados Base – somente as colunas desejadas)
# ------------------------------------------------------------------------------
COLUNAS = [
    "id_pai", "codigo_sequencia", "Status", "Projeto", "Tipo de Serviço",
    "Data Início Contrapartida (Previsto)", "Data Término Contrapartida (Previsto)",
    "Valor Viabilidade", "Orçamento", "% Execução", "Gasto Real",
    "Modo de Medição", "Comentários"
]

# ------------------------------------------------------------------------------
# Funções Auxiliares
# ------------------------------------------------------------------------------
def formatar_data(data: datetime.date) -> str:
    if not data:
        return ""
    return data.strftime("%d/%m/%Y")

def gerar_excel_download(df: pd.DataFrame, nome_arquivo: str = "dados_exportados.xlsx") -> str:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        # Planilha 1: Dados Base (somente as colunas definidas)
        df[COLUNAS].to_excel(writer, index=False, sheet_name='Dados Base')
        # Planilha 2: Resumo Financeiro
        df_fin = df.copy()
        df_fin["Saldo"] = df_fin["Orçamento"] - df_fin["Gasto Real"]
        df_fin["% Gasto"] = df_fin.apply(lambda x: round((x["Gasto Real"] / x["Orçamento"]) * 100, 2)
                                         if x["Orçamento"] > 0 else 0, axis=1)
        df_fin_exibir = df_fin[["codigo_sequencia", "Projeto", "Orçamento", "Gasto Real", "Saldo", "% Gasto"]]
        df_fin_exibir.to_excel(writer, index=False, sheet_name='Resumo Financeiro')
        # Planilha 3: Desembolso Consolidado
        final_df_list = []
        for projeto, df_disp in st.session_state.desembolso.items():
            projeto_df = df[df["Projeto"] == projeto]
            if projeto_df.empty:
                continue
            orcamento = projeto_df.iloc[0]["Orçamento"]
            perc_list = df_disp["Percentual (%)"].tolist()
            soma = sum(perc_list)
            if soma != 100:
                perc_normalizado = [round((p/soma)*100, 1) for p in perc_list]
            else:
                perc_normalizado = perc_list
            parcelas = [round((p/100)*orcamento, 2) for p in perc_normalizado]
            df_final = pd.DataFrame({
                "Mês": df_disp["Mês"],
                "Percentual (%)": perc_normalizado,
                "Parcela (R$)": parcelas
            })
            df_final["Projeto"] = projeto
            final_df_list.append(df_final)
        if final_df_list:
            df_consol = pd.concat(final_df_list)
            df_consol_group = df_consol.groupby("Mês").agg({"Parcela (R$)":"sum"}).reset_index()
        else:
            df_consol_group = pd.DataFrame()
        df_consol_group.to_excel(writer, index=False, sheet_name='Desembolso Consolidado')
        # Planilha 4: Resumo Mensal por Projeto
        if not df_consol_group.empty and final_df_list:
            df_break = df_consol.groupby(["Mês", "Projeto"])["Parcela (R$)"].sum().reset_index()
            total_by_month = df_break.groupby("Mês")["Parcela (R$)"].transform('sum')
            df_break["Percentual (%)"] = (df_break["Parcela (R$)"] / total_by_month * 100).round(1)
        else:
            df_break = pd.DataFrame()
        df_break.to_excel(writer, index=False, sheet_name='Resumo Mensal')
    b64 = base64.b64encode(buffer.getvalue()).decode()
    return f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{nome_arquivo}">Baixar {nome_arquivo}</a>'

def load_data() -> pd.DataFrame:
    if os.path.exists("contrapartidas.csv"):
        df = pd.read_csv("contrapartidas.csv", sep=";")
        # Garantir que todas as colunas definidas existam
        for col in COLUNAS:
            if col not in df.columns:
                df[col] = ""
        # Converter apenas as colunas de data que permanecem
        date_cols = [
            "Data Início Contrapartida (Previsto)", "Data Término Contrapartida (Previsto)"
        ]
        for col in date_cols:
            if col in df.columns and df[col].dtype != 'datetime64[ns]':
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
        return df
    else:
        return pd.DataFrame(columns=COLUNAS)

def persist_data():
    st.session_state.df_principal.to_csv("contrapartidas.csv", index=False, sep=";")

# ------------------------------------------------------------------------------
# Função para reorganizar os códigos sequenciais
# ------------------------------------------------------------------------------
def reorganizar_codigos():
    df = st.session_state.df_principal.copy()
    # Reorganiza os projetos (id_pai nulo)
    projects = df[df["id_pai"].isnull()].copy().sort_index()
    new_codes = {}
    seq = 1
    for idx in projects.index:
        new_code = str(seq)
        new_codes[df.loc[idx, "Projeto"]] = new_code
        df.loc[idx, "codigo_sequencia"] = new_code
        seq += 1
    # Reorganiza as subetapas para cada projeto
    subs = df[df["id_pai"].notnull()].copy().sort_index()
    for projeto, code in new_codes.items():
        subs_proj = df[(df["id_pai"].notnull()) & (df["Projeto"] == projeto)]
        subs_proj = subs_proj.sort_values(by="codigo_sequencia")
        seq_sub = 1
        for idx in subs_proj.index:
            df.loc[idx, "codigo_sequencia"] = f"{code}.{seq_sub}"
            seq_sub += 1
    st.session_state.df_principal = df.copy()
    persist_data()
    st.session_state.last_version = df.copy()

# ------------------------------------------------------------------------------
# Inicialização do State
# ------------------------------------------------------------------------------
if "df_principal" not in st.session_state:
    st.session_state.df_principal = load_data()
if "editing_enabled" not in st.session_state:
    st.session_state.editing_enabled = False
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "show_login" not in st.session_state:
    st.session_state.show_login = False
if "versoes" not in st.session_state:
    st.session_state.versoes = []
if "last_version" not in st.session_state:
    st.session_state.last_version = st.session_state.df_principal.copy()
if "edit_in_progress" not in st.session_state:
    st.session_state.edit_in_progress = False
if "edit_idx" not in st.session_state:
    st.session_state.edit_idx = None
if "desembolso" not in st.session_state:
    st.session_state.desembolso = {}

# ------------------------------------------------------------------------------
# Sidebar de Edição
# ------------------------------------------------------------------------------
def sidebar_edicao():
    with st.sidebar:
        st.header("Controle de Edição")
        if not st.session_state.editing_enabled:
            if st.button("Ativar Modo de Edição"):
                st.session_state.show_login = True
            if st.session_state.show_login and not st.session_state.logged_in:
                with st.form(key="login_form"):
                    usuario = st.text_input("Usuário", key="usuario_edicao")
                    senha = st.text_input("Senha", type="password", key="senha_edicao")
                    if st.form_submit_button("Confirmar Login"):
                        if usuario in USERS and senha == USERS[usuario]:
                            st.session_state.logged_in = True
                            st.session_state.editing_enabled = True
                            st.session_state.show_login = False
                            st.success("Modo de edição ativado!")
                            persist_data()
                        else:
                            st.error("Usuário ou senha incorretos!")
        else:
            if st.button("Desativar Modo de Edição"):
                st.session_state.editing_enabled = False
                st.session_state.logged_in = False
                st.success("Modo de edição desativado!")
        st.write("Modo de edição:", st.session_state.editing_enabled)

# ------------------------------------------------------------------------------
# Funções de Adição/Exclusão
# ------------------------------------------------------------------------------
def excluir_projeto(idx):
    df = st.session_state.df_principal
    projeto_val = df.loc[idx, "Projeto"]
    df = df[(df["Projeto"] != projeto_val) | (df["id_pai"].notnull())]
    st.session_state.df_principal = df.reset_index(drop=True)
    reorganizar_codigos()
    st.success("Projeto excluído!")

def excluir_subetapa(idx):
    df = st.session_state.df_principal
    st.session_state.df_principal = df.drop(idx).reset_index(drop=True)
    reorganizar_codigos()
    st.success("Subetapa excluída!")

def adicionar_projeto_callback():
    df = st.session_state.df_principal
    novo_id = 1 if df.empty else (df["codigo_sequencia"].count() + 1)
    novo_codigo = str(novo_id)
    novo_projeto = {
        "id_pai": None,
        "codigo_sequencia": novo_codigo,
        "Status": "Não Iniciado",
        "Projeto": "Novo Projeto",
        "Tipo de Serviço": "",
        "Data Início Contrapartida (Previsto)": datetime.date.today(),
        "Data Término Contrapartida (Previsto)": datetime.date.today(),
        "Valor Viabilidade": 0,
        "Orçamento": 0,
        "% Execução": 0,
        "Gasto Real": 0,
        "Modo de Medição": "Por % Execução",
        "Comentários": ""
    }
    st.session_state.df_principal = pd.concat([df, pd.DataFrame([novo_projeto])], ignore_index=True)
    reorganizar_codigos()
    st.success("Projeto adicionado!")

def adicionar_subetapa_callback(projeto_val):
    df = st.session_state.df_principal
    if df.empty:
        st.warning("Nenhum projeto para associar subetapas.")
        return
    novo_id = df["codigo_sequencia"].count() + 1
    parent = df[df["Projeto"] == projeto_val].iloc[0]
    sub_count = len(df[df["Projeto"] == projeto_val]) - 1
    novo_codigo = f"{parent['codigo_sequencia']}.{sub_count+1}"
    nova_subetapa = {
        "id_pai": projeto_val,
        "codigo_sequencia": novo_codigo,
        "Status": "Não Iniciado",
        "Projeto": parent["Projeto"],
        "Tipo de Serviço": "",
        "Data Início Contrapartida (Previsto)": parent["Data Início Contrapartida (Previsto)"],
        "Data Término Contrapartida (Previsto)": parent["Data Término Contrapartida (Previsto)"],
        "Valor Viabilidade": 0,
        "Orçamento": 0,
        "% Execução": 0,
        "Gasto Real": 0,
        "Modo de Medição": "Por % Execução",
        "Comentários": ""
    }
    st.session_state.df_principal = pd.concat([df, pd.DataFrame([nova_subetapa])], ignore_index=True)
    reorganizar_codigos()
    st.success("Subetapa adicionada!")

# ------------------------------------------------------------------------------
# Controle de Edição Inline
# ------------------------------------------------------------------------------
def iniciar_edicao(idx):
    st.session_state.edit_in_progress = True
    st.session_state.edit_idx = idx

def cancelar_edicao():
    st.session_state.edit_in_progress = False
    st.session_state.edit_idx = None

def exibir_form_edicao_inline(idx):
    df = st.session_state.df_principal
    row = df.loc[idx]
    st.markdown("##### Editando registro")
    with st.form(key=f"form_edicao_{idx}"):
        if pd.isnull(row.get("id_pai")):
            novo_projeto = st.text_input("Projeto", value=row.get("Projeto", ""))
        else:
            st.write("Projeto:", row.get("Projeto", ""))
            novo_projeto = row.get("Projeto", "")
        novo_tipo = st.text_input("Tipo de Serviço", value=row.get("Tipo de Serviço", ""))
        status_options = ["Não Iniciado", "Planejamento", "Em Andamento", "Concluído"]
        status_index = status_options.index(row["Status"]) if row["Status"] in status_options else 0
        novo_status = st.selectbox("Status", status_options, index=status_index)
        default_inicio_cont = row.get("Data Início Contrapartida (Previsto)")
        default_inicio_cont_str = formatar_data(default_inicio_cont) if default_inicio_cont else datetime.date.today().strftime("%d/%m/%Y")
        label_inicio = "Data Início Contrapartida (Previsto)" if pd.isnull(row.get("id_pai")) else "Data Início Subetapa (Previsto)"
        novo_data_inicio_cont_prev_str = st.text_input(label_inicio, value=default_inicio_cont_str)
        default_termino_cont = row.get("Data Término Contrapartida (Previsto)")
        default_termino_cont_str = formatar_data(default_termino_cont) if default_termino_cont else datetime.date.today().strftime("%d/%m/%Y")
        label_termino = "Data Término Contrapartida (Previsto)" if pd.isnull(row.get("id_pai")) else "Data Término Subetapa (Previsto)"
        novo_data_termino_cont_prev_str = st.text_input(label_termino, value=default_termino_cont_str)
        if pd.isnull(row.get("id_pai")):
            novo_valor_viabilidade = st.number_input("Viabilidade", min_value=0.0, value=float(row.get("Valor Viabilidade", 0)), step=100.0)
        else:
            novo_valor_viabilidade = row.get("Valor Viabilidade", 0)
        novo_orcamento = st.number_input("Orçamento", min_value=0.0, value=float(row.get("Orçamento", 0)), step=1000.0)
        modo_atual = row.get("Modo de Medição", "Por % Execução")
        modo_options = ["Por % Execução", "Por Gasto Real"]
        modo_index = 0 if modo_atual == "Por % Execução" else 1
        modo_medicao = st.radio("Modo de Medição", options=modo_options, index=modo_index, key=f"modo_medicao_{idx}")
        if modo_medicao == "Por % Execução":
            valor_exec = float(row.get("% Execução", 0))
            novo_execucao = st.number_input("% Execução", min_value=0.0, max_value=100.0, value=valor_exec, step=1.0, key=f"execucao_{idx}")
            gasto_calculado = round((novo_execucao/100.0) * novo_orcamento, 2)
            st.number_input("Gasto Real (calculado)", value=gasto_calculado, disabled=True, key=f"gasto_calc_{idx}")
        else:
            valor_gasto = float(row.get("Gasto Real", 0))
            novo_gasto = st.number_input("Gasto Real", min_value=0.0, value=valor_gasto, step=100.0, key=f"gasto_{idx}")
            exec_calc = round((novo_gasto/novo_orcamento)*100, 2) if novo_orcamento > 0 else 0
            st.number_input("% Execução (calculado)", value=exec_calc, disabled=True, key=f"execucao_calc_{idx}")
        novos_comentarios = st.text_area("Comentários", value=row.get("Comentários", ""))
        try:
            novo_data_inicio_cont_prev = datetime.datetime.strptime(novo_data_inicio_cont_prev_str, "%d/%m/%Y").date()
        except Exception as e:
            st.error(f"{label_inicio} inválida. Utilize o formato DD/MM/YYYY.")
            return
        try:
            novo_data_termino_cont_prev = datetime.datetime.strptime(novo_data_termino_cont_prev_str, "%d/%m/%Y").date()
        except Exception as e:
            st.error(f"{label_termino} inválida. Utilize o formato DD/MM/YYYY.")
            return
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("Salvar Alterações"):
                df.at[idx, "Projeto"] = novo_projeto
                df.at[idx, "Tipo de Serviço"] = novo_tipo
                df.at[idx, "Status"] = novo_status
                df.at[idx, "Data Início Contrapartida (Previsto)"] = novo_data_inicio_cont_prev
                df.at[idx, "Data Término Contrapartida (Previsto)"] = novo_data_termino_cont_prev
                if pd.isnull(row.get("id_pai")):
                    df.at[idx, "Valor Viabilidade"] = novo_valor_viabilidade
                df.at[idx, "Orçamento"] = novo_orcamento
                if modo_medicao == "Por % Execução":
                    df.at[idx, "% Execução"] = novo_execucao
                    df.at[idx, "Gasto Real"] = gasto_calculado
                else:
                    df.at[idx, "Gasto Real"] = novo_gasto
                    df.at[idx, "% Execução"] = exec_calc
                df.at[idx, "Modo de Medição"] = modo_medicao
                df.at[idx, "Comentários"] = novos_comentarios
                st.session_state.df_principal = df.copy()
                persist_data()
                st.success("Alterações salvas!")
                cancelar_edicao()
        with col2:
            if st.form_submit_button("Fechar Edição"):
                cancelar_edicao()
                st.info("Edição cancelada.")

# ------------------------------------------------------------------------------
# Exibição do Cronograma Físico com Filtros
# ------------------------------------------------------------------------------
def exibir_cronograma_fisico():
    st.subheader("⏱️Cronograma Físico")
    df = st.session_state.df_principal.copy()
    if df.empty:
        st.info("Nenhum projeto cadastrado. Utilize 'Adicionar Projeto' para incluir.")
        return

    with st.container():
        st.markdown("### Filtros do Cronograma Físico")
        projetos = sorted(df["Projeto"].dropna().unique())
        projetos_filter = st.multiselect("Projeto", options=projetos, default=[])
        if projetos_filter:
            df = df[df["Projeto"].isin(projetos_filter)]
        status_options = ["Não Iniciado", "Planejamento", "Em Andamento", "Concluído"]
        status_filter = st.multiselect("Status", options=status_options, default=[])
        if status_filter:
            df = df[df["Status"].isin(status_filter)]
        if not df["Data Início Contrapartida (Previsto)"].dropna().empty:
            df["Mes"] = pd.to_datetime(df["Data Início Contrapartida (Previsto)"]).dt.month
            df["Ano"] = pd.to_datetime(df["Data Início Contrapartida (Previsto)"]).dt.year
            month_map = {1:"janeiro", 2:"fevereiro", 3:"março", 4:"abril", 5:"maio", 6:"junho",
                         7:"julho", 8:"agosto", 9:"setembro", 10:"outubro", 11:"novembro", 12:"dezembro"}
            df["Mes_Nome"] = df["Mes"].map(month_map)
            meses_available = [m for m in month_map.values() if m in df["Mes_Nome"].unique()]
            meses_filter = st.multiselect("Período (Mês)", options=meses_available, default=[])
            if meses_filter:
                df = df[df["Mes_Nome"].isin(meses_filter)]
            anos_available = sorted(df["Ano"].unique())
            anos_filter = st.multiselect("Período (Ano)", options=[str(y) for y in anos_available], default=[])
            if anos_filter:
                df = df[df["Ano"].isin([int(y) for y in anos_filter])]
    principais = df[df["id_pai"].isnull()].copy()
    for idx, row in principais.iterrows():
        with st.expander(f"Código: {row.get('codigo_sequencia', '')} | {row.get('Projeto', '')} | {row.get('Tipo de Serviço', '')}", expanded=False):
            st.write("**Status:**", row.get("Status", ""))
            st.write("**Data Início Contrapartida (Previsto):**", formatar_data(row.get("Data Início Contrapartida (Previsto)")))
            st.write("**Data Término Contrapartida (Previsto):**", formatar_data(row.get("Data Término Contrapartida (Previsto)")))
            st.write("**Viabilidade:**", row.get("Valor Viabilidade", 0))
            st.write("**Orçamento:** R$", row.get("Orçamento", 0))
            st.write("**Gasto Real:** R$", row.get("Gasto Real", 0))
            st.write("**% Execução:**", row.get("% Execução", 0), "%")
            st.write("**Comentários:**", row.get("Comentários", ""))
            if st.session_state.editing_enabled:
                c1, c2, c3 = st.columns(3)
                with c1:
                    if st.button("Editar Projeto", key=f"editar_projeto_{idx}"):
                        iniciar_edicao(idx)
                with c2:
                    if st.button("Adicionar Subetapa", key=f"add_sub_{idx}"):
                        adicionar_subetapa_callback(row["Projeto"])
                with c3:
                    if st.button("Excluir Projeto", key=f"excluir_projeto_{idx}"):
                        excluir_projeto(idx)
            if st.session_state.edit_in_progress and st.session_state.edit_idx == idx:
                exibir_form_edicao_inline(idx)
            subetapas = df[df["id_pai"] == row["id"]]
            if not subetapas.empty:
                if st.checkbox("Mostrar subetapas", key=f"mostrar_sub_{row.get('id')}"):
                    for idx_sub, row_sub in subetapas.iterrows():
                        st.markdown(f"**Código: {row_sub.get('codigo_sequencia', '')} | {row_sub.get('Projeto', '')} | {row_sub.get('Tipo de Serviço', '')}**")
                        st.write("Status:", row_sub.get("Status", ""))
                        st.write("Data Início Subetapa (Previsto):", formatar_data(row_sub.get("Data Início Contrapartida (Previsto)")))
                        st.write("Data Término Subetapa (Previsto):", formatar_data(row_sub.get("Data Término Contrapartida (Previsto)")))
                        st.write("Orçamento: R$", row_sub.get("Orçamento", 0))
                        st.write("Gasto Real: R$", row_sub.get("Gasto Real", 0))
                        st.write("% Execução:", row_sub.get("% Execução", 0), "%")
                        st.write("Comentários:", row_sub.get("Comentários", ""))
                        if st.session_state.editing_enabled:
                            sc1, sc2 = st.columns(2)
                            with sc1:
                                if st.button("Editar Subetapa", key=f"editar_sub_{idx_sub}"):
                                    iniciar_edicao(idx_sub)
                            with sc2:
                                if st.button("Excluir Subetapa", key=f"excluir_sub_{idx_sub}"):
                                    excluir_subetapa(idx_sub)
                            if st.session_state.edit_in_progress and st.session_state.edit_idx == idx_sub:
                                exibir_form_edicao_inline(idx_sub)
    st.markdown('-----')

# ------------------------------------------------------------------------------
# Gráficos Gantt
# ------------------------------------------------------------------------------
def exibir_gantt_fisico():
    st.markdown("### 🗓️ Planejamento")
    df_version = st.session_state.last_version if "last_version" in st.session_state else st.session_state.df_principal
    if df_version.empty:
        st.info("Sem dados para exibir o Gantt.")
        return
    # Filtro de Ano para o Gantt (default vazio)
    if not df_version["Data Início Contrapartida (Previsto)"].dropna().empty:
        df_version["Ano"] = pd.to_datetime(df_version["Data Início Contrapartida (Previsto)"]).dt.year
        anos_available = sorted(df_version["Ano"].unique())
        anos_filter = st.multiselect("Ano (Gantt)", options=[str(a) for a in anos_available], default=[])
        if anos_filter:
            df_version = df_version[df_version["Ano"].isin([int(a) for a in anos_filter])]
    df_etapas = df_version[df_version["id_pai"].isnull()]
    projeto_opcoes = [''] + sorted(df_etapas["Projeto"].dropna().unique().tolist())
    projeto_selecionado = st.selectbox("Selecione o Projeto para Desembolso (Etapas)", options=projeto_opcoes, index=0)
    if projeto_selecionado:
        df_version = df_version[df_version["Projeto"] == projeto_selecionado]
    filtro = st.selectbox("Filtrar Gantt", options=["Etapa e Subetapa", "Só Etapa", "Só Subetapa"])
    df_version = df_version.copy()
    df_version["Tipo"] = df_version["id_pai"].apply(lambda x: "Subetapa" if pd.notnull(x) else "Etapa")
    if filtro == "Só Etapa":
        df_version = df_version[df_version["Tipo"] == "Etapa"]
    elif filtro == "Só Subetapa":
        df_version = df_version[df_version["Tipo"] == "Subetapa"]
    gantt_data = []
    for _, row in df_version.iterrows():
        inicio = row.get("Data Início Contrapartida (Previsto)")
        fim = row.get("Data Término Contrapartida (Previsto)")
        if inicio and fim:
            duration = (fim - inicio).days
            gantt_data.append({
                "Projeto": row.get("Projeto", ""),
                "Codigo": row.get("codigo_sequencia", ""),
                "TipoServico": row.get("Tipo de Serviço", ""),
                "Tipo": row.get("Tipo", ""),
                "Start": inicio,
                "Finish": fim,
                "Duration": duration,
                "Execucao": row.get("% Execução", 0)
            })
    if not gantt_data:
        st.info("Não há datas definidas para exibir o Gantt.")
        return
    df_gantt = pd.DataFrame(gantt_data)
    def sort_key(codigo):
        try:
            return tuple(int(x) for x in str(codigo).split('.'))
        except:
            return (999,)
    df_gantt["SortKey"] = df_gantt["Codigo"].apply(sort_key)
    df_gantt = df_gantt.sort_values(by="SortKey")
    reference_date = df_gantt["Start"].min()
    df_gantt["Start_num"] = df_gantt["Start"].apply(lambda d: (d - reference_date).days)
    color_palette = px.colors.qualitative.Plotly
    unique_etapas = df_gantt[df_gantt["Tipo"]=="Etapa"]["Codigo"].unique()
    etapa_colors = {codigo: color_palette[i % len(color_palette)] for i, codigo in enumerate(unique_etapas)}
    def lighten_color(hex_color, amount=0.5):
        hex_color = hex_color.lstrip('#')
        lv = len(hex_color)
        rgb = tuple(int(hex_color[i:i+lv//3], 16) for i in range(0, lv, lv//3))
        new_rgb = tuple(int(c + (255-c)*amount) for c in rgb)
        return '#%02x%02x%02x' % new_rgb
    df_gantt.loc[df_gantt["Tipo"]=="Etapa", "Label"] = df_gantt[df_gantt["Tipo"]=="Etapa"].apply(
        lambda r: f"Código: {r.get('codigo_sequencia','')} | {r['Projeto']} | {r['TipoServico']}", axis=1
    )
    df_gantt.loc[df_gantt["Tipo"]=="Subetapa", "Label"] = df_gantt[df_gantt["Tipo"]=="Subetapa"].apply(
        lambda r: f"Código: {r.get('codigo_sequencia','')} | {r['Projeto']} | {r['TipoServico']}", axis=1
    )
    labels_order = df_gantt["Label"].unique().tolist()
    fig = go.Figure()
    df_etapa_plot = df_gantt[df_gantt["Tipo"]=="Etapa"]
    for _, row in df_etapa_plot.iterrows():
        fig.add_trace(go.Bar(
            x=[row["Duration"]],
            y=[row["Label"]],
            base=[row["Start_num"]],
            orientation="h",
            marker_color=etapa_colors.get(row.get("codigo_sequencia",""), "#636efa"),
            width=0.8,
            text=f'{row["Execucao"]}%',
            textposition="inside"
        ))
    df_sub_plot = df_gantt[df_gantt["Tipo"]=="Subetapa"]
    for _, row in df_sub_plot.iterrows():
        parent_codigo = str(row.get("Codigo", "")).split('.')[0]
        parent_color = etapa_colors.get(parent_codigo, "#636efa")
        sub_color = lighten_color(parent_color, amount=0.5)
        fig.add_trace(go.Bar(
            x=[row["Duration"]],
            y=[row["Label"]],
            base=[row["Start_num"]],
            orientation="h",
            marker_color=sub_color,
            width=0.4,
            text=f'{row["Execucao"]}%',
            textposition="inside"
        ))
    start_date = df_gantt["Start"].min()
    end_date = df_gantt["Finish"].max()
    monthly_ticks = []
    current = datetime.date(start_date.year, start_date.month, 1)
    while current <= end_date:
        monthly_ticks.append((current - reference_date).days)
        y = current.year
        m = current.month + 1
        if m > 12:
            m = 1
            y += 1
        current = datetime.date(y, m, 1)
    tick_vals = monthly_ticks
    tick_text = [(reference_date + datetime.timedelta(days=val)).strftime("%m/%Y") for val in tick_vals]
    fig.update_layout(
        barmode='stack',
        yaxis={'categoryorder': 'array', 'categoryarray': labels_order, 'autorange': 'reversed'},
        xaxis=dict(tickmode='array', tickvals=tick_vals, ticktext=tick_text, title="Data"),
        title="📋 Cronograma de Projetos",
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------------------
# Cronograma Financeiro e Desembolso Mensal
# ------------------------------------------------------------------------------
def exibir_cronograma_financeiro():
    st.subheader("💸 Resumo Financeiro")
    df = st.session_state.df_principal
    if df.empty:
        st.info("Nenhum dado disponível para o Cronograma Financeiro.")
        return

    # Filtros: Projeto e Status (default vazio)
    projetos_resumo = sorted(df["Projeto"].dropna().unique())
    projetos_filter = st.multiselect("Filtrar por Projeto", options=projetos_resumo, default=[])
    if projetos_filter:
        df = df[df["Projeto"].isin(projetos_filter)]
    status_resumo = sorted(df["Status"].dropna().unique())
    status_filter = st.multiselect("Filtrar por Status", options=status_resumo, default=[])
    if status_filter:
        df = df[df["Status"].isin(status_filter)]

    opcao = st.radio("Visualizar:", ["Somente Etapas", "Somente Subetapas", "Todos"])
    if opcao == "Somente Etapas":
        df_fin = df[df["id_pai"].isnull()].copy()
    elif opcao == "Somente Subetapas":
        df_fin = df[df["id_pai"].notnull()].copy()
    else:
        df_fin = df.copy()
    if df_fin.empty:
        st.info("Nenhum registro encontrado para esse filtro.")
        return
    df_fin["Saldo"] = df_fin["Orçamento"] - df_fin["Gasto Real"]
    df_fin["% Gasto"] = df_fin.apply(lambda x: round((x["Gasto Real"] / x["Orçamento"]) * 100, 2)
                                     if x["Orçamento"] > 0 else 0, axis=1)
    st.write("### 📟Tabela Resumo Financeiro")
    df_fin_exibir = df_fin[["codigo_sequencia", "Projeto", "Orçamento", "Gasto Real", "Saldo", "% Gasto"]]
    st.dataframe(df_fin_exibir)
    # Gráfico: Viabilidade vs Orçamento vs Gasto Real (agregado por Projeto)
    df_fin_exibir2 = df_fin[["Projeto", "Valor Viabilidade", "Orçamento", "Gasto Real"]]
    df_grouped = df_fin_exibir2.groupby("Projeto", as_index=False).agg({
        "Valor Viabilidade": "max",
        "Orçamento": "sum",
        "Gasto Real": "sum"
    })
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=df_grouped["Projeto"],
        y=df_grouped["Valor Viabilidade"],
        name="Valor Viabilidade",
        marker_color='#FFDAB9',
        marker_line_color='#FF8C00',
        marker_line_width=1,
        text=df_grouped["Valor Viabilidade"],
        textposition="auto"
    ))
    fig2.add_trace(go.Bar(
        x=df_grouped["Projeto"],
        y=df_grouped["Orçamento"],
        name="Orçamento",
        marker_color='#D3D3D3',
        marker_line_color='#A9A9A9',
        marker_line_width=1,
        text=df_grouped["Orçamento"],
        textposition="auto"
    ))
    fig2.add_trace(go.Bar(
        x=df_grouped["Projeto"],
        y=df_grouped["Gasto Real"],
        name="Gasto Real",
        marker_color='#90EE90',
        marker_line_color='#008000',
        marker_line_width=1,
        text=df_grouped["Gasto Real"],
        textposition="auto"
    ))
    fig2.update_layout(barmode="group", title="🫰 Viabilidade vs Orçamento vs Gasto Real",
                       xaxis_title="Projeto", yaxis_title="Valor (R$)")
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown('-----')
    exibir_cronograma_desembolso()

def exibir_cronograma_desembolso():
    st.subheader("💲Cronograma de Desembolso Mensal")
    df_etapas = st.session_state.df_principal[st.session_state.df_principal["id_pai"].isnull()]
    if df_etapas.empty:
        st.info("Nenhum projeto disponível para desembolso.")
        return
    projeto_opcoes = sorted(df_etapas["Projeto"].dropna().unique())
    projetos_selecionados = st.multiselect("Selecione os Projetos para Desembolso", options=projeto_opcoes, default=[])
    if not projetos_selecionados:
        projetos_selecionados = projeto_opcoes
    final_df_list = []
    for projeto in projetos_selecionados:
        with st.expander(f"Cronograma de Desembolso para: {projeto}", expanded=False):
            if projeto not in st.session_state.desembolso:
                projeto_record = df_etapas[df_etapas["Projeto"] == projeto].iloc[0]
                data_inicio = projeto_record["Data Início Contrapartida (Previsto)"]
                data_termino = projeto_record["Data Término Contrapartida (Previsto)"]
                if not data_inicio or not data_termino:
                    st.error(f"O projeto {projeto} não possui datas de contrapartida definidas.")
                    continue
                meses = []
                current = datetime.date(data_inicio.year, data_inicio.month, 1)
                while current <= datetime.date(data_termino.year, data_termino.month, 1):
                    meses.append(current)
                    y = current.year
                    m = current.month + 1
                    if m > 12:
                        m = 1
                        y += 1
                    current = datetime.date(y, m, 1)
                num_meses = len(meses)
                distrib_default = [round(100/num_meses, 1) for _ in range(num_meses)]
                st.session_state.desembolso[projeto] = pd.DataFrame({
                    "Mês": [mes.strftime("%m/%Y") for mes in meses],
                    "Percentual (%)": distrib_default
                })
            df_editado = st.data_editor(
                st.session_state.desembolso[projeto].copy(),
                num_rows="dynamic",
                key=f"distrib_{projeto}",
                disabled=not st.session_state.editing_enabled
            )
            st.session_state.desembolso[projeto] = df_editado.copy()
            projeto_record = df_etapas[df_etapas["Projeto"] == projeto].iloc[0]
            orcamento = projeto_record["Orçamento"]
            df_distrib = st.session_state.desembolso[projeto]
            perc_list = df_distrib["Percentual (%)"].tolist()
            soma = sum(perc_list)
            if soma != 100:
                perc_normalizado = [round((p/soma)*100, 1) for p in perc_list]
                st.write("**Percentuais normalizados** (soma = 100):", perc_normalizado)
            else:
                perc_normalizado = perc_list
            parcelas = [round((p/100)*orcamento, 2) for p in perc_normalizado]
            df_final = pd.DataFrame({
                "Mês": df_distrib["Mês"],
                "Percentual (%)": perc_normalizado,
                "Parcela (R$)": parcelas
            })
            st.write("### Cronograma de Desembolso Final:")
            st.dataframe(df_final)
            fig = px.bar(df_final, x="Mês", y="Parcela (R$)", text="Percentual (%)", title=f"Desembolso Mensal para {projeto}")
            fig.update_traces(marker_color='gray', marker_line_color='lightgray', marker_line_width=1)
            st.plotly_chart(fig, use_container_width=True)
            df_final["Projeto"] = projeto
            final_df_list.append(df_final)
    if final_df_list:
        st.markdown('-----')
        st.write("## 💳 Cronograma de Desembolso Consolidado")
        df_consol = pd.concat(final_df_list)
        df_consol_group = df_consol.groupby("Mês").agg({"Parcela (R$)":"sum"}).reset_index()
        st.dataframe(df_consol_group)
        fig_consol = px.bar(df_consol_group, x="Mês", y="Parcela (R$)", text="Parcela (R$)", title="💵 Desembolso Mensal Consolidado")
        fig_consol.update_traces(marker_color='orange', marker_line_color='lightcoral', marker_line_width=1)
        st.plotly_chart(fig_consol, use_container_width=True)
        st.write("## 🏙️ Resumo Mensal por Projeto")
        df_break = df_consol.groupby(["Mês", "Projeto"])["Parcela (R$)"].sum().reset_index()
        if not df_break.empty:
            total_by_month = df_break.groupby("Mês")["Parcela (R$)"].transform('sum')
            df_break["Percentual (%)"] = (df_break["Parcela (R$)"] / total_by_month * 100).round(1)
            fig_break = px.bar(df_break, x="Mês", y="Parcela (R$)", color="Projeto",
                               text="Percentual (%)", title="Resumo Mensal por Projeto", barmode="stack")
            st.plotly_chart(fig_break, use_container_width=True)

# ------------------------------------------------------------------------------
# Salvamento de Versão (Excel com múltiplas planilhas)
# ------------------------------------------------------------------------------
def salvar_versao():
    df = st.session_state.df_principal.copy()
    df_fin = df.copy()
    df_fin["Saldo"] = df_fin["Orçamento"] - df_fin["Gasto Real"]
    df_fin["% Gasto"] = df_fin.apply(lambda x: round((x["Gasto Real"] / x["Orçamento"]) * 100, 2)
                                     if x["Orçamento"] > 0 else 0, axis=1)
    df_fin_exibir = df_fin[["codigo_sequencia", "Projeto", "Orçamento", "Gasto Real", "Saldo", "% Gasto"]]
    final_df_list = []
    for projeto, df_disp in st.session_state.desembolso.items():
        projeto_df = df[df["Projeto"] == projeto]
        if projeto_df.empty:
            continue
        orcamento = projeto_df.iloc[0]["Orçamento"]
        perc_list = df_disp["Percentual (%)"].tolist()
        soma = sum(perc_list)
        if soma != 100:
            perc_normalizado = [round((p/soma)*100, 1) for p in perc_list]
        else:
            perc_normalizado = perc_list
        parcelas = [round((p/100)*orcamento, 2) for p in perc_normalizado]
        df_final = pd.DataFrame({
            "Mês": df_disp["Mês"],
            "Percentual (%)": perc_normalizado,
            "Parcela (R$)": parcelas
        })
        df_final["Projeto"] = projeto
        final_df_list.append(df_final)
    if final_df_list:
        df_consol = pd.concat(final_df_list)
        df_consol_group = df_consol.groupby("Mês").agg({"Parcela (R$)":"sum"}).reset_index()
    else:
        df_consol_group = pd.DataFrame()
    if not df_consol_group.empty and final_df_list:
        df_break = df_consol.groupby(["Mês", "Projeto"])["Parcela (R$)"].sum().reset_index()
        total_by_month = df_break.groupby("Mês")["Parcela (R$)"].transform('sum')
        df_break["Percentual (%)"] = (df_break["Parcela (R$)"] / total_by_month * 100).round(1)
    else:
        df_break = pd.DataFrame()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"versao_cronograma_{timestamp}.xlsx"
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df[COLUNAS].to_excel(writer, index=False, sheet_name='Dados Base')
        df_fin_exibir.to_excel(writer, index=False, sheet_name='Resumo Financeiro')
        df_consol_group.to_excel(writer, index=False, sheet_name='Desembolso Consolidado')
        df_break.to_excel(writer, index=False, sheet_name='Resumo Mensal')
    b64 = base64.b64encode(buffer.getvalue()).decode()
    excel_link = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">Baixar {filename}</a>'
    st.session_state.versoes.append(excel_link)
    st.session_state.last_version = df.copy()
    st.success("Versão salva com sucesso!")

# ------------------------------------------------------------------------------
# Abas Principais
# ------------------------------------------------------------------------------
def app_tabs():
    tabs = st.tabs(["Cronograma Físico (Geral)", "Cronograma Financeiro (Geral)"])
    with tabs[0]:
        exibir_cronograma_fisico()
        exibir_gantt_fisico()
    with tabs[1]:
        exibir_cronograma_financeiro()
    st.markdown("---")
    if st.button("Salvar Versão"):
        salvar_versao()
    if st.session_state.versoes:
        st.markdown("### Versões Salvas:")
        for link in st.session_state.versoes:
            st.markdown(link, unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# Tela Principal
# ------------------------------------------------------------------------------
def main():
    st.markdown('<h1 style="color: orange;">Gestão de Contrapartidas 🛣️</h1>', unsafe_allow_html=True)
    st.markdown('')
    sidebar_edicao()
    app_tabs()

if __name__ == "__main__":
    main()
