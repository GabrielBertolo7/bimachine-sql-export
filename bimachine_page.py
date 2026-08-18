"""Page Object para as telas do BIMachine usadas na extracao de SQL das estruturas.

Concentra os seletores e as interacoes com a pagina num unico lugar, pra que os
scripts (extract_all.py, extract_one.py, list_structures.py) nao precisem
conhecer a estrutura HTML do BIMachine, so o que cada acao faz.
"""
from __future__ import annotations

from playwright.sync_api import Locator, Page

from bimachine_helpers import extract_name

URL_COCKPIT = "https://app.bimachine.com/spr/bng/cockpit"

TIMEOUT_BOTAO_3_PONTOS_MS = 60000


class BimachinePage:
    """Interacoes com o BIMachine via um `Page` do Playwright ja aberto numa
    janela (com ou sem sessao ativa)."""

    def __init__(self, page: Page) -> None:
        self._page = page

    # ---------- login ----------

    def abrir(self) -> None:
        self._page.goto(URL_COCKPIT)

    @property
    def esta_deslogado(self) -> bool:
        return "login" in self._page.url

    def fazer_login(self, email: str, senha: str) -> bool:
        """Preenche e envia o formulario de login. Retorna True se a etapa de
        2FA apareceu (o chamador precisa esperar confirmacao manual nesse caso)."""
        self._page.locator('input[name="email"]').fill(email)
        self._page.locator('input[name="password"]').fill(senha)
        self._page.get_by_role("button", name="Entrar").click()

        try:
            self._page.get_by_role("button", name="Verificar").wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False

    def aguardar_redirecionamento_pos_login(self) -> None:
        """Depois do login (com ou sem 2FA), o site pode levar um instante pra
        sair da tela de login; espera um pouco antes de considerar que falhou."""
        try:
            self._page.wait_for_url(lambda url: "login" not in url, timeout=10000)
        except Exception:
            pass

    # ---------- navegacao ----------

    def selecionar_projeto(self, nome: str) -> bool:
        """Abre o menu de projetos, filtra pelo nome e clica na opcao exata.
        Retorna False se o projeto nao aparecer na lista."""
        self._page.locator('[data-tour="navbar-projects"]').click()
        self._page.get_by_placeholder("Pesquisar projetos...").fill(nome)

        opcao = self._page.get_by_text(nome, exact=True)
        try:
            opcao.first.wait_for(state="visible", timeout=5000)
        except Exception:
            return False
        opcao.first.click()
        return True

    def abrir_dados_e_integracoes(self) -> None:
        self._page.get_by_role("link", name="Gerenciar").click()
        self._page.get_by_role("button", name="Dados e Integrações Configure").click()
        self._page.wait_for_selector("table.BngTable")

    # ---------- estruturas ----------

    def listar_linhas_estruturas(self) -> list[Locator]:
        """Retorna os locators de cada linha da tabela de estruturas (ja carregada)."""
        self._page.wait_for_selector("tr.BngTableTr")
        return self._page.locator("tr.BngTableTr").all()

    def ler_info_linha(self, linha: Locator) -> tuple[str, str, str]:
        """Le nome, tipo e origem de uma linha da tabela de estruturas."""
        nome = extract_name(linha)
        celulas = linha.locator("td").all_inner_texts()
        tipo = celulas[1].strip() if len(celulas) > 1 else "?"
        origem = celulas[2].strip() if len(celulas) > 2 else "?"
        return nome, tipo, origem

    def extrair_sql(self, nome_estrutura: str) -> str:
        """Abre a tela de edicao da estrutura indicada, le o SQL do editor
        CodeMirror e fecha a tela de volta."""
        linha = self._page.locator("tr.BngTableTr").filter(
            has=self._page.get_by_text(nome_estrutura, exact=True)
        )
        linha.locator("button.BngIconButton").click(timeout=TIMEOUT_BOTAO_3_PONTOS_MS)
        self._page.get_by_text("editEditar").click()
        self._page.get_by_role("button", name="Próximo ").click()
        self._page.wait_for_selector(".CodeMirror")

        sql = self._page.evaluate("document.querySelector('.CodeMirror').CodeMirror.getValue()")

        self._page.locator(".dialog-close-button-marker-class").click()
        self._page.evaluate(
            "document.querySelectorAll('.StructureMenuPopper, .BngClickOutsideOverlay')"
            ".forEach(el => el.remove())"
        )
        return sql

    def fechar_modais_apos_erro(self) -> None:
        """Se um erro aconteceu no meio de `extrair_sql` (antes de fechar a
        modal de edicao), tenta fechar tudo que possa ter ficado aberto, pra
        nao bloquear a extracao da proxima estrutura. Cada tentativa e'
        independente das outras: uma falhar nao impede as demais."""
        tentativas = (
            lambda: self._page.locator(".dialog-close-button-marker-class").click(timeout=3000),
            lambda: self._page.keyboard.press("Escape"),
            lambda: self._page.evaluate(
                "document.querySelectorAll('.StructureMenuPopper, .BngClickOutsideOverlay')"
                ".forEach(el => el.remove())"
            ),
            lambda: self._page.evaluate(
                "document.querySelectorAll('.IceDialogBackdrop').forEach(el => el.remove())"
            ),
        )
        for tentativa in tentativas:
            try:
                tentativa()
            except Exception:
                pass
