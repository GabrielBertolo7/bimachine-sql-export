import os

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from bimachine_page import BimachinePage

load_dotenv("config.env")
EMAIL = os.environ["BIMACHINE_EMAIL"]
SENHA = os.environ["BIMACHINE_SENHA"]

PROJETO = "SupremoBI - Preview"
STRUCTURE_NAME = "Preview - Dados - Aux Vendedor"

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

    sql = bp.extrair_sql(STRUCTURE_NAME)
    print("SQL capturado:")
    print(sql)

    os.makedirs("output", exist_ok=True)
    with open(f"output/{STRUCTURE_NAME}.sql", "w", encoding="utf-8") as f:
        f.write(sql)
    print(f"Salvo em output/{STRUCTURE_NAME}.sql")

    context.close()
