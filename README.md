# BIMachine SQL Export

Automação que extrai o SQL de todas as consultas ("estruturas") configuradas
num projeto do [BIMachine](https://www.bimachine.com.br/) e salva cada uma
como arquivo `.sql` local, organizado por cliente/mês e por tipo (Dados /
Analítica).

Este é o repositório de desenvolvimento. Quem só vai **rodar** a ferramenta
(sem mexer no código) deve usar o pacote gerado por `build.py`, que inclui um
guia próprio ([`LEIA-ME.txt`](LEIA-ME.txt)); não precisa clonar este repo.

## Contexto

Esse processo era feito manualmente: abrir cada estrutura na tela de "Dados e
Integrações" do BIMachine e copiar o SQL um por um. A API pública da
plataforma não expõe o SQL bruto das consultas (dado sensível), e a tela onde
ele aparece é um wizard legado (ICEfaces/JSF) sem uma API REST limpa por
trás; reconstruir isso via requisição HTTP direta seria frágil.

Por isso a automação usa um navegador real (Playwright): deixa o próprio site
renderizar normalmente e lê a tela como um humano faria, em vez de tentar
recriar as chamadas internas da página. O SQL em si é lido direto da
instância do editor CodeMirror (`.CodeMirror.getValue()` via JS), não do
texto renderizado; evita problemas de consultas grandes não aparecerem
inteiras na tela.

## Regras de segurança

- **Somente leitura**: o script nunca digita nada além do login, nunca clica
  em "Salvar", e sempre fecha telas pelo X/Cancelar.
- **Login individual**: cada colaborador roda com a própria conta do
  BIMachine; compartilhar login entre pessoas viola os Termos de Uso da
  plataforma.
- Credenciais ficam só na máquina de cada um (`config.env`, fora do controle
  de versão) e nunca sobem para este repositório.

## Estrutura

```
extract_all.py        -> script principal: login, seleciona o projeto, extrai o SQL de cada
                          estrutura elegivel e salva em output/<ano-mes> - <projeto>/<Dados|Analitica>/
bimachine_helpers.py   -> funcoes auxiliares (nome limpo da estrutura, nome de arquivo seguro)
build.py               -> gera o pacote executavel (.exe + Chromium embutido) para distribuir ao time
LEIA-ME.txt            -> instrucoes para quem so vai RODAR o programa (nao editar codigo)
extract_one.py         -> script de teste/depuracao numa unica estrutura - uso do desenvolvedor
list_structures.py     -> lista as estruturas disponiveis sem extrair nada - uso do desenvolvedor
```

## Padrões

`BimachinePage` (`bimachine_page.py`) é um [Page Object](https://martinfowler.com/bliki/PageObject.html): concentra os seletores e as interações com a interface do BIMachine num único lugar, separado da lógica de cada script. `extract_all.py`, `extract_one.py` e `list_structures.py` usam essa mesma classe, o que elimina a duplicação de login/navegação que existia entre eles.

## Rodando em desenvolvimento

```
python -m venv venv
.\venv\Scripts\pip install playwright python-dotenv
.\venv\Scripts\playwright install chromium
copy config.env.example config.env
```

Edite o `config.env` gerado com suas credenciais do BIMachine, depois rode:

```
.\venv\Scripts\python.exe extract_all.py
```

A sessão do navegador fica salva em `browser_profile/` (também fora do
controle de versão) para não pedir login/2FA a cada execução.

## Empacotando para distribuir ao time

```
.\venv\Scripts\pip install pyinstaller
.\venv\Scripts\python.exe build.py
```

Isso gera `dist/ExtrairSQLs.zip`, que inclui o Chromium embutido; então quem for
só usar não precisa instalar Python nem nada além de descompactar e rodar o
`.exe`. É o conteúdo desse zip que deve ser copiado para a pasta compartilhada
com o time, não a raiz deste repositório. Rode o `build.py` de novo toda vez
que o código mudar, antes de redistribuir.
