from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time

def selecionar_todos_registros(driver, wait):
    """
    Seleciona a opção "Todos" no dropdown de status e clica em 'Filtrar'.
    """
    try:
        # 1) Localiza o select de status pelo ID
        select_element = wait.until(
            EC.presence_of_element_located((By.ID, "cbxstatus"))
        )
        select = Select(select_element)

        # 2) Seleciona pelo texto visível "Todos"
        select.select_by_visible_text("Todos")
        print("[INFO] Opção 'Todos' selecionada com sucesso.")

        # 3) Clica no botão 'Filtrar' para aplicar
        filtro_btn = wait.until(
            EC.element_to_be_clickable((By.ID, "btnfiltrasolics"))
        )
        filtro_btn.click()
        print("[INFO] Botão 'Filtrar' clicado com sucesso.")

        return True
    except Exception as e:
        print(f"[ERRO] Falha ao aplicar filtro 'Todos' e clicar em Filtrar: {e}")
        return False

def main():
    driver = webdriver.Chrome()
    wait = WebDriverWait(driver, 15)

    try:
        # Acessar página de login
        driver.get("https://posobravalorreal.com.br/admin/")
        print("[INFO] Página de login aberta.")

        # Login
        username_input = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//input[@type='text' or @name='usuario' or contains(@id, 'user')]")
        ))
        password_input = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//input[@type='password' or @name='senha' or contains(@id, 'pass')]")
        ))
        username_input.send_keys("lucas")
        password_input.send_keys("55365883")
        password_input.send_keys(Keys.RETURN)
        print("[INFO] Login enviado.")

        driver.switch_to.default_content()
        time.sleep(3)

        # Esperar carregamento da tabela
        wait.until(EC.presence_of_element_located((By.XPATH, "//table[@id='tabsolics']")))
        print("[INFO] Página de solicitações carregada.")

        # Aplicar filtro "Todos" uma única vez
        if not selecionar_todos_registros(driver, wait):
            print("[ERRO] Não foi possível aplicar o filtro 'Todos'. Encerrando script.")
            return

        # Aguardar atualização da tabela após aplicar o filtro
        time.sleep(5)

        # Obter todas as linhas da tabela
        linhas = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//table[@id='tabsolics']//tbody/tr")))
        total_linhas = len(linhas)
        print(f"[INFO] Extraindo dados de {total_linhas} solicitações.")

        # Extração dos dados
        dados = []
        for linha in linhas:
            try:
                colunas = linha.find_elements(By.TAG_NAME, "td")
                if len(colunas) < 9:
                    print(f"[WARN] Linha com colunas insuficientes. Pulando.")
                    continue

                # Extração dos dados básicos
                num = colunas[0].text.strip()
                empreendimento = colunas[1].text.strip()
                unidade = colunas[2].text.strip().replace("Comum", "Área Comum")
                bloco = colunas[3].text.strip() if unidade != "Área Comum" else "Área Comum"
                responsavel = colunas[4].text.strip()
                data_abertura = colunas[5].text.strip()
                status = colunas[7].text.strip()

                # Verificar se a pesquisa foi realizada
                try:
                    # Esperar o ícone estar visível
                    pesquisa_icon = WebDriverWait(linha, 2).until(
                        EC.presence_of_element_located((By.XPATH, ".//td[10]//*[name()='svg'][contains(@class, 'fa-check') and contains(@class, 'text-success')]"))
                    )
                    pesquisa = "Pesquisa Realizada"
                except Exception:
                    pesquisa = "Pesquisa Não Realizada"

                # Capturar a data de encerramento (se houver)
                encerramento = ""
                if status.lower() in ["concluída", "improcedente"]:
                    try:
                        encerramento = colunas[6].text.strip()  # Ajuste o índice conforme necessário
                    except:
                        encerramento = ""

                # Capturar a garantia selecionada
                garantia_solicitada = colunas[8].text.strip()  # Ajuste o índice conforme necessário

                # Adicionar dados à lista
                dados.append([
                    num, empreendimento, unidade, bloco, responsavel,
                    data_abertura, encerramento,  # "Data de Encerramento"
                    status, pesquisa, garantia_solicitada
                ])
                print(f"[INFO] Solicitação {num} processada com sucesso.")

            except Exception as ex_linha:
                print(f"[ERRO] Falha ao processar linha: {ex_linha}")

        # Exportar para Excel
        colunas_headers = [
            "N°", "Empreendimento", "Unidade", "Bloco", "Responsável",
            "Data de Abertura", "Encerramento",
            "Status", "Pesquisa", "Garantia Solicitada"
        ]
        df = pd.DataFrame(dados, columns=colunas_headers)
        df.to_excel("engenharia.xlsx", index=False)
        print("[INFO] Dados exportados com sucesso!")

    except Exception as e:
        print(f"[ERRO] Falha na execução principal: {e}")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()