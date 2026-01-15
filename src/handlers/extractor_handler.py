from pathlib import Path
from typing import Any
import pandas as pd
import glob
import os

from src.Domain.Package import Package
from src.handlers.Handler import AbstractHandler


class ExtractorHandler(AbstractHandler):
    def _carregarUnirXlsx(self, pasta):
        # 1. Monta o caminho absoluto corretamente
        # Subindo 3 níveis: src/handlers/ExtractorHandler.py -> src/handlers -> src -> raiz
        raiz_projeto = Path(__file__).resolve().parent.parent.parent
        caminho_base = (raiz_projeto / pasta).resolve()

        print(f"Buscando em: {caminho_base}")  # Debug para conferir o caminho final

        # 2. Busca os arquivos usando pathlib (mais moderno que glob.glob)
        arquivos = list(caminho_base.glob("*.xlsx"))

        dfs = []
        for arquivo in arquivos:
            try:
                # 'arquivo' aqui é um objeto Path, o pandas aceita diretamente
                df = pd.read_excel(arquivo)
                dfs.append(df)
                print(f"Arquivo carregado: {arquivo.name}")
            except Exception as e:
                print(f"Erro ao ler o arquivo {arquivo}: {e}")

        # 3. Verificação
        if not dfs:
            print(f"Aviso: Nenhum arquivo Excel encontrado em: {caminho_base}")
            return pd.DataFrame()

        return pd.concat(dfs, ignore_index=True)

    def handle(self, request: Package) -> Package:
        package = Package(request.parameters ,self._carregarUnirXlsx(request.parameters.pasta))
        return super().handle(package)


