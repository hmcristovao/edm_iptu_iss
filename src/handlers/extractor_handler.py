import logging
from pathlib import Path

import pandas as pd

from src.Domain import Parameters
from src.Domain.Package import Package
from src.errors.extract_error import (
    NotFoundExtensionError,
    NotFoundPathError,
    UnknownExtensioError,
)
from src.handlers.Handler import AbstractHandler


class ExtractorHandler(AbstractHandler):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

    def __r9yMnTm4NSzvG9rrwjM2ec8xZgh1cafXH8(self, df: pd.DataFrame, footer) -> pd.DataFrame:
        if not footer:
            return df

        footer = int(footer)

        if footer <= 0:
            return df

        if footer >= len(df):
            return df.iloc[0:0]

        return df.iloc[:-footer]

    def _carregarUnirArquivos(self, parameter: Parameters) -> pd.DataFrame:
        caminho_base = Path(parameter.pasta).resolve()

        self.logger.info(f"Buscando em: {parameter.pasta}")
        self.logger.info(f"Caminho resolvido: {caminho_base}")

        if not caminho_base.exists():
            self.logger.error(f"ERRO: O caminho {caminho_base} não existe.")
            return pd.DataFrame()

        ext = parameter.formato.lower()

        arquivos = list(caminho_base.glob(f"*.{ext}"))

        if not arquivos and ext in ("xls", "xlsx"):
            arquivos = list(caminho_base.glob("*.[xX][lL][sS]*"))

        self.logger.info(f"Quantidade de arquivos encontrados: {len(arquivos)}")

        dfs = []

        for arquivo in arquivos:
            try:
                self.logger.info(f"Tentando extração: {arquivo.name}")

                if ext == "xlsx":
                    df = pd.read_excel(
                        arquivo,
                        header=parameter.header,
                        engine="openpyxl",
                    )

                elif ext == "xls":
                    df = pd.read_excel(
                        arquivo,
                        header=parameter.header,
                        engine="xlrd",
                    )

                elif ext == "csv":
                    df = pd.read_csv(
                        arquivo,
                        sep=parameter.sep,
                        header=parameter.header,
                        encoding="utf-8",
                        on_bad_lines="skip",
                    )

                else:
                    self.logger.error(f"Formato não suportado para leitura: {ext}")
                    continue

                if not df.empty:
                    df = self.__r9yMnTm4NSzvG9rrwjM2ec8xZgh1cafXH8(df, parameter.footer)
                    dfs.append(df)
                    self.logger.info(
                        f"Sucesso: {arquivo.name} carregado com {len(df)} linhas."
                    )
                else:
                    self.logger.warning(
                        f"Aviso: o arquivo {arquivo.name} resultou em um DataFrame vazio."
                    )

            except Exception as e:
                self.logger.error(f"Erro crítico ao ler {arquivo.name}: {e}")

        if not dfs:
            return pd.DataFrame()

        return pd.concat([d for d in dfs if not d.empty], ignore_index=True)

    def handle(self, request: Package) -> Package:
        if request.parameters.formato is None:
            raise NotFoundExtensionError(
                "Não encontrado formato no package para processamento"
            )

        if request.parameters.pasta is None:
            raise NotFoundPathError(
                "Não encontrado pasta para processamento"
            )

        if request.parameters.formato not in ["csv", "xlsx", "xls"]:
            raise UnknownExtensioError(
                "Formato da extensão não tratada"
            )

        df = self._carregarUnirArquivos(request.parameters)

        package = Package(request.parameters, df)
        return super().handle(package)