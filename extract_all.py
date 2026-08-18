import datetime
import getpass
import os
import sys
import time

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from bimachine_helpers import sanitize_filename
from bimachine_page import BimachinePage

# Quando empacotado (PyInstaller), os arquivos ficam ao lado do .exe, nao do cwd
BASE_DIR = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.env")
BROWSER_PROFILE_PATH = os.path.join(BASE_DIR, "browser_profile")
OUTPUT_BASE_DIR = os.path.join(BASE_DIR, "output")

if getattr(sys, "frozen", False):
    navegador_embutido = os.path.join(BASE_DIR, "ms-playwright")
    if os.path.isdir(navegador_embutido):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = navegador_embutido

PAUSA_ENTRE_ESTRUTURAS_SEGUNDOS = 2


def carregar_ou_pedir_credenciais():
    """Retorna (email, senha, deve_salvar). deve_salvar so vem True quando as
    credenciais acabaram de ser digitadas agora e ainda nao foram gravadas -
    so gravamos de verdade depois de confirmar que o login funcionou."""
    if os.path.exists(CONFIG_PATH):
        load_dotenv(CONFIG_PATH)
        return os.environ["BIMACHINE_EMAIL"], os.environ["BIMACHINE_SENHA"], False

    print("Primeira vez rodando aqui - preciso do seu login do BIMachine.")
    email = input("Email: ").strip()
    senha = getpass.getpass("Senha (nao aparece na tela enquanto digita): ")
    return email, senha, True


def salvar_credenciais(email, senha):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(f"BIMACHINE_EMAIL={email}\nBIMACHINE_SENHA={senha}\n")
    print(f"Credenciais salvas em {CONFIG_PATH}\n")


def sair_com_erro(mensagem):
    print(f"\n{mensagem}")
    input("\nPressione Enter para fechar...")
    sys.exit(1)


def perguntar_sim_nao(pergunta, padrao=True):
    sufixo = "[S/n]" if padrao else "[s/N]"
    resp = input(f"{pergunta} {sufixo}: ").strip().lower()
    if not resp:
        return padrao
    return resp in ("s", "sim", "y", "yes")


def fazer_login_se_necessario(bp: BimachinePage, email: str, senha: str, deve_salvar_credenciais: bool) -> None:
    if not bp.esta_deslogado:
        return

    print("Sessao nao encontrada, fazendo login...")
    precisa_2fa = bp.fazer_login(email, senha)

    if precisa_2fa:
        input("Complete o 2FA na janela do navegador e pressione Enter aqui para continuar...")
    else:
        print("Login concluido sem necessidade de 2FA (dispositivo ja confiavel).")

    bp.aguardar_redirecionamento_pos_login()

    if bp.esta_deslogado:
        sair_com_erro(
            "ERRO: nao foi possivel entrar no BIMachine.\n"
            "Confira se o email e a senha estao corretos e tente de novo."
        )

    if deve_salvar_credenciais:
        salvar_credenciais(email, senha)


def coletar_estruturas_elegiveis(bp: BimachinePage, pasta_por_tipo: dict) -> list[tuple[str, str]]:
    """Le a tabela de estruturas e retorna, pra cada uma elegivel, (nome, pasta_de_destino)."""
    alvos = []
    for linha in bp.listar_linhas_estruturas():
        nome, tipo, origem = bp.ler_info_linha(linha)
        if tipo == "Dados" and origem == "Database" and "Dados" in pasta_por_tipo:
            alvos.append((nome, pasta_por_tipo["Dados"]))
        elif tipo == "Analítica" and "Analítica" in pasta_por_tipo:
            alvos.append((nome, pasta_por_tipo["Analítica"]))
    return alvos


def extrair_todas(bp: BimachinePage, alvos: list[tuple[str, str]]) -> tuple[list[str], list[str]]:
    sucesso = []
    falha = []

    for i, (nome, pasta) in enumerate(alvos, start=1):
        print(f"[{i}/{len(alvos)}] ({os.path.basename(pasta)}) {nome}...")
        try:
            sql = bp.extrair_sql(nome)
            arquivo = os.path.join(pasta, f"{sanitize_filename(nome)}.sql")
            with open(arquivo, "w", encoding="utf-8") as f:
                f.write(sql)
            sucesso.append(nome)
            print("    OK")
        except Exception as e:
            falha.append(nome)
            print(f"    ERRO: {e}")
            bp.fechar_modais_apos_erro()

        time.sleep(PAUSA_ENTRE_ESTRUTURAS_SEGUNDOS)

    return sucesso, falha


def main():
    print("=== BIMachine SQL Export ===\n")

    email, senha, deve_salvar_credenciais = carregar_ou_pedir_credenciais()

    projeto = input("Nome do projeto (exatamente como aparece em 'Projetos'): ").strip()
    if not projeto:
        sair_com_erro("Nome do projeto e obrigatorio.")

    quer_dados = perguntar_sim_nao("Extrair estruturas do tipo 'Dados'?", padrao=True)
    quer_analitica = perguntar_sim_nao("Extrair estruturas do tipo 'Analítica'?", padrao=True)
    if not quer_dados and not quer_analitica:
        sair_com_erro("Nada selecionado para extrair. Encerrando.")

    mes_ano = datetime.date.today().strftime("%Y-%m")
    pasta_cliente = sanitize_filename(f"{mes_ano} - {projeto}")
    pasta_por_tipo = {}
    if quer_dados:
        pasta_por_tipo["Dados"] = os.path.join(OUTPUT_BASE_DIR, pasta_cliente, "Dados")
    if quer_analitica:
        pasta_por_tipo["Analítica"] = os.path.join(OUTPUT_BASE_DIR, pasta_cliente, "Analitica")

    print("\nIniciando...\n")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(BROWSER_PROFILE_PATH, headless=False)
        page = context.pages[0] if context.pages else context.new_page()
        bp = BimachinePage(page)

        bp.abrir()
        fazer_login_se_necessario(bp, email, senha, deve_salvar_credenciais)

        if not bp.selecionar_projeto(projeto):
            context.close()
            sair_com_erro(
                f"ERRO: projeto '{projeto}' nao encontrado na lista de projetos.\n"
                "Confira se o nome esta exatamente como aparece no menu 'Projetos'."
            )

        bp.abrir_dados_e_integracoes()

        alvos = coletar_estruturas_elegiveis(bp, pasta_por_tipo)
        print(f"{len(alvos)} estruturas para extrair.\n")

        for pasta in pasta_por_tipo.values():
            os.makedirs(pasta, exist_ok=True)

        sucesso, falha = extrair_todas(bp, alvos)

        print(f"\nConcluido: {len(sucesso)} extraidas, {len(falha)} com erro.")
        if falha:
            print("Falharam:")
            for nome in falha:
                print(f"  - {nome}")

        context.close()

    input("\nPressione Enter para fechar...")


if __name__ == "__main__":
    main()
