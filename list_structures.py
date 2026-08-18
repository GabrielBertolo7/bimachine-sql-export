import os

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from bimachine_page import BimachinePage

load_dotenv("config.env")
EMAIL = os.environ["BIMACHINE_EMAIL"]
SENHA = os.environ["BIMACHINE_SENHA"]

PROJETO = "SupremoBI - Preview"

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context("browser_profile", headless=False)
    page = context.pages[0] if context.pages else context.new_page()
    bp = BimachinePage(page)

    bp.abrir()

    if bp.esta_deslogado:
        print("Sessao nao encontrada, fazendo login...")
        bp.fazer_login(EMAIL, SENHA)
        input("Complete o 2FA na janela do navegador e pressione Enter aqui para continuar...")

    bp.selecionar_projeto(PROJETO)
    bp.abrir_dados_e_integracoes()

    linhas = bp.listar_linhas_estruturas()
    print(f"Total de linhas encontradas: {len(linhas)}\n")

    extraiveis = 0
    for linha in linhas:
        nome, tipo, origem = bp.ler_info_linha(linha)
        print(f"Nome: {nome!r:45} Tipo: {tipo!r:15} Origem: {origem!r}")
        if tipo == "Dados" and origem == "Database":
            extraiveis += 1

    print(f"\nTotal extraivel (Tipo == 'Dados' e Origem == 'Database'): {extraiveis}")

    context.close()
