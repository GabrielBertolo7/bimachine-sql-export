"""
Gera o pacote distribuivel da ferramenta (pasta pronta para zipar e compartilhar).
Rodar com: .\\venv\\Scripts\\python.exe build.py
"""
import os
import shutil
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NOME_APP = "ExtrairSQLs"
DIST_DIR = os.path.join(BASE_DIR, "dist", NOME_APP)
LOCALAPPDATA = os.environ["LOCALAPPDATA"]
MS_PLAYWRIGHT_SRC = os.path.join(LOCALAPPDATA, "ms-playwright")


def limpar_builds_antigos():
    for pasta in ("build", "dist"):
        caminho = os.path.join(BASE_DIR, pasta)
        if os.path.isdir(caminho):
            shutil.rmtree(caminho)
    spec = os.path.join(BASE_DIR, f"{NOME_APP}.spec")
    if os.path.isfile(spec):
        os.remove(spec)


def rodar_pyinstaller():
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--onedir",
            "--name", NOME_APP,
            "--collect-all", "playwright",
            "--console",
            os.path.join(BASE_DIR, "extract_all.py"),
        ],
        cwd=BASE_DIR,
        check=True,
    )


def copiar_chromium():
    pastas_chromium = [
        p for p in os.listdir(MS_PLAYWRIGHT_SRC)
        if p.startswith("chromium-") and os.path.isdir(os.path.join(MS_PLAYWRIGHT_SRC, p))
    ]
    if not pastas_chromium:
        raise RuntimeError(
            f"Nenhuma pasta 'chromium-*' encontrada em {MS_PLAYWRIGHT_SRC}. "
            "Rode 'playwright install chromium' primeiro."
        )
    destino_base = os.path.join(DIST_DIR, "ms-playwright")
    os.makedirs(destino_base, exist_ok=True)
    for pasta in pastas_chromium:
        origem = os.path.join(MS_PLAYWRIGHT_SRC, pasta)
        destino = os.path.join(destino_base, pasta)
        print(f"Copiando {pasta} para o pacote...")
        shutil.copytree(origem, destino)


def copiar_arquivos_extra():
    shutil.copy(
        os.path.join(BASE_DIR, "config.env.example"),
        os.path.join(DIST_DIR, "config.env.example"),
    )
    shutil.copy(
        os.path.join(BASE_DIR, "LEIA-ME.txt"),
        os.path.join(DIST_DIR, "LEIA-ME.txt"),
    )


def compactar():
    zip_path = os.path.join(BASE_DIR, "dist", NOME_APP)
    shutil.make_archive(zip_path, "zip", root_dir=os.path.join(BASE_DIR, "dist"), base_dir=NOME_APP)
    print(f"\nPacote pronto: {zip_path}.zip")


def main():
    print("1/5 Limpando builds antigos...")
    limpar_builds_antigos()

    print("2/5 Rodando PyInstaller...")
    rodar_pyinstaller()

    print("3/5 Copiando navegador Chromium para dentro do pacote...")
    copiar_chromium()

    print("4/5 Copiando LEIA-ME.txt e config.env.example...")
    copiar_arquivos_extra()

    print("5/5 Compactando...")
    compactar()


if __name__ == "__main__":
    main()
