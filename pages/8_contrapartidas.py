import streamlit as st
import pandas as pd
import datetime
import base64
import plotly.express as px
import plotly.graph_objects as go
import os
from io import BytesIO

# ------------------------------------------------------------------------------
# Configura a página para ocupar toda a largura
# ------------------------------------------------------------------------------
st.set_page_config(layout="wide")

# ------------------------------------------------------------------------------
# Credenciais de exemplo (para produção, utilize um método mais seguro)
# ------------------------------------------------------------------------------
USERS = {
    "admin": "1234",
    "gerente": "senha"
}

# ------------------------------------------------------------------------------
# Lista de colunas necessárias para o DataFrame
# ------------------------------------------------------------------------------
COLUNAS = [
    "id", "id_pai", "codigo_sequencia", "Status", "Projeto", "Tipo de Serviço",
    "Data Início Obra (Prevista)", "Data Entrega Obra (Prevista)",
    "Limite p/ Contratação", "Data Início Contrapartida (Previsto)",
    "Data Início Contrapartida (Real)", "Data Término Contrapartida (Previsto)",
    "Data Término Contrapartida (Real)", "Valor Viabilidade", "Orçamento",
    "% Execução", "Gasto Real", "Modo de Medição", "Comentários"
]

# ------------------------------------------------------------------------------
# Funções Auxiliares
# ------------------------------------------------------------------------------
def formatar_data(data: datetime.date) -> str:
    """Formata uma data no padrão DD/MM/YYYY."""
    if not data:
        return ""
    return data.strftime("%d/%m/%Y")

def gerar_excel_download(df: pd.DataFrame, nome_arquivo: str = "dados_exportados.xlsx") -> str:
    """Gera um link para download do DataFrame em Excel (.xlsx) codificado em Base64."""
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Dados')
    b64 = base64.b64encode(buffer.getvalue()).decode()
    return f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{nome_arquivo}">Baixar {nome_arquivo}</a>'

def load_data() -> pd.DataFrame:
    """Carrega os dados do arquivo 'contrapartidas.csv', ou retorna um DF vazio com as colunas definidas."""
    if os.path.exists("contrapartidas.csv"):
        df = pd.read_csv("contrapartidas.csv", sep=";")
        # Converter as colunas de data
        date_cols = [
            "Data Início Obra (Prevista)", "Data Entrega Obra (Prevista)",
            "Limite p/ Contratação", "Data Início Contrapartida (Previsto)",
            "Data Término Contrapartida (Previsto)"
        ]
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col]).dt.date
        return df
    else:
        return pd.DataFrame(columns=COLUNAS)

def persist_data():
    """Salva o DataFrame atual em 'contrapartidas.csv'."""
    st.session_state.df_principal.to_csv("contrapartidas.csv", index=False, sep=";")

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

# Variáveis para controle de edição inline
if "edit_in_progress" not in st.session_state:
    st.session_state.edit_in_progress = False

if "edit_idx" not in st.session_state:
    st.session_state.edit_idx = None

# ------------------------------------------------------------------------------
# Sidebar: Controle de Edição com Login
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
# Funções de Adição e Exclusão
# ------------------------------------------------------------------------------
def excluir_projeto(idx):
    df = st.session_state.df_principal
    projeto_id = df.loc[idx, "id"]
    df = df[(df["id"] != projeto_id) & (df["id_pai"] != projeto_id)]
    st.session_state.df_principal = df.reset_index(drop=True)
    persist_data()
    st.success("Projeto excluído!")

def excluir_subetapa(idx):
    df = st.session_state.df_principal
    st.session_state.df_principal = df.drop(idx).reset_index(drop=True)
    persist_data()
    st.success("Subetapa excluída!")

def adicionar_projeto_callback():
    df = st.session_state.df_principal
    if df.empty:
        novo_id = 1
    else:
        novo_id = df["id"].max() + 1
    novo_codigo = str(novo_id)
    novo_projeto = {
        "id": novo_id,
        "id_pai": None,
        "codigo_sequencia": novo_codigo,
        "Status": "Planejamento",
        "Projeto": "Novo Projeto",
        "Tipo de Serviço": "",
        "Data Início Obra (Prevista)": datetime.date.today(),
        "Data Entrega Obra (Prevista)": datetime.date.today(),
        "Limite p/ Contratação": datetime.date.today(),
        "Data Início Contrapartida (Previsto)": datetime.date.today(),
        "Data Início Contrapartida (Real)": None,
        "Data Término Contrapartida (Previsto)": datetime.date.today(),
        "Data Término Contrapartida (Real)": None,
        "Valor Viabilidade": 0,
        "Orçamento": 0,
        "% Execução": 0,
        "Gasto Real": 0,
        "Modo de Medição": "Por % Execução",
        "Comentários": ""
    }
    st.session_state.df_principal = pd.concat([df, pd.DataFrame([novo_projeto])], ignore_index=True)
    persist_data()
    st.success("Projeto adicionado!")

def adicionar_subetapa_callback(projeto_id):
    df = st.session_state.df_principal
    if df.empty:
        st.warning("Nenhum projeto para associar subetapas.")
        return
    novo_id = df["id"].max() + 1
    parent = df[df["id"] == projeto_id].iloc[0]
    sub_count = len(df[df["id_pai"] == projeto_id])
    novo_codigo = f"{parent['codigo_sequencia']}.{sub_count+1}"
    nova_subetapa = {
        "id": novo_id,
        "id_pai": projeto_id,
        "codigo_sequencia": novo_codigo,
        "Status": "Planejamento",
        "Projeto": parent["Projeto"],  # O mesmo nome do projeto pai
        "Tipo de Serviço": "",
        "Data Início Obra (Prevista)": None,
        "Data Entrega Obra (Prevista)": None,
        "Limite p/ Contratação": parent["Limite p/ Contratação"],
        "Data Início Contrapartida (Previsto)": parent["Data Início Contrapartida (Previsto)"],
        "Data Início Contrapartida (Real)": None,
        "Data Término Contrapartida (Previsto)": parent["Data Término Contrapartida (Previsto)"],
        "Data Término Contrapartida (Real)": None,
        "Valor Viabilidade": 0,  # Não utilizado nas subetapas
        "Orçamento": 0,
        "% Execução": 0,
        "Gasto Real": 0,
        "Modo de Medição": "Por % Execução",
        "Comentários": ""
    }
    st.session_state.df_principal = pd.concat([df, pd.DataFrame([nova_subetapa])], ignore_index=True)
    persist_data()
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
        # Se for etapa (não tem pai), permitir editar Projeto; senão, apenas exibir como texto.
        if pd.isnull(row.get("id_pai")):
            novo_projeto = st.text_input("Projeto", value=row.get("Projeto", ""))
        else:
            st.write("Projeto:", row.get("Projeto", ""))
            novo_projeto = row.get("Projeto", "")
        
        novo_tipo = st.text_input("Tipo de Serviço", value=row.get("Tipo de Serviço", ""))
        status_options = ["Planejamento", "Em Andamento", "Concluído"]
        status_index = status_options.index(row["Status"]) if row["Status"] in status_options else 0
        novo_status = st.selectbox("Status", status_options, index=status_index)
        
        # Não exibe os campos de Obra (Início/Entrega). Somente Contrapartida/Subetapa
        default_inicio_cont = row.get("Data Início Contrapartida (Previsto)")
        default_inicio_cont_str = formatar_data(default_inicio_cont) if default_inicio_cont else datetime.date.today().strftime("%d/%m/%Y")
        # Se for subetapa, renomeia o rótulo:
        label_inicio = "Data Início Contrapartida (Previsto)" if pd.isnull(row.get("id_pai")) else "Data Início Subetapa (Previsto)"
        novo_data_inicio_cont_prev_str = st.text_input(label_inicio, value=default_inicio_cont_str)
        
        default_termino_cont = row.get("Data Término Contrapartida (Previsto)")
        default_termino_cont_str = formatar_data(default_termino_cont) if default_termino_cont else datetime.date.today().strftime("%d/%m/%Y")
        label_termino = "Data Término Contrapartida (Previsto)" if pd.isnull(row.get("id_pai")) else "Data Término Subetapa (Previsto)"
        novo_data_termino_cont_prev_str = st.text_input(label_termino, value=default_termino_cont_str)
        
        # Se for etapa, permite editar Viabilidade; para subetapas, não.
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
            novo_execucao = st.number_input("% Execução", min_value=0.0, max_value=100.0,
                                            value=valor_exec, step=1.0, key=f"execucao_{idx}")
            gasto_calculado = round((novo_execucao/100.0) * novo_orcamento, 2)
            st.number_input("Gasto Real (calculado)", value=gasto_calculado, disabled=True, key=f"gasto_calc_{idx}")
        else:
            valor_gasto = float(row.get("Gasto Real", 0))
            novo_gasto = st.number_input("Gasto Real", min_value=0.0,
                                         value=valor_gasto, step=100.0, key=f"gasto_{idx}")
            exec_calc = round((novo_gasto/novo_orcamento)*100, 2) if novo_orcamento > 0 else 0
            st.number_input("% Execução (calculado)", value=exec_calc, disabled=True, key=f"execucao_calc_{idx}")
        
        novos_comentarios = st.text_area("Comentários", value=row.get("Comentários", ""))
        
        # Conversão das datas de Contrapartida/Subetapa
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
                # Se for etapa, atualiza Viabilidade; para subetapas, mantém o valor.
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
# Exibição do Cronograma Físico
# ------------------------------------------------------------------------------
def exibir_cronograma_fisico():
    st.subheader("Cronograma Físico (Geral)")
    if st.session_state.editing_enabled:
        if st.button("Adicionar Projeto", on_click=adicionar_projeto_callback):
            pass

    df = st.session_state.df_principal
    if df.empty:
        st.info("Nenhum projeto cadastrado. Utilize 'Adicionar Projeto' para incluir.")
        return

    # Exibição das etapas (projetos sem pai)
    principais = df[df["id_pai"].isna()].copy()
    for idx, row in principais.iterrows():
        with st.expander(f"Código: {row.get('codigo_sequencia','')} | {row.get('Projeto','')} | {row.get('Tipo de Serviço','')}", expanded=False):
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
                        adicionar_subetapa_callback(row["id"])
                with c3:
                    if st.button("Excluir Projeto", key=f"excluir_projeto_{idx}"):
                        excluir_projeto(idx)
            
            if st.session_state.edit_in_progress and st.session_state.edit_idx == idx:
                exibir_form_edicao_inline(idx)
            
            # Exibição das subetapas relacionadas à etapa
            subetapas = df[df["id_pai"] == row["id"]]
            if not subetapas.empty:
                if st.checkbox("Mostrar subetapas", key=f"mostrar_sub_{row.get('id')}"):
                    for idx_sub, row_sub in subetapas.iterrows():
                        st.markdown(f"**Código: {row_sub.get('codigo_sequencia','')} | {row_sub.get('Projeto','')} | {row_sub.get('Tipo de Serviço','')}**")
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

# ------------------------------------------------------------------------------
# Gráficos Gantt
# ------------------------------------------------------------------------------
def exibir_gantt_fisico():
    st.markdown("### Gantt - Cronograma Físico")
    df_version = st.session_state.last_version if "last_version" in st.session_state else st.session_state.df_principal
    if df_version.empty:
        st.info("Sem dados para exibir no Gantt.")
        return

    # Filtro de Projetos: somente nomes de projeto das ETAPAS (id_pai isna())
    df_etapas = df_version[df_version["id_pai"].isna()]
    projetos_opcoes = sorted(df_etapas["Projeto"].dropna().unique())
    projetos_selecionados = st.multiselect("Filtrar por Projeto (Etapas)", options=projetos_opcoes, default=[])
    if projetos_selecionados:
        df_version = df_version[df_version["Projeto"].isin(projetos_selecionados)]
    
    # Filtro para exibir Etapa e Subetapa, só Etapa ou Só Subetapa
    filtro = st.selectbox("Filtrar Gantt", options=["Etapa e Subetapa", "Só Etapa", "Só Subetapa"])
    
    # Cria coluna 'Tipo' para identificar Etapa (id_pai é NaN) e Subetapa (id_pai definido)
    df_version = df_version.copy()
    df_version["Tipo"] = df_version["id_pai"].apply(lambda x: "Subetapa" if pd.notnull(x) else "Etapa")
    
    if filtro == "Só Etapa":
        df_version = df_version[df_version["Tipo"] == "Etapa"]
    elif filtro == "Só Subetapa":
        df_version = df_version[df_version["Tipo"] == "Subetapa"]

    # Monta os dados para o Gantt
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

    # --- Ordenação pelo Código ---
    def sort_key(codigo):
        try:
            return tuple(int(x) for x in str(codigo).split('.'))
        except:
            return (999,)

    df_gantt["SortKey"] = df_gantt["Codigo"].apply(sort_key)
    df_gantt = df_gantt.sort_values(by="SortKey")

    # Converter datas para valores numéricos (dias) a partir da data mínima
    reference_date = df_gantt["Start"].min()
    df_gantt["Start_num"] = df_gantt["Start"].apply(lambda d: (d - reference_date).days)

    # Definir mapeamento de cores para Etapas (baseado no código)
    unique_etapas = df_gantt[df_gantt["Tipo"]=="Etapa"]["Codigo"].unique()
    color_palette = px.colors.qualitative.Plotly
    etapa_colors = {codigo: color_palette[i % len(color_palette)] for i, codigo in enumerate(unique_etapas)}

    # Função para clarear a cor (gera variação mais clara)
    def lighten_color(hex_color, amount=0.5):
        hex_color = hex_color.lstrip('#')
        lv = len(hex_color)
        rgb = tuple(int(hex_color[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))
        new_rgb = tuple(int(c + (255 - c) * amount) for c in rgb)
        return '#%02x%02x%02x' % new_rgb

    # Cria os rótulos conforme solicitado
    df_gantt.loc[df_gantt["Tipo"]=="Etapa", "Label"] = df_gantt[df_gantt["Tipo"]=="Etapa"].apply(
        lambda r: f"Código: {r['Codigo']} | {r['Projeto']} | {r['TipoServico']}", axis=1)
    df_gantt.loc[df_gantt["Tipo"]=="Subetapa", "Label"] = df_gantt[df_gantt["Tipo"]=="Subetapa"].apply(
        lambda r: f"Código: {r['Codigo']} | {r['Projeto']} | {r['TipoServico']}", axis=1)

    # Gerar array de labels na ordem correta
    labels_order = df_gantt["Label"].unique().tolist()

    # Cria o gráfico usando barras horizontais (go.Bar)
    fig = go.Figure()

    # Separa as Etapas e Subetapas (já ordenadas) e plota
    df_etapa_plot = df_gantt[df_gantt["Tipo"]=="Etapa"]
    for _, row in df_etapa_plot.iterrows():
        fig.add_trace(go.Bar(
            x=[row["Duration"]],
            y=[row["Label"]],
            base=[row["Start_num"]],
            orientation="h",
            marker_color=etapa_colors.get(row["Codigo"], "#636efa"),
            width=0.8,
            text=f'{row["Execucao"]}%',
            textposition="inside"
        ))
    df_sub_plot = df_gantt[df_gantt["Tipo"]=="Subetapa"]
    for _, row in df_sub_plot.iterrows():
        parent_codigo = str(row["Codigo"]).split('.')[0]
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
    
    # -- Escala mensal no eixo X --
    start_date = df_gantt["Start"].min()
    end_date = df_gantt["Finish"].max()
    monthly_ticks = []
    current = datetime.date(start_date.year, start_date.month, 1)
    while current <= end_date:
        monthly_ticks.append((current - reference_date).days)
        # incrementa 1 mês
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
        yaxis={
            'categoryorder': 'array',
            'categoryarray': labels_order,
            'autorange': 'reversed'  # <--- REVERSO: Etapas ficam acima das Subetapas
        },
        xaxis=dict(
            tickmode='array',
            tickvals=tick_vals,
            ticktext=tick_text,
            title="Data"
        ),
        title="Gantt - Cronograma Físico",
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------------------
# Aba Cronograma Financeiro (Placeholder)
# ------------------------------------------------------------------------------
def exibir_cronograma_financeiro():
    st.subheader("Cronograma Financeiro (Geral)")
    st.info("Implementação da aba Financeiro pendente.")

# ------------------------------------------------------------------------------
# Salvamento de Versão
# ------------------------------------------------------------------------------
def salvar_versao():
    df = st.session_state.df_principal.copy()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"versao_cronograma_{timestamp}.xlsx"
    excel_link = gerar_excel_download(df, nome_arquivo=filename)
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
    st.title("Gestão de Contrapartidas")
    sidebar_edicao()
    app_tabs()

if __name__ == "__main__":
    main()
